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
