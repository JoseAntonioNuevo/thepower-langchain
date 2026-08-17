# Clase 1 — LangGraph (5 oct 2026)

Grafo explícito → tools → memoria → chatbot. 90 min, thePower AI Engineer.

El repo enseña LangGraph en cuatro scripts. Los helpers (tools, TUI) viven en `utilities/`; los tests en `tests/`; el grafo de `04` también se exporta en `app/` para la clase de observabilidad.

## Organización

```
1-langGraph/
  lessons/           # Scripts de clase (se ejecutan desde la raíz)
    01_grafo.py
    02_tools.py
    03_memoria.py
    04_chatbot.py
  utilities/         # Tools y TUI que reutilizan 04, app y los tests
    buscar_web.py
    fecha_hoy.py
    juez.py
    validador.py
    chat_input.py
    chat_lines.py
    chat_tui.py
    consola.py
  docs/              # Explicación en español del ciclo de 04
    04_juez_validador.md
  tests/             # unittest, sin red ni OpenRouter
  app/graph.py       # Reexporta el grafo de 04, sin TUI (7 oct)
  requirements.txt
  .env.example
```

Ejecuta siempre desde la raíz del repo. Los scripts de `lessons/` y
`app/graph.py` añaden esa raíz a `sys.path` para importar `utilities`.

## Setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Pega tu clave en `.env` ([openrouter.ai/settings/keys](https://openrouter.ai/settings/keys)). `TAVILY_API_KEY` hace falta para hechos actuales (tiempo, resultados, noticias); sin ella `04` sigue el grafo y `buscar_web` avisa que falta la clave ([tavily.com](https://www.tavily.com)).

`01` no necesita claves. `02`–`04` y `app/graph.py` sí (`OPENROUTER_API_KEY`).

## Dependencias (`requirements.txt`)

| Paquete | Para qué |
|---|---|
| `langgraph` | `StateGraph`, `START`/`END`, `add_messages`, `ToolNode`, aristas condicionales, `InMemorySaver` |
| `langchain` | `@tool` (02, 04, `fecha_hoy`, `buscar_web`) |
| `langchain-core` | `HumanMessage`, `SystemMessage`, `AnyMessage`, `RunnableConfig` |
| `langchain-openrouter` | `ChatOpenRouter` (02–04, `app`) |
| `python-dotenv` | `load_dotenv()` lee `.env` (02–04, `app`) |
| `opentui` | TUI a pantalla completa de `04` (`chat_tui`) |
| `tavily-python` | Cliente de búsqueda en `buscar_web` (04 / `app`) |

Modelo: `google/gemma-4-31b-it` vía OpenRouter, Cerebras primero (`order`, no `only`). Si Cerebras da 429, OpenRouter usa otro proveedor. Espera unos segundos entre 02, 03 y 04.

## Lessons

Desde la raíz:

```bash
python lessons/01_grafo.py     # sin clave
python lessons/02_tools.py
python lessons/03_memoria.py
python lessons/04_chatbot.py   # TUI; salir/q o Esc
```

### `01_grafo.py` — un grafo es funciones + aristas (~12 min)

Sin LLM. Un nodo pasa `"hola thepower"` a mayúsculas.
La salida incluye un banner de lección, el recorrido ASCII del grafo y paneles
con el estado antes/después.

| Usa | No usa |
|---|---|
| `langgraph` (`StateGraph`, `START`, `END`) | API key, LangChain, OpenRouter, tools, TUI |

### `02_tools.py` — bind_tools + ToolNode (~18 min)

El modelo pide `buscar_clima` (mock local). Un `invoke`, sin memoria entre turnos.
La espera del modelo muestra un spinner y el resultado separa pregunta, tool
solicitada, dato devuelto y respuesta final.

| Usa | No usa |
|---|---|
| `langgraph` (`StateGraph`, `add_messages`, `ToolNode`, `tools_condition`) | Checkpointer, Tavily, OpenTUI |
| `langchain` (`@tool`) | |
| `langchain-core` (`HumanMessage`) | |
| `langchain-openrouter`, `python-dotenv` | |

