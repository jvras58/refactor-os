# Funcionamento do refactor-os

Documentação de referência sobre **como o projeto funciona por dentro**: conexão
entre agentes e tools, papel do embedding/knowledge base, orquestração do
pipeline pelo service, uso do dataset pelos agentes e mecânica da avaliação
empírica.

> Para visão geral de escopo (4 smells × 4 patterns), endpoints e setup
> consulte [Readme.md](../Readme.md), [docs/architecture.md](architecture.md)
> e [docs/usage.md](usage.md). Este documento foca em **como cada peça opera**.

---

## 1. Os três agentes e suas tools

O sistema é um **pipeline cirúrgico** com três agentes Agno construídos por
factories em [app/agents/](../app/agents/). Cada agente é especialista em uma
única responsabilidade, recebe apenas as tools que precisa para ela e devolve
um schema Pydantic validado (Spec-Driven).

| Agente | Factory | Tools / Skills | Output (Pydantic) |
|---|---|---|---|
| **Detector** (Rastreador, multi-label) | [detector_agent.py](../app/agents/detector_agent.py) | nenhuma tool — o prior heurístico é injetado no prompt pelo service | [`TypeDetectionResult`](../app/core/schemas.py) (1 por chamada; 8 chamadas agregadas em `DetectionScanResult`) |
| **Recommender** (Arquiteto) | [recommender_agent.py](../app/agents/recommender_agent.py) | skills: `Skills(loaders=[LocalSkills("app/skills")])` → expõe `get_skill_instructions` + RAG `search_knowledge_base` | [`RefactoringProposal`](../app/core/schemas.py) |
| **Critic** (Revisor / Reflection) | [critic_agent.py](../app/agents/critic_agent.py) | tools: `syntax_checker_tool`, `diff_generator_tool` | [`ReflectionReview`](../app/core/schemas.py) |

Os três compartilham o mesmo `MistralChat` (`LLM_MODEL_ID`, default
`mistral-medium-latest`) construído pelo
[`build_main_model()`](../app/core/llm.py), e cada um também recebe um
`parser_model` separado pela
[`build_parser_model()`](../app/core/llm.py) (mesmo modelo, temperatura 0)
para extrair o `output_schema` sem confundir tool/skill-calling com JSON-mode
forçado. O que muda entre eles é o **prompt**
([app/core/prompts.py](../app/core/prompts.py)), as **tools/skills** e o
**`output_schema`**.

### 1.1 Detector — multi-detector em 4 fases

O Detector não é mais uma única chamada de LLM: é o
[`MultiDetectorService`](../app/services/multi_detector_service.py), um
pipeline **multi-label** de 4 fases explícitas:

1. **Validação** — `ast.parse` no código de entrada; falha levanta
   [`InvalidPythonCodeError`](../app/core/exceptions.py) (a API devolve `422`).
2. **Matriz heurística (sem LLM)** —
   [`score_all_smells`](../app/tools/heuristic_engine.py) devolve um sinal
   determinístico **por smell** (sempre os 4, mesmo quando não há evidência):
   score, evidências e linhas.
3. **8 chamadas LLM, uma por tipo** — para cada smell e cada pattern, o agente
   ([detector_agent.py](../app/agents/detector_agent.py)) recebe: a definição
   canônica do tipo ([`SMELL_DEFINITIONS`/`PATTERN_DEFINITIONS`](../app/core/prompts.py)),
   o prior heurístico relevante e o código completo — e devolve um veredito
   sim/não isolado (`TypeDetectionResult` com `detected`, `evidencias`,
   `reasoning`). O prior **informa** cada prompt, mas nunca pula uma checagem.
4. **Compilação** — uma estratégia trocável (`ResultCompiler`) dá forma ao scan
   para cada consumidor; a padrão (`GroundTruthArrayCompiler`) devolve a lista
   de nomes detectados, no mesmo formato do `problems` do ground truth.

Pontos do desenho:

