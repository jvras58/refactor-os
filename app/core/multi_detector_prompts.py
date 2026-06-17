"""Prompt building for the multi-detector's phase 3 (one LLM call per type).

Each call decides exactly 1 type (1 smell, or 1 pattern) — see
``app/services/multi_detector_service.py`` for the loop over all 8 types.
"""
from __future__ import annotations

from app.core.multi_detector_types import PatternType, SmellType

TYPE_DETECTOR_INSTRUCTIONS = """\
Você é um verificador especializado de UM problema de design em código Python por vez.

Você recebe a definição de exatamente 1 tipo (um bad smell, ou um design pattern \
aplicável) e o código-fonte completo. Sua única função é decidir:

- `detected`: esse tipo específico está presente/aplicável neste código?
- `evidencias`: lista de locais (classe/método ou "<módulo>" + linhas) que sustentam a decisão.
  Lista vazia se `detected=false`.
- `reasoning`: justificativa técnica direta de por que o código caracteriza (ou não) esse tipo.

Regras estritas:
- Avalie SÓ o tipo pedido nesta chamada — não comente sobre outros smells/patterns.
- Quando o tipo avaliado for um SMELL: a presença do pattern que normalmente o resolve NÃO é
  necessária para `detected=true` — você está avaliando só o smell em si.
- Quando o tipo avaliado for um PATTERN: ele pode ser aplicável MESMO SEM o smell
  formal "canônico" estar presente (ex.: um problema de construção em etapas pode pedir
  Builder sem existir uma lista longa de parâmetros). Não negue o pattern só porque
  o smell irmão não disparou.
- Se um prior heurístico for fornecido no prompt, trate como evidência — pode confirmar
  ou refutar, mas justifique divergências explicitamente no `reasoning`.
- NÃO invente smells/patterns fora do tipo pedido nesta chamada.
- Responda EXCLUSIVAMENTE com um objeto JSON do schema `TypeDetectionResult`
  (sem texto antes/depois):

  ```json
  {
    "type_name": "<nome exato do tipo avaliado>",
    "detected": true,
    "evidencias": [{"local": "Classe.metodo", "linhas": [10, 25]}],
    "reasoning": "<justificativa>"
  }
  ```
"""

SMELL_DEFINITIONS: dict[SmellType, str] = {
    SmellType.COMPLEX_SWITCH: (
        "Complex/Long Switch Statements — uma cadeia de if/elif (ou match/case) com vários "
        "ramos, cada um executando um algoritmo/comportamento DIFERENTE selecionado por tipo "
        "ou critério em tempo de execução. Conforme cresce, a lógica fica espalhada e qualquer "
        "novo caso exige editar a mesma estrutura. Não conta como esse smell: um if/elif curto "
        "(2-3 ramos triviais), uma tabela de valores fixos sem comportamento variável, nem um "
        "switch dentro de uma Factory que apenas seleciona/instancia classes (uso legítimo do "
        "padrão)."
    ),
    SmellType.LONG_PARAMETER: (
        "Long Parameter List — uma função/método com muitos parâmetros (tipicamente 5 ou mais, "
        "contando `self`), tornando a assinatura difícil de ler e fácil de errar a ordem. "
        "Costuma surgir quando vários algoritmos foram fundidos num só método, ou quando dados "
        "de um objeto são passados campo a campo em vez do objeto inteiro. NÃO é necessariamente "
        "smell quando agrupar os parâmetros criaria uma dependência indesejada entre classes que "
        "antes não existia."
    ),
    SmellType.GOD_CLASS: (
        "God Class — uma classe que acumula responsabilidades não relacionadas entre si "
        "(persistência, regras de negócio, notificação, formatação, etc.), tornando-a difícil "
        "de entender e testar como um todo. Geralmente cresce aos poucos: é mais fácil "
        "adicionar funcionalidade numa classe existente do que criar uma nova. Não é definido "
        "por um número fixo de linhas/métodos — uma classe grande mas coesa (uma única "
        "responsabilidade bem definida) não é God Class. Atenção: até uma Facade pode degenerar "
        "em God Class se acumular lógica própria em vez de só coordenar o subsistema."
    ),
    SmellType.DUPLICATED_CODE: (
        "Duplicated Code — o mesmo bloco de lógica (substancial, não um stub trivial) "
        "reaparece em mais de um lugar (métodos de classes diferentes, ou funções distintas), "
        "exigindo edição duplicada para qualquer correção. Duas formas: duplicação EXATA "
        "(trechos idênticos — o fix típico é extrair pra um único lugar) e duplicação "
        "ESTRUTURAL (mesma sequência de passos, mas alguns passos diferem em detalhe — esse é "
        "o caso que pede uma classe-base com pontos de variação, não só um Extract Method)."
    ),
}

