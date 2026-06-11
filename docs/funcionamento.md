# Funcionamento do refactor-os

Documentação de referência sobre **como o projeto funciona por dentro**: conexão
entre agentes e tools, papel do embedding/knowledge base, orquestração do
pipeline pelo service, uso do dataset pelos agentes e mecânica da avaliação
empírica.

> Para visão geral de escopo (5 smells × 5 patterns), endpoints e setup
> consulte [Readme.md](../Readme.md), [docs/architecture.md](architecture.md)
> e [docs/usage.md](usage.md). Este documento foca em **como cada peça opera**.

---

## 1. Os três agentes e suas tools

O sistema é um **pipeline cirúrgico** com três agentes Agno construídos por
factories em [app/agents/](../app/agents/). Cada agente é especialista em uma
única responsabilidade, recebe apenas as tools que precisa para ela e devolve
um schema Pydantic validado (Spec-Driven).

| Agente | Factory | Tools recebidas | Output (Pydantic) |
|---|---|---|---|
| **Detector** (Rastreador) | [detector_agent.py:14](../app/agents/detector_agent.py#L14) | `ast_analyzer_tool` | [`SmellDetection`](../app/core/schemas.py#L35) |
| **Recommender** (Arquiteto) | [recommender_agent.py:16](../app/agents/recommender_agent.py#L16) | `design_pattern_reference_tool`, `KnowledgeTools(get_pattern_knowledge())` | [`RefactoringProposal`](../app/core/schemas.py#L44) |
| **Critic** (Revisor / Reflection) | [critic_agent.py:15](../app/agents/critic_agent.py#L15) | `syntax_checker_tool`, `diff_generator_tool` | [`ReflectionReview`](../app/core/schemas.py#L51) |

Os três compartilham o mesmo `MistralChat` (`LLM_MODEL_ID`, default
`mistral-medium-latest`) e a mesma `PostgresDb` (sessões/traces) via
[get_db()](../app/db/session.py). O que muda é o **prompt**
([app/core/prompts.py](../app/core/prompts.py)), as **tools** e o
**`output_schema`**.

### 1.1 Detector — como usa suas tools

Prompt em [prompts.py:3](../app/core/prompts.py#L3) (`DETECTOR_INSTRUCTIONS`)
obriga a chamar `ast_analyzer_tool` **antes** de concluir.

- **`ast_analyzer_tool`** ([ast_tools.py:124](../app/tools/ast_tools.py#L124))
  combina `ast` + `radon.complexity.cc_visit` e devolve métricas
  determinísticas:
  - complexidade ciclomática por bloco e blocos com CC > 10
    (`HIGH_COMPLEXITY_THRESHOLD`);
  - classes com mais de 20 membros (`GOD_CLASS_MEMBER_THRESHOLD`);
  - funções com ≥ 5 parâmetros (`LONG_PARAMETER_THRESHOLD`).

O prompt amarra esses thresholds aos smells (`CC > 10 → suspeita de Complex
Switch`, `>20 membros → God Class`, `≥5 params → Long Parameter List`), o que
**reduz drasticamente o espaço para alucinação**: o LLM precisa apenas
classificar com base em números objetivos vindos da tool.

### 1.2 Recommender — como usa suas tools

Prompt em [prompts.py:35](../app/core/prompts.py#L35)
(`RECOMMENDER_INSTRUCTIONS`) força o mapeamento estrito Smell→Pattern e
inclui um bloco **`## Exemplos (few-shot)`** a partir de
[prompts.py:68](../app/core/prompts.py#L68) — dois pares
entrada→saída (Strategy e Template Method) extraídos do dataset, mostrando
(a) `refactored_code` em string JSON única, (b) wrapper preservando a
assinatura pública e (c) `architectural_explanation` numerado. Veja a
justificativa do gap que motivou esses exemplos em
[`docs/agentic_patterns.md`](agentic_patterns.md#15--few-shot-prompting-recommender--critic).

- **`design_pattern_reference_tool`**
  ([pattern_registry.py:274](../app/tools/pattern_registry.py#L274)) é um
  **registro fechado** com `intent`, `structure` e `rules` de cada um dos 5
  patterns. O agente é obrigado a chamá-lo com o nome do pattern obrigatório
  antes de propor código — isso garante que a estrutura canônica venha do
  registro, não da memória do modelo. Aliases (`"strategy"`, `"di"`, `"srp"`,
  …) são normalizados em `_PATTERN_ALIASES`
  ([pattern_registry.py:97](../app/tools/pattern_registry.py#L97)).
- **`KnowledgeTools(get_pattern_knowledge())`** dá ao Recommender acesso de
  retrieval semântico aos `.md` de cada pattern indexados no PgVector — é a
  parte que usa embeddings (ver §2). O agente pode buscar exemplos e
  justificativas para enriquecer o `architectural_explanation` sem inventar.

A função `service.propose()`
([refactor_service.py:59](../app/services/refactor_service.py#L59)) **resolve
deterministicamente** o pattern via `SMELL_TO_PATTERN[smell_type]`
([schemas.py:25](../app/core/schemas.py#L25)) e o injeta no prompt como
"pattern obrigatório" — o LLM não escolhe o pattern; ele só implementa.

### 1.3 Critic — como usa suas tools

Prompt em [prompts.py:120](../app/core/prompts.py#L120) (`CRITIC_INSTRUCTIONS`)
define **5 critérios** (sintaxe, lógica preservada, pattern correto,
assinaturas públicas, imports controlados) e, a partir de
[prompts.py:165](../app/core/prompts.py#L165), inclui um bloco
**`## Exemplos (few-shot)`** com 3 casos: 1 aprovação amarrando todos os 5
critérios na `critique` + 2 rejeições mostrando o formato "Critério N
falhou: ... Ação: ...". A motivação está documentada em
[`docs/agentic_patterns.md`](agentic_patterns.md#15--few-shot-prompting-recommender--critic).

> O **Detector** segue **zero-shot** propositalmente — o baseline já marcava
> F1 = 1.000 sobre 20 amostras; adicionar exemplos ali só introduz ruído.

Obriga a usar duas tools:

- **`syntax_checker_tool`** ([syntax_tools.py:55](../app/tools/syntax_tools.py#L55))
  roda `ast.parse` + `ruff check` num arquivo temporário e devolve
  `is_valid` + lista de issues.
- **`diff_generator_tool`** ([diff_tools.py:20](../app/tools/diff_tools.py#L20))
  produz `difflib.unified_diff` entre o original e o refatorado, base para o
  julgamento de "lógica preservada".

A decisão é binária (`is_approved`); quando falsa, a `critique` precisa citar
o número do critério que falhou — é esse texto que o service realimenta no
Recommender no próximo ciclo de reflection.

---

## 2. Embeddings — quem usa e por quê

**Quem usa:** apenas o **Recommender**, via a tool `KnowledgeTools` instanciada
em [recommender_agent.py:31](../app/agents/recommender_agent.py#L31).

**Por quê:** o Recommender é o único agente que precisa de **conhecimento
canônico aberto** sobre cada pattern (intent, estrutura, exemplos) para
fundamentar o `architectural_explanation` e o código gerado. Detector e Critic
operam sobre fatos determinísticos do código (AST/radon, ruff, diff), não
precisam de retrieval semântico.

**Por que retrieval em vez de inlinear no prompt:** os 5 `.md` em
[app/knowledge/patterns/](../app/knowledge/patterns/) são longos e crescerão.
PgVector permite injetar **só os trechos relevantes** ao smell em questão,
mantendo o prompt enxuto e o custo de tokens previsível.

### 2.1 Como o KB é construído

[provider.py:20](../app/knowledge/provider.py#L20)
(`get_pattern_knowledge`, com `@lru_cache`) monta a stack:

```
HuggingfaceCustomEmbedder(BAAI/bge-small-en-v1.5, 384 dims)
        │  HF Inference API gratuita (HUGGINGFACE_API_KEY)
        ▼
PgVector(table=design_patterns_kb, db_url=…)
        │
        ▼
Knowledge(name="design-patterns-kb", contents_db=PostgresDb)
```

A escolha por **HF Inference API + `bge-small-en-v1.5` (384 dim)** é
deliberada:
- **gratuito** (só pede um token Read do HF);
- **sem compilação Rust local** (evita o `tokenizers` nativo);
- modelo pequeno e rápido o suficiente para uma base de 5 documentos;
- 384 dimensões batem com a tabela do PgVector criada por Agno.

### 2.2 Como o KB é populado

`POST /api/v1/knowledge/sync` dispara
[`load_patterns_into_kb`](../app/services/knowledge_service.py#L14):

```
for cada *.md em app/knowledge/patterns/:
    knowledge.ainsert(name=stem, path=…)   # paraleliza com asyncio.gather
return len(arquivos)
```

Cada `.md` é dividido em chunks pela Agno, cada chunk vira um embedding via HF
e é gravado em `design_patterns_kb`. Em tempo de uso, o `KnowledgeTools` que o
Recommender carrega permite ao LLM emitir queries do tipo *"estrutura
canônica do Strategy Pattern aplicado a switch sobre tipo"* e receber os
trechos top-K mais similares.

---

## 3. Como o service produz o pipeline dos agentes

A "cola" entre os agentes é o **`RefactorService`**
([refactor_service.py](../app/services/refactor_service.py)) — explicitamente
**não** um `Team` da Agno. A razão está documentada em
[architecture.md:122](architecture.md#L122): `Team` em modo `route`/`coordinate`
introduz um LLM coordenador, o que quebraria (i) ordem fixa, (ii) número
exato de iterações e (iii) métricas isoladas por estágio.

### 3.1 Construção

`RefactorService.__init__` instancia os três agentes uma única vez
([refactor_service.py:41](../app/services/refactor_service.py#L41)). Como
`get_settings()` e `get_db()` são `lru_cache`, todos compartilham a mesma
sessão Postgres.

### 3.2 Três métodos por estágio

Cada estágio tem um método `async` que monta o prompt específico, chama
`agent.arun(prompt)` e **valida o tipo de retorno** contra o schema esperado
— se vier qualquer coisa diferente, lança `ValueError` (não há fallback
silencioso).

- **`detect(source_code)`** — embute o código entre fences e força
  `ast_analyzer_tool`. Retorna `SmellDetection`.
- **`propose(source_code, detection, prior_critique=None)`** — resolve o
  pattern via `SMELL_TO_PATTERN`, monta um prompt com smell, pattern
  obrigatório, justificativa do Detector, linhas afetadas e (opcional) a
  crítica da rodada anterior. Retorna `RefactoringProposal`.
- **`review(source_code, proposal)`** — monta um prompt com original ×
  refatorado, força `syntax_checker_tool` + `diff_generator_tool` e exige
  `final_validated_code=null`. Retorna `ReflectionReview`.

### 3.3 Orquestração + reflection loop

`run(request)` em
[refactor_service.py:110](../app/services/refactor_service.py#L110) é o coração:

```
detection = await detect(source)
if detection sem smell → encerra (approved=False, iterations=0)

critique = None
for iteration in 1..MAX_REFLECTION_ITERATIONS (default 3):
    proposal = await propose(source, detection, prior_critique=critique)
    review   = await review(source, proposal)
    if review.is_approved:
        return RefactorResult(approved=True, iterations=iteration, …)
    critique = review.critique            # vira input do próximo propose

return RefactorResult(approved=False, iterations=MAX, …)
```

Pontos importantes:

- **Cada estágio está envolto em `try/except`** com `logger.exception` — uma
  falha do Detector aborta o pipeline e devolve `_DETECT_FALLBACK`
  ([refactor_service.py:31](../app/services/refactor_service.py#L31)); falhas
  do Recommender/Critic preservam o que já foi obtido e marcam `error`. A
  avaliação consegue distinguir "erro de infra" de "veredito do agente".
- **A crítica é o único canal de feedback** Critic→Recommender. O Recommender
  não vê o histórico do próprio Critic; recebe apenas o texto da `critique`,
  o que mantém cada chamada determinística e reproduzível.
- **O limite é configurável** via `MAX_REFLECTION_ITERATIONS` (env). A métrica
  `avg_iterations` da avaliação mede o "esforço" típico do pipeline.

### 3.4 Caminho de entrada

O `RefactorService` é chamado por:
- `POST /api/v1/refactor` ([routes.py](../app/api/routes.py) → controller) para
  uso interativo;
- `EvaluationService.evaluate_refactor`
  ([evaluation_service.py:149](../app/services/evaluation_service.py#L149))
  para a métrica do Refatorador;
- diretamente em Python (`service.run(RefactorRequest(...))`), como
  documentado em [usage.md:159](usage.md#L159).

---

## 4. Como o dataset é usado pelos agentes

> O dataset **não treina** os agentes — não há fine-tuning, RL, nem
> few-shot inlinado dos exemplos no prompt. O dataset é **gabarito de
> avaliação** (ground truth) usado para medir a qualidade de cada agente em
> isolamento.

### 4.1 Estrutura

Cada eixo de avaliação tem 10 + 10 amostras (ver
[dataset/README.md](../dataset/README.md)):

```
dataset/
├── examples/      10 .py COM smell intencional    (positivos do Detector)
├── clean/         10 .py sem smell                (negativos do Detector)
├── solutions/
│   ├── correct/   10 refatorações boas            (positivos do Critic)
│   └── incorrect/ 10 refatorações com defeito     (negativos do Critic)
├── ground_truth.json    gabarito do Detector (20 entradas)
└── critic_truth.json    gabarito do Critic   (20 entradas)
```

`ground_truth.json` mapeia cada `.py` para `smell_type` + `expected_pattern`
(schema `GroundTruthEntry`). `critic_truth.json` aponta `problem_file`,
`solution_file`, `applied_pattern`, `expected_approved` e `defect_kind`
(schema `CriticTruthEntry`).

### 4.2 Quem lê o quê

`EvaluationService` é o único consumidor do dataset
([evaluation_service.py:60](../app/services/evaluation_service.py#L60)):

| Eixo | Dataset usado | Como o agente entra |
|---|---|---|
| Detector | `examples/` + `clean/` (via `ground_truth.json`) | `service.detect(arquivo)` por arquivo |
| Refactor | só `examples/` (10 c/ smell) | `service.run(RefactorRequest(...))` pipeline completo |
| Critic | `critic_truth.json` → `solutions/{correct,incorrect}` | `service.review(original, RefactoringProposal(fixture))` — o Critic recebe a solução pronta como se viesse do Recommender |

No eixo Critic há um detalhe importante
([evaluation_service.py:247](../app/services/evaluation_service.py#L247)):
o harness **constrói uma `RefactoringProposal` sintética** a partir do `.py`
em `solutions/`. Isso isola o julgamento do Critic do desempenho do
Recommender — é como pedir ao revisor para julgar trabalhos prontos vindos
de uma fonte controlada.

### 4.3 "Aprendizado" sem treino

Onde fica o conhecimento que orienta os agentes a acertarem?

1. **Mapeamento Smell→Pattern** vive em código
   ([schemas.py:25](../app/core/schemas.py#L25),
   [pattern_registry.py:117](../app/tools/pattern_registry.py#L117)).
2. **Estrutura canônica dos patterns** vive nos `.md` indexados (§2) —
   isso sim é "consultado" pelo Recommender em tempo de execução.
3. **Critérios de aprovação** vivem nos prompts
   ([prompts.py](../app/core/prompts.py)).
4. **Métricas objetivas** vêm de tools determinísticas (AST, radon, ruff,
   diff, `assess_refactoring`).

O dataset apenas mede a aderência dos agentes a essas fontes. Esse desenho é
proposital: o resultado da avaliação aponta **onde melhorar** (prompt,
threshold, conteúdo do `.md`, escopo do `pattern_registry`) sem precisar de
um loop de treino.

---

## 5. Como funciona a avaliação empírica

Três avaliações independentes, uma por agente, todas executadas pelo
`EvaluationService` ([evaluation_service.py](../app/services/evaluation_service.py)).
Endpoints em [routes.py](../app/api/routes.py); CLI equivalente em
`scripts/run_evaluation.py`.

### 5.1 Agente Rastreador — `evaluate_detector` (`/evaluate/detector`)

[evaluation_service.py:74](../app/services/evaluation_service.py#L74)

Itera sobre `ground_truth.json` (10 com smell + 10 limpos). Para cada arquivo
chama `service.detect()` e classifica:

| Esperado | Predito | Classificação |
|---|---|---|
| tem smell | tem smell | TP (e ainda checa se `smell_type` bate → `type_accuracy`) |
| tem smell | sem smell | **FN** — deixou passar |
| sem smell | tem smell | **FP** — viu onde não há |
| sem smell | sem smell | TN |

Métricas reportadas: `precision`, `recall`, `accuracy`, `f1`, `specificity`,
`false_positive_rate`, `false_negative_rate`, `type_accuracy` e o
`per_file` com a classificação por arquivo (`DetectorMetrics`).

### 5.2 Agente Refatorador — `evaluate_refactor` (`/evaluate/refactor`)

[evaluation_service.py:149](../app/services/evaluation_service.py#L149)

Para cada um dos 10 `examples/` roda o **pipeline completo**
(`service.run`) e passa a proposta por
[`assess_refactoring`](../app/services/quality_checks.py#L66), que aplica três
verificações **determinísticas** (sem LLM):

1. **`pattern_correct`** — `applied_pattern == expected_pattern`
   (`pattern_matches`).
2. **`syntax_valid`** — `ast.parse` + `ruff check` via `check_syntax`.
3. **`logic_preserved`** — `api_preservation`: extrai funções/classes/métodos
   públicos do original e exige que sobrevivam no refatorado.

`is_correct = pattern_correct AND syntax_valid AND logic_preserved`. As
métricas (`RefactorQualityMetrics`) reportam taxas por eixo + `avg_iterations`
(quantas voltas de reflection foram necessárias em média) e
`pipeline_approved_rate` (quantas o Critic deixou passar). Importante: a
`accuracy` aqui é **objetiva** (heurísticas), não depende do veredito do
Critic — assim dá pra detectar quando o Critic aprovou algo que falha nas
checagens estáticas.

### 5.3 Agente Revisor — `evaluate_critic` (`/evaluate/critic`)

[evaluation_service.py:230](../app/services/evaluation_service.py#L230)

Itera sobre `critic_truth.json` (10 corretas + 10 com defeito). Para cada
entrada:

1. lê `problem_file` (original) e `solution_file` (refatorado);
2. monta uma `RefactoringProposal` sintética (sem rodar o Recommender);
3. chama `service.review(original, proposal)` com **até 2 tentativas** (o
   parser do Mistral falha esporadicamente em entradas longas — comentário em
   [evaluation_service.py:253](../app/services/evaluation_service.py#L253));
4. compara `review.is_approved` com `expected_approved`:

| Esperado aprovar? | Critic aprovou? | Classificação |
|---|---|---|
| sim | sim | TP |
| sim | não | **FN (false reject)** — reprovou correta |
| não | sim | **FP (false accept)** — aprovou incorreta |
| não | não | TN |

`CriticMetrics` reporta `accuracy`, `precision`, `recall`, `f1`,
`false_accept_rate` e `false_reject_rate` — as duas últimas são as
**métricas-chave do revisor**.

### 5.4 Relatório combinado

- `evaluate_all` ([evaluation_service.py](../app/services/evaluation_service.py))
  agrega os três em `FullEvaluationReport` e é exposto via
  `POST /api/v1/evaluate/all`. Aceita body opcional com até três seções
  (`detector`/`refactor`/`critic`), cada uma com seu próprio `samples`; seções
  ausentes caem no dataset, permitindo misturar ad-hoc e dataset numa única
  chamada.
- Os três endpoints por agente (`/evaluate/{detector,refactor,critic}`) também
  aceitam um body com `samples` para avaliar **código submetido**
  pelo usuário no lugar do dataset — útil pra rodar a métrica sobre amostras
  ad-hoc sem precisar adicionar arquivos ao `dataset/`. Veja o `Readme.md` para
  o schema das amostras.
- `scripts/run_evaluation.py --all --md … --json …` produz
  `dataset/reports/evaluation.{md,json}` (o `.md` é auto-contido por seção).

### 5.5 Garantias do desenho

- **Cada agente é medido isoladamente** (FP/FN do Detector não contaminam
  accuracy do Refator; veredito do Critic não contamina checagens estáticas).
- **As métricas que importam não usam LLM** — `assess_refactoring`,
  `ConfusionMatrix` e a comparação contra ground truth são puramente
  determinísticas. O LLM aparece **dentro** do que está sendo medido, não no
  juiz.
- **Erros de infraestrutura são logados e isolados** (`per_file: {error:
  true}`), de forma que uma falha de rede não inflaciona FN/FP.

---

## Mapa rápido para navegação

- Pipeline e reflection loop → [app/services/refactor_service.py](../app/services/refactor_service.py)
- Avaliação → [app/services/evaluation_service.py](../app/services/evaluation_service.py)
- Schemas trocados entre agentes → [app/core/schemas.py](../app/core/schemas.py)
- Prompts (contrato de comportamento) → [app/core/prompts.py](../app/core/prompts.py)
- Tools determinísticas → [app/tools/](../app/tools/)
- Knowledge base (PgVector + HF embeddings) → [app/knowledge/provider.py](../app/knowledge/provider.py)
- Checagens objetivas do refator → [app/services/quality_checks.py](../app/services/quality_checks.py)
- Dataset e gabaritos → [dataset/](../dataset/)
