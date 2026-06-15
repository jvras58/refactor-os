# Lições — avaliando modelos locais (Ollama)

Registro de uma investigação real: ao rodar o pipeline com um modelo **local de 7B**,
o estágio Refator dava ~0% de código válido. A conclusão precipitada foi *"modelo
pequeno não sabe refatorar"*. Estava errada — o código gerado era bom; o problema
estava em **como o pipeline tratava a saída**. Eram **dois bugs**.

## Sintoma

Com `qwen2.5-coder:7b`/`mistral` local, toda proposta de refatoração reprovava em
`syntax_valid`, mesmo com `pattern_correct=true`. Parecia incapacidade do modelo.

## Bug 1 — CONFIRMADO: indentação após decorador

Ao emitir o código como **string JSON**, o modelo perdia a indentação da linha
imediatamente **após um decorador**:

```python
class ShippingStrategy(ABC):
    @abstractmethod
def calculate(self, weight_kg):   # <- veio na coluna 0 → SyntaxError no arquivo inteiro
        pass
```

Uma única linha desindentada invalida o arquivo todo. O resto do código estava
perfeitamente formatado — só a linha pós-decorador quebrava.

**Correção:** [`app/services/code_repair.py`](../app/services/code_repair.py) —
`repair_refactored_code` re-indenta o `def`/`class` que segue um decorador para casar
com a indentação do decorador. É **puramente estrutural** (não altera tokens/lógica) e
**no-op** em código bem-formado, então roda em toda proposta antes do Critic/avaliação.
Provado reproduzindo no output real + testes em
[`tests/test_code_repair.py`](../tests/test_code_repair.py).

## Bug 2 — TEORIA (refutada): a 2ª passada do `parser_model`

A arquitetura usa um **`parser_model`** (2ª chamada ao LLM só para extrair o JSON
estruturado — um *workaround do Mistral*, cujo JSON-mode não coexiste com tool calls).
**Hipótese:** essa re-serialização corrompia o código. Desligamos o `parser_model` para
o Ollama e uma rodada saiu **perfeita** → parecia confirmado.

**Era um falso positivo.** Aquela rodada, por acaso, não usou decorador (`raise
NotImplementedError()` em vez de `@abstractmethod`). Num **teste controlado**, o erro de
sintaxe **voltou** com `@abstractmethod` — provando que o `parser_model` **não** era a
causa (era o Bug 1 o tempo todo).

> **Lição metodológica:** quase aceitamos uma conclusão com base em **uma única
> observação favorável**. Só um teste controlado, variando uma coisa por vez, revelou a
> causa real. Confirmação não é uma amostra de sorte.

O `parser_model` ficou **desligado no Ollama mesmo assim** — esse provider faz structured
output nativo, então é **uma chamada a menos por estágio** (mais rápido). Ver
[`app/core/llm.py`](../app/core/llm.py).

## Melhoria correlata — preservação da API pública

Depois de consertada a sintaxe, faltava `logic_preserved`: o modelo trocava o ponto de
entrada público (ex.: `calculate_shipping(country, weight_kg)`) por um novo nome. Um
reforço estrito no `RECOMMENDER_INSTRUCTIONS` ([prompts.py](../app/core/prompts.py))
exige manter toda função/classe/método público com o mesmo nome e assinatura, usando um
wrapper fino que delega para a estrutura nova.

## Resultado

No problema `01_complex_switch`, após os consertos: `is_correct` passou de **False → True**,
aprovado pelo Critic na 1ª iteração.

**Mensagem central:** o gargalo não era a capacidade do modelo, e sim o **tratamento da
saída** no pipeline. E validar a hipótese com teste controlado evitou uma conclusão errada.

> Nota: o `is_correct=True` acima é de **um** problema. Os números agregados sobre os 10
> problemas saem dos relatórios em `dataset/reports/` quando a avaliação completa fecha.
