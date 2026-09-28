# Lección 02 — Tools: `bind_tools` + `ToolNode`

Esta lección conecta un LLM al grafo. El modelo no ejecuta Python
directamente: solicita una tool con nombre y argumentos, y LangGraph la
ejecuta de forma controlada.

```bash
python langgraph/02_tools.py
```

Hace falta `OPENROUTER_API_KEY`. La tool `buscar_clima` es un mock local, así
que esta lección no necesita Tavily ni red de búsqueda.

## Por qué usamos un mock

```python
@tool
def buscar_clima(ciudad: str) -> str:
    """Devuelve el tiempo actual en una ciudad (mock para la clase)."""
    return f"Soleado en {ciudad}"
```

El decorador `@tool` convierte la función en una herramienta que LangChain
puede describir al modelo. El nombre, el tipo de `ciudad` y el docstring forman
parte del contrato que el LLM lee.

El resultado fijo es útil en clase porque elimina variables externas. No es un
servicio meteorológico real: para hechos actuales, el agente de 04 usa
`buscar_web`.

## Dos objetos que deben coincidir

```python
tools = [buscar_clima]
model_with_tools = model.bind_tools(tools)
```

La lista se pasa dos veces por una razón:

1. `bind_tools(tools)` enseña al modelo qué puede solicitar.
2. `ToolNode(tools)` sabe qué función Python ejecutar cuando llega la solicitud.

Si el modelo pide `buscar_clima(ciudad="Madrid")`, la ejecución conceptual es:

```text
AIMessage(tool_calls=[buscar_clima(...)])
        ↓
ToolNode
        ↓
ToolMessage("Soleado en Madrid")
```

Después el resultado vuelve al modelo para que redacte una respuesta humana.

## El estado es un historial de mensajes

```python
class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
```

`messages` puede contener `HumanMessage`, `AIMessage` y `ToolMessage`.
`add_messages` es un reducer: cuando un nodo devuelve mensajes nuevos, se
añaden a la lista en lugar de reemplazar todo el historial.

El nodo del asistente es pequeño:

```python
def chatbot(state: State) -> dict:
    response = model_with_tools.invoke(state["messages"])
    return {"messages": [response]}
```

La respuesta del modelo puede ser texto o un `AIMessage` con `tool_calls`.
El nodo siguiente depende de cuál de los dos casos haya ocurrido.

## La arista condicional

```python
builder.add_node("chatbot", chatbot)
builder.add_node("tools", ToolNode(tools))
builder.add_edge(START, "chatbot")
builder.add_conditional_edges("chatbot", tools_condition)
builder.add_edge("tools", "chatbot")
```

`tools_condition` mira el último `AIMessage`:

- si tiene `tool_calls`, entra en `tools`;
- si no, termina el grafo;
- después de ejecutar una tool, la arista vuelve a `chatbot`.

```text
START → chatbot ⇄ tools
             └──────→ END  cuando no hay tool_calls
```

El bucle no significa que la tool llame al modelo. Significa que el modelo
recibe el `ToolMessage` y decide si ya puede responder o necesita otra
herramienta.

## Qué muestra el script

La pregunta de ejemplo es `¿Qué tiempo hace en Madrid?`. La salida separa:

1. **Pregunta**: el `HumanMessage`.
2. **Tool solicitada**: el nombre y argumentos encontrados en `AIMessage`.
3. **Dato devuelto**: el contenido del `ToolMessage`.
4. **Respuesta**: el último mensaje del modelo.

Separar estas cuatro piezas permite ver el protocolo, no solo el texto final.

## Modelo y proveedor

El código usa `ChatOpenRouter` con `openai/gpt-6-luna`, `temperature=0`,
`reasoning.effort` `none` y `service_tier` `priority`.

`none` no es una preferencia de estilo: en Chat Completions, GPT-6 Luna solo
acepta function calling con ese effort. `priority` es el modo rápido. En este
cliente el alias `fast` no se aplica y la respuesta vuelve como `default`.

El interruptor `DEMO_FORCE_TOOL_ERROR=1` hace que el mock lance un
`TimeoutError`. Sirve para practicar observabilidad sin tocar una API real.

## Qué usa y qué no usa

| Usa | No usa |
|---|---|
| `StateGraph`, `ToolNode`, `tools_condition` | Checkpointer |
| `@tool` y `bind_tools` | Memoria entre invocaciones |
| `HumanMessage` y `AnyMessage` | Tavily |
| OpenRouter y `python-dotenv` | OpenTUI |

## Mapa de ficheros

| Fichero | Papel |
|---|---|
| [`langgraph/02_tools.py`](../../langgraph/02_tools.py) | Modelo, mock, nodo y ciclo de tools |
| [`app/fecha_hoy.py`](../../app/fecha_hoy.py) | En 04, una tool determinista adicional |
| [`app/buscar_web.py`](../../app/buscar_web.py) | En 04, la tool real de Tavily |
| [`tests/test_buscar_web.py`](../../tests/test_buscar_web.py) | Testea Tavily con `TavilyClient` mockeado |

La siguiente lección añade memoria a este historial mediante un checkpointer:
[`03_memoria.md`](03_memoria.md).