- **Smell ≠ pattern**: as instruções ([`TYPE_DETECTOR_INSTRUCTIONS`](../app/core/prompts.py))
  deixam explícito que um pattern pode ser aplicável mesmo sem o smell irmão
  presente (ex.: Builder sem Long Parameter List) — e vice-versa.
- **Genérico por construção**: o agente é um só; o tipo avaliado é injetado no
  prompt **por chamada** (`build_type_prompt`), não nas instruções estáticas.
- **Custo**: cada `detect()` = 8 chamadas reais de LLM (com throttle anti-429
  em [`app/utils/retry.py`](../app/utils/retry.py)).

### 1.2 Recommender — como usa Skills no lugar de RAG

Prompt (`RECOMMENDER_INSTRUCTIONS` em [prompts.py](../app/core/prompts.py))
força o mapeamento estrito Smell→Pattern e obriga
o agente a chamar `get_skill_instructions(name="<skill>")` antes de propor o
código. O nome do skill é injetado **deterministicamente** pelo serviço (não
é o LLM que escolhe).

- **Skills** ([recommender_agent.py](../app/agents/recommender_agent.py)) —
  `Skills(loaders=[LocalSkills(SKILLS_DIR)])` aponta para [`app/skills/`](../app/skills/),
  com um `SKILL.md` por pattern do escopo:
  `strategy-pattern`, `builder-parameter-object`, `facade-srp`, `template-method`.
  - **System prompt automático:** o Agno injeta no system prompt apenas as
    `description:` curtas de cada skill — o corpo (regras, exemplo, justificativa)
    só entra no contexto quando o agente chama `get_skill_instructions`.
  - **Tools expostas automaticamente:** `get_skill_instructions(name)`,
    `get_skill_reference(name, path)`, `get_skill_script(name, path)`. No nosso
    fluxo só usamos a primeira.
  - **Resolução determinística:** `service.propose()` traduz o
    `target_pattern` no nome do skill via `_PATTERN_TO_SKILL` em
    [`refactor_service.py`](../app/services/refactor_service.py) e o injeta no
    prompt. O LLM não precisa adivinhar o nome.

O alvo (`target_smell` + `target_pattern`) é **selecionado deterministicamente**
do scan multi-label pelo `RefactorService._select_target()` (ver §3.2) — o LLM
não escolhe o pattern; ele só carrega o skill correspondente e implementa.