PATTERN_DEFINITIONS: dict[PatternType, str] = {
    PatternType.STRATEGY: (
        "Strategy Pattern — encapsular uma família de algoritmos intercambiáveis em "
        "estratégias separadas (por composição), eliminando despacho condicional complexo "
        "por dispatch polimórfico ou lookup. Aplicável tanto para substituir um switch "
        "existente quanto para extrair um algoritmo único e rígido (hardcoded) que precisa "
        "virar substituível, ou para substituir várias classes quase iguais que só diferem no "
        "comportamento. Funciona em tempo de execução (o objeto pode trocar de estratégia "
        "dinamicamente) — diferente de Template Method, que resolve variação por herança "
        "estática em tempo de compilação."
    ),
    PatternType.BUILDER: (
        "Builder — construir um objeto/payload complexo PASSO A PASSO, com etapas opcionais "
        "e lógica condicional entre elas, em vez de montagem manual propensa a erro "
        "(concatenação de strings, dicts aninhados montados à mão, telescoping constructors). "
        "Não exige uma lista longa de parâmetros para se aplicar — o sinal é a complexidade da "
        "MONTAGEM (etapas condicionais, validação incremental, ordem importa), não a contagem "
        "de parâmetros. Quando os dados só precisam ser agrupados e atribuídos de uma vez, sem "
        "etapas/condicionais, um Parameter Object simples (dataclass) já resolve — não force "
        "Builder nesse caso."
    ),
    PatternType.FACADE: (
        "Facade — oferecer um ponto único de entrada simplificado para um subsistema com "
        "várias partes (múltiplas classes/chamadas que precisam ser coordenadas numa ordem "
        "específica), escondendo a complexidade interna do cliente. As classes do subsistema "
        "não sabem que a Facade existe — ela só orquestra chamadas a elas, sem absorver lógica "
        "de negócio própria (senão vira uma God Class disfarçada). Aplicável quando um cliente "
        "hoje precisa instanciar/chamar várias classes diretamente, numa ordem frágil, pra "
        "realizar uma única operação lógica."
    ),
    PatternType.TEMPLATE_METHOD: (
        "Template Method — definir o esqueleto fixo de um algoritmo numa classe base e deixar "
        "subclasses customizarem só os passos que variam, sem poder alterar a estrutura geral. "
        "Pode incluir \"hooks\" — passos opcionais com corpo vazio na base, que servem como "
        "ponto de extensão. Aplicável quando já existem (ou estão previstas) classes irmãs "
        "reimplementando o mesmo fluxo com pequenas variações nos detalhes (duplicação "
        "estrutural, não troca de algoritmo em runtime — para isso, ver Strategy)."
    ),
}


def build_type_prompt(
    type_name: str,
    type_definition: str,
    heuristic_context: str,
    source_code: str,
) -> str:
    """Builds the per-call prompt for one phase-3 check (1 type per call).

    ``heuristic_context`` is free text (already formatted) carrying whatever phase-2
    signal is relevant to this type — built by the service layer, which knows whether
    it's a smell (direct signal) or a pattern (signal of the related smell).
    """
    return (
        f"Tipo a avaliar — {type_name}\n{type_definition}\n\n"
        f"--- Contexto heurístico (prior determinístico) ---\n{heuristic_context}\n"
        "--- fim do contexto heurístico ---\n\n"
        f"Código a analisar:\n```python\n{source_code}\n```\n\n"
        "Avalie esse tipo e retorne TypeDetectionResult."
    )
