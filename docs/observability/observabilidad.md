# Clase 2 — Observabilidad sobre el mismo grafo

Instrumentar el grafo del 5 oct para depurar, evaluar y mejorar con datos reales.
90 min: 15 min deck + 75 min live coding.

La observabilidad responde a una pregunta distinta de la ejecución:
**¿qué ocurrió dentro del agente y dónde falló?**

El ciclo **no se reescribe**. Los scripts de [`observability/`](../../observability/) importan
el mismo `graph` que usa la Clase 1:

```python
from app.graph import MODELO, graph, thread_id
```

No hay un segundo chatbot ni una copia del ciclo. Si cambia
[`app/graph.py`](../../app/graph.py), las demos de observabilidad ven ese cambio.

Pregunta de demo: `¿Qué tiempo hace en Madrid?`. En 04 el juez marca `usar_web`
y el chatbot llama a `buscar_web`. Sin `TAVILY_API_KEY` la tool avisa y el grafo
sigue. `DEMO_FORCE_TOOL_ERROR=1` (ya en Clase 1) simula un timeout.

## Cómo ejecutar

Desde la **raíz del repo**:

```bash
source .venv/bin/activate
python observability/01_sin_obs.py
python observability/02_langsmith.py
python observability/03_langfuse.py
python observability/04_incidente.py
```

| Script | Qué enseña | Claves |
|---|---|---|
| `01_sin_obs.py` | Misma respuesta, cero árbol. Si falla, el bug es el grafo del lunes | `OPENROUTER_API_KEY` |
| `02_langsmith.py` | `LANGSMITH_*` + `invoke` = árbol. `thread_id`, `user_id` hasheado, tags. `pull_prompt` opcional | + `LANGSMITH_API_KEY` |
| `03_langfuse.py` | Mismo invoke vía Langfuse v4. `session_id` / `user_id`, scores, `shutdown()` | + `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` |
| `04_incidente.py` | `DEMO_FORCE_TOOL_ERROR=1`. El fallo de la tool en las dos UIs | LangSmith + Langfuse |

`TAVILY_API_KEY` es opcional. Copia las vars nuevas desde [`.env.example`](../../.env.example).

## Baseline: sin observabilidad

[`01_sin_obs.py`](../../observability/01_sin_obs.py) desactiva el tracing
automático y ejecuta exactamente la pregunta de la clase:

```text
¿Qué tiempo hace en Madrid?
```

Vemos el resumen de pregunta, tool, dato, respuesta y validador, pero no el
árbol interno. Es el control experimental:

- si falla aquí, el problema está en el grafo;
- si funciona aquí y falla al instrumentarlo, investigamos la integración;
- si funciona en ambos, la plataforma nos ayuda a depurar ejecuciones reales.

## LangSmith

[`02_langsmith.py`](../../observability/02_langsmith.py) activa el tracing
con variables `LANGSMITH_*` y ejecuta el grafo con `invoke()`:

```python
config = config_base(
    thread_id,
    leccion="02",
    tags=["clase-2", "langsmith", "thepower"],
)
resultado = graph.invoke({"messages": [HumanMessage(PREGUNTA)]}, config)
```

En el proyecto configurado debería aparecer un árbol parecido a:

```text
juez
└── chatbot
    └── tools
        └── chatbot
            └── validador
```

El grafo puede repetir partes según la ruta real. Los tags y el metadata
permiten filtrar las ejecuciones por clase y lección.

`pull_prompt()` intenta leer `thepower-obs:staging` desde LangSmith Hub, pero
solo lo muestra: el prompt no se inyecta en el grafo. La demo enseña la
diferencia entre versionar un prompt y cambiar la ejecución.

## Identidad e higiene

- `user_id` = `sha256("alumno-demo-thepower")[:16]`. Nunca email, DNI o teléfono.
- No uses `LANGCHAIN_TRACING_V2` / `LANGCHAIN_API_KEY` / `LANGCHAIN_PROJECT`.
- Langfuse: `from langfuse import get_client` y `from langfuse.langchain import CallbackHandler`. Host = `LANGFUSE_BASE_URL`, no `LANGFUSE_HOST`.
- En un CLI corto, `langfuse.shutdown()` o se pierde el batch.
- No imprimas claves ni las mandes a las trazas.

