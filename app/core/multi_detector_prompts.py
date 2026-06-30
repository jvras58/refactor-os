"""Prompt building for the multi-detector's phase 3 (paired LLM verification).

Each LLM call decides exactly 2 independent types (2 smells, or 2 patterns) in one
shot — see ``app/services/multi_detector_service.py`` for the pairing/grouping.
"""
from __future__ import annotations

from app.core.multi_detector_types import PatternType, SmellType

PAIR_DETECTOR_INSTRUCTIONS = """\
Você é um verificador especializado de UM par de problemas de design em código Python.

Você recebe a definição de exatamente 2 tipos independentes (podem ser 2 bad smells, ou \
2 design patterns aplicáveis) e o código-fonte completo. Sua única função é decidir, \
para CADA um dos 2 tipos, separadamente:

- `detected`: esse tipo específico está presente/aplicável neste código?
- `evidencias`: lista de locais (classe/método ou "<módulo>" + linhas) que sustentam a decisão.
  Lista vazia se `detected=false`.
- `reasoning`: justificativa técnica direta de por que o código caracteriza (ou não) esse tipo.

Regras estritas:
- Os 2 tipos são AVALIADOS DE FORMA TOTALMENTE INDEPENDENTE. A presença de um não implica
  nem exclui o outro — não force uma resposta para "casar" os dois.
- Quando o tipo avaliado for um SMELL: a presença do pattern correspondente NÃO é
  necessária para `detected=true` — você está avaliando só o smell em si.
- Quando o tipo avaliado for um PATTERN: ele pode ser aplicável MESMO SEM o smell
  formal "canônico" estar presente (ex.: um problema de construção em etapas pode pedir
  Builder sem existir uma lista longa de parâmetros). Não negue um pattern só porque
  o smell irmão não disparou.
- Se um prior heurístico for fornecido no prompt, trate como evidência — pode confirmar
  ou refutar, mas justifique divergências explicitamente no `reasoning`.
- NÃO invente smells/patterns fora dos 2 tipos pedidos nesta chamada.
- Responda EXCLUSIVAMENTE com um objeto JSON do schema `PairedDetectionResponse`
  (sem texto antes/depois):

  ```json
  {
    "result_a": {
      "type_name": "<nome exato do tipo A>",
      "detected": true,
      "evidencias": [{"local": "Classe.metodo", "linhas": [10, 25]}],
      "reasoning": "<justificativa>"
    },
    "result_b": {
      "type_name": "<nome exato do tipo B>",
      "detected": false,
      "evidencias": [],
      "reasoning": "<justificativa>"
    }
  }
  ```
"""

SMELL_DEFINITIONS: dict[SmellType, str] = {
    SmellType.COMPLEX_SWITCH: (
        "Complex/Long Switch Statements — uma cadeia de if/elif (ou match/case) com vários "
        "ramos, cada um executando um algoritmo/comportamento DIFERENTE selecionado por tipo "
        "ou critério em tempo de execução. Não conta como esse smell um if/elif curto (2-3 "
        "ramos triviais) nem uma tabela de valores fixos sem comportamento variável."
    ),
    SmellType.LONG_PARAMETER: (
        "Long Parameter List — uma função/método com muitos parâmetros (tipicamente 5 ou mais, "
        "contando `self`), tornando a assinatura difícil de ler e fácil de errar a ordem."
    ),
    SmellType.GOD_CLASS: (
        "God Class — uma classe que acumula responsabilidades não relacionadas entre si "
        "(persistência, regras de negócio, notificação, formatação, etc.), tornando-a difícil "
        "de entender e testar como um todo."
    ),
    SmellType.DUPLICATED_CODE: (
        "Duplicated Code — o mesmo bloco de lógica (substancial, não um stub trivial) "
        "reaparece em mais de um lugar (métodos de classes diferentes, ou funções distintas), "
        "exigindo edição duplicada para qualquer correção."
    ),
}

PATTERN_DEFINITIONS: dict[PatternType, str] = {
    PatternType.STRATEGY: (
        "Strategy Pattern — encapsular uma família de algoritmos intercambiáveis em "
        "estratégias separadas, eliminando despacho condicional complexo por dispatch "
        "polimórfico ou lookup. Aplicável tanto para substituir um switch existente quanto "
        "para extrair um algoritmo único e rígido (hardcoded) que precisa virar substituível."
    ),
    PatternType.BUILDER: (
        "Builder — construir um objeto/payload complexo passo a passo (ou a partir de campos "
        "opcionais/condicionais), em vez de montagem manual propensa a erro (concatenação de "
        "strings, dicts aninhados montados à mão, parâmetros demais). Não exige uma lista longa "
        "de parâmetros para se aplicar — o sinal é a complexidade da MONTAGEM, não a contagem."
    ),
    PatternType.FACADE: (
        "Facade — oferecer um ponto único de entrada simplificado para um subsistema com "
        "várias partes (múltiplas classes/chamadas que precisam ser coordenadas numa ordem "
        "específica), escondendo a complexidade interna do cliente."
    ),
    PatternType.TEMPLATE_METHOD: (
        "Template Method — definir o esqueleto fixo de um algoritmo numa classe base e deixar "
        "subclasses customizarem só os passos que variam. Aplicável quando já existem (ou estão "
        "previstas) classes irmãs reimplementando o mesmo fluxo com pequenas variações."
    ),
}


def build_pair_prompt(
    type_a_name: str,
    type_a_definition: str,
    type_b_name: str,
    type_b_definition: str,
    heuristic_context: str,
    source_code: str,
) -> str:
    """Builds the per-call prompt for one paired phase-3 check.

    ``heuristic_context`` is free text (already formatted) carrying whatever phase-2
    signal is relevant to this pair — built by the service layer, which knows whether
    each type is a smell (direct signal) or a pattern (signal of the related smell).
    """
    return (
        f"Tipo A — {type_a_name}\n{type_a_definition}\n\n"
        f"Tipo B — {type_b_name}\n{type_b_definition}\n\n"
        f"--- Contexto heurístico (prior determinístico) ---\n{heuristic_context}\n"
        "--- fim do contexto heurístico ---\n\n"
        f"Código a analisar:\n```python\n{source_code}\n```\n\n"
        "Avalie os 2 tipos de forma independente e retorne PairedDetectionResponse."
    )
