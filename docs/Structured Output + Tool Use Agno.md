# Structured Output + Tool Use na Agno

## O problema com Groq

A API do Groq retorna o seguinte erro quando você tenta combinar `output_schema` (saída estruturada via JSON mode) com `tools`:

```
json mode cannot be combined with tool/function calling
```

Isso é uma **limitação do provedor Groq**, não da Agno. A API deles aceita um ou outro:
- `response_format: json_object` (json mode) **OU**
- `tools: [...]` (function calling)

Mas nunca os dois na mesma requisição.

## Por que isso acontece

Quando você define `output_schema=MeuSchema` no `Agent`, a Agno instrui o modelo a responder em JSON validado contra o schema. No Groq, isso é traduzido para `response_format`, que entra em conflito direto com `tools`.

## Tentativas de contorno (e por que falham com Groq)

| Estratégia | Funciona com Groq? |
|---|---|
| `output_schema` + `tools` | Não — conflito direto |
| `output_schema` + `parser_model=Groq` | Não — o parser cria uma tool fantasma a partir do schema, reintroduzindo o conflito |
| `output_schema` + `output_model=Groq` | Não — o json mode ainda é aplicado em algum passo |

A saída para usar Groq é trocar o `parser_model`/`output_model` por outro provedor (Gemini, Mistral, Ollama local) que suporte structured output nativo.

## Por que Mistral não tem esse problema

O Mistral suporta **structured output e tool use simultaneamente** numa única requisição. Você passa tools e um `response_format` com schema, e o modelo:

1. Decide se precisa chamar tools
2. Executa o ciclo de tool calls
3. Retorna a resposta final já formatada conforme o schema

A Agno documenta isso explicitamente no exemplo `structured-output-with-tool-use`, que combina `DuckDuckGoTools` com um `output_schema` Pydantic, sem precisar de `parser_model` ou `output_model`.

## Padrão recomendado

```py
from agno.agent import Agent
from agno.models.mistral import MistralChat
from pydantic import BaseModel

class MinhaResposta(BaseModel):
    campo: str

agent = Agent(
    model=MistralChat(id="mistral-medium-latest"),
    tools=[minha_tool],
    output_schema=MinhaResposta,
)
```

Simples, sem hacks de modelos auxiliares.

## Outros provedores que combinam tools + structured output nativamente

- **OpenAI** (gpt-4o, gpt-4o-mini)
- **Anthropic** (Claude)
- **Google Gemini**
- **Mistral**
- **Cerebras**
- **Cohere**

## Quando usar `parser_model` / `output_model`

Conforme a doc `/input-output/output-model`:
- **`parser_model`**: quando o modelo primário não suporta structured output, usa um segundo modelo só para extrair/estruturar a saída
- **`output_model`**: quando o primário não tem o formato desejado, delega a geração final estruturada a outro modelo

Esses padrões são úteis com modelos locais (Ollama, llama.cpp) ou provedores limitados como o Groq, **desde que o modelo auxiliar suporte structured output nativamente**.


(Mistral: Structured Output with Tool Use)[/examples/models/mistral/structured-output-with-tool-use]
(Output Model)[/input-output/output-model]
(Structured Output for Agents)[/input-output/structured-output/agent]