> **Skills + RAG (lado a lado):** o Recommender carrega o playbook do pattern via
> Skill (`get_skill_instructions`, lookup por nome) **e** recupera exemplos de
> referência via agentic RAG nativo (`Agent(knowledge=get_solution_knowledge(),
> search_knowledge=True)` → tool `search_knowledge_base`) sobre PgVector + HuggingFace
> embeddings (corpus `app/knowledge/solutions/`). Detalhes em
> [`docs/agentic_patterns.md`](agentic_patterns.md#16--rag-pgvector--corpus-de-soluções).
> A tabela pgvector precisa ser populada via `POST /api/v1/knowledge/sync`.

### 1.3 Critic — como usa suas tools

Prompt (`CRITIC_INSTRUCTIONS` em [prompts.py](../app/core/prompts.py))
define **5 critérios** (sintaxe, lógica preservada, pattern correto,
assinaturas públicas, imports controlados) e inclui um bloco
**`## Exemplos (few-shot)`** com 3 casos: 1 aprovação amarrando todos os 5
critérios na `critique` + 2 rejeições mostrando o formato "Critério N
falhou: ... Ação: ...". A motivação está documentada em
[`docs/agentic_patterns.md`](agentic_patterns.md#15--few-shot-prompting-recommender--critic).

> O **Detector** segue **zero-shot** propositalmente — cada chamada avalia um
> único tipo com definição canônica + prior heurístico; exemplos ali só
> introduzem ruído.

Obriga a usar duas tools:

- **`syntax_checker_tool`** ([syntax_tools.py](../app/tools/syntax_tools.py))
  roda `ast.parse` + `ruff check` num arquivo temporário e devolve
  `is_valid` + lista de issues.
- **`diff_generator_tool`** ([diff_tools.py](../app/tools/diff_tools.py))
  produz `difflib.unified_diff` entre o original e o refatorado, base para o
  julgamento de "lógica preservada".

A decisão é binária (`is_approved`); quando falsa, a `critique` precisa citar
o número do critério que falhou — é esse texto que o service realimenta no
Recommender no próximo ciclo de reflection.

---

## 2. Skills — onde vive o conhecimento dos patterns

**Quem usa:** apenas o **Recommender**, via `Skills(loaders=[LocalSkills(...)])`
instanciado em [recommender_agent.py](../app/agents/recommender_agent.py).

**Por quê:** o Recommender é o único agente que precisa de **conhecimento
canônico aberto** sobre cada pattern (intent, estrutura, exemplo) para
fundamentar o `architectural_explanation` e o código gerado. Detector e Critic
operam sobre fatos determinísticos do código (AST, ruff, diff) + definições
canônicas nos próprios prompts, não precisam de conhecimento externo.

**Por que skills em vez de RAG (decisão arquitetural):** o escopo é fechado
em 4 patterns e o mapeamento smell→pattern é 1-pra-1. Top-k semântico não
agrega valor — adiciona ruído (e dependência de embeddings, pgvector, token
HuggingFace). Skills oferecem **lookup determinístico por nome**, conteúdo
**lazy-loaded** sob demanda, e zero infra externa. Justificativa completa em
[`docs/agentic_patterns.md`](agentic_patterns.md#16--skills-substituem-rag-decisão-arquitetural).

### 2.1 Estrutura de um skill

```
app/skills/strategy-pattern/
└── SKILL.md
```

Cada `SKILL.md` tem YAML frontmatter (`name`, `description`) + corpo Markdown
com: intent, estrutura canônica, regras estritas, exemplo problema→solução
completo, justificativa arquitetural numerada e benefícios esperados.

**Apenas a `description` curta entra no system prompt o tempo todo** — o corpo
só vai pro contexto quando o agente chama `get_skill_instructions(name=...)`.

### 2.2 Como o agente descobre o skill certo

O `service.propose()` traduz o `target_pattern` no nome do skill via
`_PATTERN_TO_SKILL` em
[`refactor_service.py`](../app/services/refactor_service.py) e injeta no
prompt da chamada — o LLM recebe literalmente:

```
Skill obrigatório: strategy-pattern
Use obrigatoriamente `get_skill_instructions(name='strategy-pattern')` ...
```

Resultado: o nome do skill é **determinístico** (vem do Python, não da decisão
do LLM), e o conteúdo do skill carregado é **exatamente o relevante** para o
alvo selecionado.

### 2.3 Mapeamento smell → pattern → skill

| Smell (`SmellType`) | Pattern (`PatternType`) | Skill (`app/skills/...`) |
|---|---|---|
| Complex/Long Switch Statements | `STRATEGY` | `strategy-pattern` |
| Long Parameter List | `BUILDER` | `builder-parameter-object` |
| God Class | `FACADE` | `facade-srp` |
| Duplicated Code | `TEMPLATE_METHOD` | `template-method` |

---

## 3. Como o service produz o pipeline dos agentes

A "cola" entre os agentes é o **`RefactorService`**
([refactor_service.py](../app/services/refactor_service.py)) — explicitamente
**não** um `Team` da Agno. A razão está documentada em
[architecture.md](architecture.md): `Team` em modo `route`/`coordinate`
introduz um LLM coordenador, o que quebraria (i) ordem fixa, (ii) número
exato de iterações e (iii) métricas isoladas por estágio.

### 3.1 Construção

`RefactorService.__init__` instancia o `MultiDetectorService` + os agentes
Recommender e Critic uma única vez. Como `get_settings()` é `lru_cache`,
todos compartilham a mesma configuração.

### 3.2 Métodos por estágio

Cada estágio tem um método `async` que monta o prompt específico, chama
`agent.arun(prompt)` via [`arun_typed`](../app/utils/retry.py) e **valida o
tipo de retorno** contra o schema esperado.

- **`detect(source_code)`** — delega ao `MultiDetectorService.detect()`
  (4 fases, §1.1). Retorna `DetectionScanResult`; código inválido levanta
  `InvalidPythonCodeError`.
- **`_select_target(scan)`** — traduz o scan multi-label em **um alvo** para o
  Recommender: o smell detectado com maior score heurístico
  (pattern via `SMELL_TO_PATTERN`); sem smell, o primeiro pattern aplicável
  (smell relacionado via `PATTERN_TO_SMELL`); sem nada → pipeline encerra.
- **`propose(source_code, target_smell, target_pattern, detection, prior_critique=None)`** —
  monta um prompt com smell alvo, pattern obrigatório, skill obrigatório,
  reasoning + evidências do Detector e (opcional) a crítica da rodada anterior.
  Retorna `RefactoringProposal`.
- **`review(source_code, proposal)`** — monta um prompt com original ×
  refatorado + prior de preservação de lógica, força `syntax_checker_tool` +
  `diff_generator_tool` e exige `final_validated_code=null`. Retorna
  `ReflectionReview`.

### 3.3 Orquestração + reflection loop

`run(request)` em
[refactor_service.py](../app/services/refactor_service.py) é o coração:

```
scan = await detect(source)                     # multi-label, 8 vereditos
target = _select_target(scan)
if target vazio → encerra (approved=False, iterations=0, scan preservado)

critique = None
for iteration in 1..MAX_REFLECTION_ITERATIONS (default 3):
    proposal = await propose(source, target_smell, target_pattern, detection, prior_critique=critique)
    review   = await review(source, proposal)
    if review.is_approved:
        return RefactorResult(approved=True, iterations=iteration, …)
    critique = review.critique            # vira input do próximo propose

return RefactorResult(approved=False, iterations=MAX, …)
```

Pontos importantes:

- **Cada estágio está envolto em `try/except`** com `logger.exception` —
  código que não compila devolve `error` explícito (sem chamar LLM); falhas
  do Recommender/Critic preservam o que já foi obtido (incluindo o scan e os
  `detected_problems`) e marcam `error`. A avaliação consegue distinguir
  "erro de infra" de "veredito do agente".
- **A crítica é o único canal de feedback** Critic→Recommender. O Recommender
  não vê o histórico do próprio Critic; recebe apenas o texto da `critique`,
  o que mantém cada chamada determinística e reproduzível.
- **O limite é configurável** via `MAX_REFLECTION_ITERATIONS` (env). A métrica
  `avg_iterations` da avaliação mede o "esforço" típico do pipeline.

### 3.4 Caminho de entrada

O `RefactorService` é chamado por:
- `POST /api/v1/refactor` ([routes.py](../app/api/routes.py) → controller) para
  uso interativo;
- `EvaluationService`
  ([evaluation_service.py](../app/services/evaluation_service.py))
  para as métricas do Detector (via `detect`) e do Refatorador (via `run`);
- diretamente em Python (`asyncio.run(service.run(RefactorRequest(...)))`), como
  documentado em [usage.md](usage.md).

O detector também pode rodar em lote, com checkpoint resumível, via
[`MultiDetectorDatasetRunner`](../app/services/multi_detector_dataset_runner.py)
(CLI: `scripts/run_multi_detector.py`).

---

## 4. Como o dataset é usado pelos agentes

> O dataset **não treina** os agentes — não há fine-tuning, RL, nem
> few-shot inlinado dos exemplos no prompt. O dataset é **gabarito de
> avaliação** (ground truth) usado para medir a qualidade de cada agente em
> isolamento.

### 4.1 Estrutura

```
dataset/
├── examples/
│   ├── code_smell/     exemplos por smell (complex-switch, long-parameter, god-class, duplicated-code)
│   ├── patterns/       exemplos onde o pattern é aplicável (strategy, builder, facade, template-method)
│   ├── mixed/          exemplos com múltiplos problemas simultâneos
│   └── complex-clean/  código complexo porém limpo (mede falsos positivos)
└── ground_truth_detector.json   gabarito multi-label do Detector
```

`ground_truth_detector.json` mapeia cada `.py` (caminho relativo a
`dataset/examples/`) para a lista `problems` — **todos** os smells/patterns
presentes no arquivo; lista vazia = código limpo (schema `GroundTruthEntry`).

### 4.2 Quem lê o quê

`EvaluationService` é o único consumidor do dataset
([evaluation_service.py](../app/services/evaluation_service.py)):

| Eixo | Dataset usado | Como o agente entra |
|---|---|---|
| Detector | `examples/` (via `ground_truth_detector.json`) | `service.detect(arquivo)` por arquivo — 8 decisões binárias comparadas com `problems` |
| Refactor | entradas com `problems` não-vazio | `service.run(RefactorRequest(...))` pipeline completo; o pattern esperado é derivado dos `problems` (pattern explícito na lista, ou `SMELL_TO_PATTERN[smell]`) |
| Critic | — (o dataset atual não traz soluções rotuladas) | só modo ad-hoc: `service.review(original, RefactoringProposal(fixture))` sobre `samples` enviados |

No eixo Critic o harness **constrói uma `RefactoringProposal` sintética** a
partir da solução enviada. Isso isola o julgamento do Critic do desempenho do
Recommender — é como pedir ao revisor para julgar trabalhos prontos vindos
de uma fonte controlada.

### 4.3 "Aprendizado" sem treino

Onde fica o conhecimento que orienta os agentes a acertarem?

1. **Vocabulário de tipos + mapeamento Smell→Pattern** vivem em código
   ([schemas.py](../app/core/schemas.py)) — os enums `SmellType`/`PatternType`
   são estritos, então não há camada de aliases a manter.
2. **Definições canônicas de cada smell/pattern** vivem em
   [`prompts.py`](../app/core/prompts.py) (`SMELL_DEFINITIONS`,
   `PATTERN_DEFINITIONS`) — injetadas uma por chamada na fase 3 do detector.
3. **Estrutura canônica dos patterns** vive nos `SKILL.md` em
   [`app/skills/`](../app/skills/) (§2) — carregada sob demanda pelo
   Recommender via `get_skill_instructions`.
4. **Critérios de aprovação** vivem nos prompts
   ([prompts.py](../app/core/prompts.py)).
5. **Métricas objetivas** vêm de tools determinísticas (AST, ruff,
   diff, `assess_refactoring`).

O dataset apenas mede a aderência dos agentes a essas fontes. Esse desenho é
proposital: o resultado da avaliação aponta **onde melhorar** (prompt,
threshold, definição de um tipo, conteúdo de uma `SKILL.md`) sem precisar de
um loop de treino.

---

## 5. Como funciona a avaliação empírica

Avaliações independentes, uma por agente, todas executadas pelo
`EvaluationService` ([evaluation_service.py](../app/services/evaluation_service.py)).
Endpoints em [routes.py](../app/api/routes.py); CLI equivalente em
`scripts/run_evaluation.py`.

### 5.1 Agente Rastreador — `evaluate_detector` (`/evaluate/detector`)

Avaliação **multi-label**: para cada arquivo do ground truth (ou `sample`
enviado), roda `service.detect()` e compara o conjunto detectado com o
esperado, **tipo a tipo** — cada arquivo gera 8 decisões binárias:

| Tipo esperado no arquivo? | Detector marcou? | Classificação |
|---|---|---|
| sim | sim | TP |
| sim | não | **FN** — deixou passar |
| não | sim | **FP** — viu onde não há |
| não | não | TN |

A matriz de confusão agrega todos os pares (arquivo × tipo). Métricas
reportadas (`DetectorMetrics`): `precision`, `recall`, `accuracy`, `f1`,
`specificity`, `false_positive_rate`, `false_negative_rate`,
**`exact_match_rate`** (fração de arquivos cujo conjunto detectado bate
exatamente com o esperado) e o `per_file` com `missing`/`extra` por arquivo.
Código que não compila é reportado como `error` no `per_file` sem contaminar
a matriz.

### 5.2 Agente Refatorador — `evaluate_refactor` (`/evaluate/refactor`)

Para cada entrada do ground truth com `problems` não-vazio, deriva o
`expected_pattern` (pattern explícito na lista, ou `SMELL_TO_PATTERN` do
primeiro smell), roda o **pipeline completo** (`service.run`) e passa a
proposta por [`assess_refactoring`](../app/services/quality_checks.py), que
aplica verificações **determinísticas** (sem LLM):

1. **`pattern_correct`** — `applied_pattern == expected_pattern`
   (`pattern_matches`).
2. **`syntax_valid`** — `ast.parse` + `ruff check` via `check_syntax`.
3. **`logic_preserved`** — `api_preservation` (API pública sobrevive) +
   `behavior_preservation` (nenhum literal/`raise` sumiu).

`is_correct = pattern_correct AND syntax_valid AND logic_preserved`. As
métricas (`RefactorQualityMetrics`) reportam taxas por eixo + `avg_iterations`
(quantas voltas de reflection foram necessárias em média) e
`pipeline_approved_rate` (quantas o Critic deixou passar). Importante: a
`accuracy` aqui é **objetiva** (heurísticas), não depende do veredito do
Critic — assim dá pra detectar quando o Critic aprovou algo que falha nas
checagens estáticas.

### 5.3 Agente Revisor — `evaluate_critic` (`/evaluate/critic`)

O dataset atual não traz soluções rotuladas, então esta avaliação **exige
`samples`** no body (sem samples → `404` com mensagem explicativa; o CLI pula
a etapa avisando). Para cada amostra:

1. monta uma `RefactoringProposal` sintética com a `solution_code`
   (sem rodar o Recommender);
2. chama `service.review(problem_code, proposal)` com **até 2 tentativas** (o
   parser do Mistral falha esporadicamente em entradas longas);
3. compara `review.is_approved` com `expected_approved`:

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
  `POST /api/v1/evaluate/all`. Aceita body com até três seções
  (`detector`/`refactor`/`critic`), cada uma com seu próprio `samples`;
  Detector/Refatorador sem seção caem no dataset, o Critic precisa da sua.
- Os endpoints por agente (`/evaluate/{detector,refactor}`) também
  aceitam um body com `samples` para avaliar **código submetido**
  pelo usuário no lugar do dataset. Veja o `Readme.md` para
  o schema das amostras.
- `scripts/run_evaluation.py --all --md … --json …` produz
  `dataset/reports/evaluation.{md,json}` (o `.md` é auto-contido por seção).
- `scripts/run_multi_detector.py` roda **só o detector** sobre
  `dataset/examples/` com checkpoint JSONL resumível — útil porque cada
  arquivo custa 8 chamadas de LLM.

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
- Detector multi-label (4 fases) → [app/services/multi_detector_service.py](../app/services/multi_detector_service.py)
- Runner com checkpoint → [app/services/multi_detector_dataset_runner.py](../app/services/multi_detector_dataset_runner.py)
- Avaliação → [app/services/evaluation_service.py](../app/services/evaluation_service.py)
- Schemas trocados entre agentes → [app/core/schemas.py](../app/core/schemas.py)
- Prompts (contrato de comportamento + definições dos tipos) → [app/core/prompts.py](../app/core/prompts.py)
- Tools determinísticas → [app/tools/](../app/tools/)
- Knowledge base (PgVector + HF embeddings) → [app/knowledge/provider.py](../app/knowledge/provider.py)
- Checagens objetivas do refator → [app/services/quality_checks.py](../app/services/quality_checks.py)
- Dataset e gabarito → [dataset/](../dataset/)