`thread_id` recibe un sufijo de la lección para no mezclar trazas entre scripts:

```text
usuario_123-c2-02
```

## Langfuse v4

[`03_langfuse.py`](../../observability/03_langfuse.py) usa el SDK v4:

1. `get_client()` crea el cliente;
2. `CallbackHandler()` conecta las llamadas LangChain;
3. `start_as_current_observation()` abre un span de la demo;
4. `propagate_attributes()` fija `user_id`, `session_id` y tags;
5. `graph.invoke()` ejecuta el mismo grafo;
6. `score_trace()` registra scores;
7. `shutdown()` vacía el batch antes de que termine el CLI.

La sesión de Langfuse es el `thread_id` de la lección. Los tres scores son
didácticos, no un segundo juez:

| Score | Valor `1.0` cuando… |
|---|---|
| `tool_success` | hay datos de tool y no se detecta error |
| `answer_quality` | existe una respuesta |
| `latency_sla` | la ejecución tarda menos de 30 segundos |

Los scores permiten practicar evaluación y filtros sin implementar todavía
un sistema de revisión humana.

## Incidente reproducible

[`04_incidente.py`](../../observability/04_incidente.py) activa:

```text
DEMO_FORCE_TOOL_ERROR=1
```

Las tools levantan un `TimeoutError` simulado. No se llama a Tavily ni se
provoca un fallo real de red. La pregunta para el alumno es localizar el
fallo en el árbol:

1. ¿El juez decidió mal?
2. ¿El modelo pidió la tool?
3. ¿`ToolNode` falló?
4. ¿El validador reintentó o cerró?
5. ¿El fallback que llega al usuario es entendible?

El valor educativo está en comparar el mismo incidente en LangSmith y
Langfuse.

## `_comun.py`: piezas compartidas

[`_comun.py`](../../observability/_comun.py) evita copiar código entre las demos:

- `preparar_entorno()` carga el `.env` de la raíz;
- `asegurar_var()` comprueba una variable sin imprimir su valor;
- `activar_langsmith()` y `asegurar_langfuse()` preparan cada plataforma;
- `config_base()` construye `thread_id`, tags y metadata;
- `resumen()` convierte el State final en datos legibles;
- `puntuaciones()` calcula los tres scores de aula;
- `imprimir_resumen()` usa los mismos paneles de la Clase 1.

La observabilidad se añade en el borde de ejecución. El núcleo del grafo sigue
siendo el de [`04_juez_validador.md`](../langgraph/04_juez_validador.md).

## Dónde mirar

- LangSmith: proyecto `LANGSMITH_PROJECT` (por defecto `thepower-clase-2`). Árbol juez → chatbot → tools → validador.
- Langfuse (EU): `https://cloud.langfuse.com`. `session_id` = `usuario_123-c2-0X`. Scores: `tool_success`, `answer_quality`, `latency_sla`.

Buenas prácticas que se enseñan en esta clase:

- usa `LANGSMITH_TRACING`, no nombres antiguos `LANGCHAIN_*`;
- usa `LANGFUSE_BASE_URL`, no `LANGFUSE_HOST`;
- no imprimas valores de claves;
- en un proceso corto llama siempre a `langfuse.shutdown()`;
- empieza por el baseline sin tracing antes de culpar a la instrumentación.

## Mapa de ficheros

| Fichero | Papel |
|---|---|
| [`app/graph.py`](../../app/graph.py) | Define el grafo, modelo e hilo |
| [`01_sin_obs.py`](../../observability/01_sin_obs.py) | Baseline |
| [`02_langsmith.py`](../../observability/02_langsmith.py) | Árbol LangSmith |
| [`03_langfuse.py`](../../observability/03_langfuse.py) | Traces y scores Langfuse |
| [`04_incidente.py`](../../observability/04_incidente.py) | Timeout reproducible |
| [`_comun.py`](../../observability/_comun.py) | Configuración y resumen compartidos |