### `03_memoria.py` — checkpointer + `thread_id` (~15 min)

Tres `invoke`: mismo hilo recuerda el nombre; otro hilo empieza vacío. El `State` no es la memoria.
Cada turno aparece en un panel etiquetado con su hilo y las pausas anti-429
mantienen feedback visual con un spinner.

| Usa | No usa |
|---|---|
| `langgraph` (`StateGraph`, `InMemorySaver`) | Tools, Tavily, OpenTUI |
| `langchain-core` (`HumanMessage`, `RunnableConfig`) | |
| `langchain-openrouter`, `python-dotenv` | |

### `04_chatbot.py` — juez + tools + validador + TUI (~20 min)

Cada nodo tiene un trabajo: `juez` decide si hace falta internet, `chatbot`
redacta (y puede pedir tools), `tools` ejecuta Tavily/`fecha_hoy`/mocks,
`validador` acepta o manda otra vuelta al juez (como mucho un reintento), y
`publicar` muestra al usuario el borrador solo después de un `ok`.
Cómo funciona cada nodo, el State y Tavily: [docs/04_juez_validador.md](docs/04_juez_validador.md).
Tools: `fecha_hoy`, `buscar_clima` (mock), `tendencia_ropa` (mock), `buscar_web`
(Tavily). La TUI está en `utilities/chat_tui.py` y pinta el ciclo completo.
El composer tiene foco real, caret parpadeante, edición multilínea, pegar, selección,
undo, `Enter` para enviar, `Shift+Enter` para nueva línea y `↑`/`↓` para
recuperar el historial. `Esc` o `salir`/`q` cierran la sesión.

| Usa | No usa |
|---|---|
| Todo lo de 02 y 03 | — |
| `utilities.fecha_hoy`, `utilities.buscar_web` | |
| `utilities.juez`, `utilities.validador` | |
| `utilities.chat_tui` → `opentui` | |
| `tavily-python` (vía `buscar_web`; opcional) | |

## Utilities

| Módulo | Qué hace | Dependencias |
|---|---|---|
| `fecha_hoy.py` | Tool: fecha de hoy + consigna de sistema | `langchain` (`@tool`) |
| `buscar_web.py` | Tool Tavily (advanced, query fechada); sin clave avisa | `langchain`, `tavily-python` |
| `juez.py` | Parseo del veredicto ¿usar web? y ruta tras el LLM | stdlib |
| `validador.py` | Heurística + parseo ok/reintenta (tope 1) | stdlib |
| `chat_input.py` | Historial y borrador del composer | stdlib |
| `chat_lines.py` | Parser puro: updates de LangGraph → filas de chat | stdlib |
| `chat_tui.py` | TUI OpenTUI; el grafo se pasa desde fuera | `opentui`, `langchain-core`, `chat_lines` |
| `consola.py` | Banners, paneles, grafos ASCII y spinner para 01–03 | stdlib |

## Tests

Sin red ni OpenRouter. Desde la raíz:

```bash
python -m unittest discover -s tests
```

| Test | Cubre | Extra |
|---|---|---|
| `test_fecha_hoy.py` | Texto de fecha y consigna | — |
| `test_buscar_web.py` | Formato, fecha en la query y cliente mockeado | — |
| `test_juez.py` | Parseo del veredicto y ruta tools/validador | `langchain-core` |
| `test_validador.py` | Heurística, parseo, reintentos y publicación aprobada | — |
| `test_chat_input.py` | Historial y borrador del composer | — |
| `test_chat_lines.py` | Parser de turnos (juez / tools / validador) | `langchain-core` (mensajes de fixture) |
| `test_chat_tui.py` | Layout OpenTUI (`test_render`) | `opentui` |
| `test_consola.py` | Banners, paneles, fallback y spinner | — |

## `app/graph.py` (7 oct)

Reexporta `graph`, `MODELO` y `thread_id` de `lessons/04_chatbot.py`. La clase de observabilidad lo importa y lo instrumenta; no reescribe el ciclo.

Dependencias: las de `04` excepto `opentui`.
