# Clase 1 — LangGraph (5 oct 2026)

Grafo explícito → tools → memoria → chatbot. 90 min, thePower AI Engineer.

El repo enseña LangGraph en cuatro scripts de `langgraph/`. El agente vive en
`app/`; la consola y la TUI en `ui/`; los tests en `tests/`. La clase de
observabilidad (`observability/`) importa el mismo grafo.

## Organización

```
1-langGraph/
  langgraph/            # Scripts del 5 oct (se ejecutan desde la raíz)
    01_grafo.py
    02_tools.py
    03_memoria.py
    04_chatbot.py    # Arranca la TUI; el ciclo vive en app/graph.py
  observability/            # Scripts del 7 oct: LangSmith + Langfuse
    01_sin_obs.py
    02_langsmith.py
    03_langfuse.py
    04_incidente.py
    _comun.py
  app/               # Grafo, juez, validador y tools
    graph.py
    juez.py
    validador.py
    fecha_hoy.py
    buscar_web.py
  ui/                # Consola de 01–03 y TUI de 04
    consola.py
    chat_input.py
    chat_lines.py
    chat_tui.py
  docs/
    00_indice.md
    langgraph/
    observability/observabilidad.md
    tests.md
  tests/             # unittest, sin red ni OpenRouter
  requirements.txt
  .env.example
```

Ejecuta siempre desde la raíz del repo. Los scripts de `langgraph/` y `observability/`
añaden esa raíz al final de `sys.path` para importar `app` y `ui` sin tapar
el paquete `langgraph`.

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
| `langsmith` | Trazas de Clase 2 (`LANGSMITH_TRACING`) |
| `langfuse` | Trazas y scores de Clase 2 (SDK v4) |

Modelo: `google/gemma-4-31b-it` vía OpenRouter, Cerebras primero (`order`, no `only`). Si Cerebras da 429, OpenRouter usa otro proveedor. Espera unos segundos entre 02, 03 y 04.

## Clase 1

Desde la raíz:

```bash
python langgraph/01_grafo.py     # sin clave
python langgraph/02_tools.py
python langgraph/03_memoria.py
python langgraph/04_chatbot.py   # TUI; salir/q o Esc
```

### `01_grafo.py` — un grafo es funciones + aristas (~12 min)

Sin LLM. Un nodo pasa `"hola thepower"` a mayúsculas.
La salida incluye un banner de lección, el recorrido ASCII del grafo y paneles
con el estado antes/después.
Explicación paso a paso: [docs/langgraph/01_grafo.md](docs/langgraph/01_grafo.md).

| Usa | No usa |
|---|---|
| `langgraph` (`StateGraph`, `START`, `END`) | API key, LangChain, OpenRouter, tools, TUI |

### `02_tools.py` — bind_tools + ToolNode (~18 min)

El modelo pide `buscar_clima` (mock local). Un `invoke`, sin memoria entre turnos.
La espera del modelo muestra un spinner y el resultado separa pregunta, tool
solicitada, dato devuelto y respuesta final.
Explicación del protocolo de tools: [docs/langgraph/02_tools.md](docs/langgraph/02_tools.md).

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
Explicación de memoria y checkpointer: [docs/langgraph/03_memoria.md](docs/langgraph/03_memoria.md).

| Usa | No usa |
|---|---|
| `langgraph` (`StateGraph`, `InMemorySaver`) | Tools, Tavily, OpenTUI |
| `langchain-core` (`HumanMessage`, `RunnableConfig`) | |
| `langchain-openrouter`, `python-dotenv` | |

### `04_chatbot.py` — juez + tools + validador + TUI (~20 min)

El ciclo vive en [`app/graph.py`](app/graph.py). Cada nodo tiene un trabajo:
`juez` decide si hace falta internet, `chatbot` redacta (y puede pedir tools),
`tools` ejecuta Tavily/`fecha_hoy`/mocks, `validador` acepta o manda otra
vuelta al juez (como mucho un reintento), y `publicar` muestra al usuario el
borrador solo después de un `ok`.
Cómo funciona cada nodo, el State y Tavily: [docs/langgraph/04_juez_validador.md](docs/langgraph/04_juez_validador.md).
Tools: `fecha_hoy`, `buscar_clima` (mock), `tendencia_ropa` (mock), `buscar_web`
(Tavily). La TUI está en `ui/chat_tui.py` y pinta el ciclo completo.
La capa de interfaz se explica en
[docs/langgraph/05_tui.md](docs/langgraph/05_tui.md).
El composer tiene foco real, caret parpadeante, edición multilínea, pegar, selección,
undo, `Enter` para enviar, `Shift+Enter` para nueva línea y `↑`/`↓` para
recuperar el historial. `Esc` o `salir`/`q` cierran la sesión.

| Usa | No usa |
|---|---|
| Todo lo de 02 y 03 | — |
| `app.fecha_hoy`, `app.buscar_web` | |
| `app.juez`, `app.validador` | |
| `ui.chat_tui` → `opentui` | |
| `tavily-python` (vía `buscar_web`; opcional) | |

## `app/` y `ui/`

Descripción didáctica de la interfaz: [docs/langgraph/05_tui.md](docs/langgraph/05_tui.md).

| Módulo | Qué hace | Dependencias |
|---|---|---|
| `app/fecha_hoy.py` | Tool: fecha de hoy + consigna de sistema | `langchain` (`@tool`) |
| `app/buscar_web.py` | Tool Tavily (advanced, query fechada); sin clave avisa | `langchain`, `tavily-python` |
| `app/juez.py` | Parseo del veredicto ¿usar web? y ruta tras el LLM | stdlib |
| `app/validador.py` | Heurística + parseo ok/reintenta (tope 1) | stdlib |
| `app/graph.py` | State, nodos y grafo compilado | LangGraph, OpenRouter |
| `ui/chat_input.py` | Historial y borrador del composer | stdlib |
| `ui/chat_lines.py` | Parser puro: updates de LangGraph → filas de chat | stdlib |
| `ui/chat_tui.py` | TUI OpenTUI; el grafo se pasa desde fuera | `opentui`, `langchain-core`, `chat_lines` |
| `ui/consola.py` | Banners, paneles, grafos ASCII y spinner para 01–03 | stdlib |

## Tests

Qué se prueba y por qué: [docs/tests.md](docs/tests.md).

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

Define `graph`, `MODELO` y `thread_id`. La clase de observabilidad lo importa
y lo instrumenta; no reescribe el ciclo.

Dependencias: las de `04` excepto `opentui`.

Mapa general y orden de lectura: [docs/00_indice.md](docs/00_indice.md).

## Clase 2 — 7 oct

Observabilidad sobre **el mismo grafo**: [`observability/`](observability/).
Los scripts importan `app/graph.py`; no hay un segundo agente.

La pregunta de demo es el tiempo en Madrid. El juez de 04 manda a `buscar_web`
(Tavily opcional). `DEMO_FORCE_TOOL_ERROR=1` ya está en las tools de Clase 1.

```bash
python observability/01_sin_obs.py
python observability/02_langsmith.py
python observability/03_langfuse.py
python observability/04_incidente.py
```

Setup, claves y arquitectura: [docs/observability/observabilidad.md](docs/observability/observabilidad.md).
