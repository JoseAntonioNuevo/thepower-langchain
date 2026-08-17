# Cómo funciona el chatbot 04: juez, Tavily y validador

Este documento explica el ciclo de `app/graph.py` de punta a punta.
La lección 02 sigue usando el mock `buscar_clima`. Aquí el objetivo es otro:
**cada nodo tiene un solo trabajo**, y los hechos actuales salen de internet
(Tavily), no de un string fijo.

Es la cuarta parada de la [guía completa del repositorio](../00_indice.md).
Antes conviene leer [01 — grafo](01_grafo.md),
[02 — tools](02_tools.md) y [03 — memoria](03_memoria.md). Después, la
[TUI](05_tui.md), la
[observabilidad](../observability/observabilidad.md) y los
[tests](../tests.md) explican las capas que rodean este ciclo.

Ejecuta siempre desde la raíz del repo:

```bash
python langgraph/04_chatbot.py
```

Hace falta `OPENROUTER_API_KEY`. `TAVILY_API_KEY` hace falta para tiempo,
resultados y noticias reales; sin ella el grafo corre igual y `buscar_web`
devuelve `Falta TAVILY_API_KEY en .env`.

---

## Por qué hay cuatro nodos y una publicación controlada

Un solo LLM con tools elige mal: ante “temperatura exacta en BCN” pedía
`buscar_clima`, que siempre responde `Soleado en Barcelona`. Ante “quién ganó
el mundial” Tavily buscaba sin fecha y devolvía 2022.

El grafo separa responsabilidades:

| Nodo | Trabajo | ¿Busca en internet? |
|---|---|---|
| `juez` | Decide si hace falta web y propone la query | No |
| `chatbot` | Redacta o pide tools (`bind_tools`) | No |
| `tools` | Ejecuta las funciones (`ToolNode`) | Sí, si pidió `buscar_web` |
| `validador` | ¿El borrador cubre lo pedido? | No |
| `publicar` | Emite el borrador aprobado al historial del chat | No |

```
START → juez → chatbot ⇄ tools → validador → publicar → END
                    ↑               |
                    +--- reintenta -+  (como mucho una vez)
```

La TUI pinta exactamente ese dibujo: **juez**, **LLM**, **tools**,
**validador**, con las etiquetas `pide tool`, `vuelve`, `ok` y `reintenta`.

---

## El estado (`State`)

El historial de chat sigue en `messages` (reducer `add_messages`: se
añaden mensajes, no se pisan). Encima van campos de routing:

| Campo | Quién lo escribe | Para qué |
|---|---|---|
| `usar_web` | juez | El chatbot debe llamar a `buscar_web` |
| `query_web` | juez | Query concreta y fechada |
| `motivo_juez` | juez | Se muestra en la TUI y entra en la consigna |
| `ok` | validador | ¿Se puede terminar el turno? |
| `motivo_validador` | validador | Si reintenta, el juez y el chatbot lo leen |
| `intentos` | validador (+ reset del juez) | Tope de una segunda vuelta |

El juez y el validador **no** meten mensajes falsos en el chat. Devuelven
solo State. La TUI lee esos campos en `stream_mode="updates"` y pinta
trazas `juez:` / `validador:`.

`draft` es el borrador privado: no entra en `messages` ni se pinta como
respuesta hasta que `validador` devuelve `ok: si`. Solo `publicar` lo convierte
en `AIMessage` y lo añade al historial.

`InMemorySaver` recuerda el hilo (`usuario_123`) entre turnos. Por eso el
juez, cuando el último mensaje es del usuario, pone `intentos = 0`. Si no,
el tope del turno anterior bloquearía el siguiente.

---

## Nodo 1 — `juez`

Archivo de lógica pura: [`app/juez.py`](../../app/juez.py).
El nodo en sí está en [`app/graph.py`](../../app/graph.py).

1. Lee la última pregunta del usuario.
2. Llama al modelo **sin tools** (`model.invoke`, no `stream`).
3. El modelo debe responder exactamente:

```
usar_web: si|no
query: temperatura actual Barcelona 17 agosto 2026
motivo: pide un número actual
```

4. `parsear_veredicto` convierte eso en un `VeredictoJuez`.
   No usamos `with_structured_output`: Gemma vía OpenRouter no es fiable.
5. Guarda el veredicto en el State y pasa **siempre** al chatbot.
   El “si / no” no es una arista: viaja en la consigna.

Reglas que ve el juez: hechos actuales (tiempo, marcadores, noticias,
precios) → web. Saludos y opiniones → no. La query debe llevar fecha y
ser concreta.

Si es un **reintento**, el último mensaje ya no es human: es la respuesta
rechazada. Entonces el juez recibe también `motivo_validador`
(“falta el número”, “no se usó buscar_web”, …).

---

## Nodo 2 — `chatbot`

Mismo papel que en la lección 02: `bind_tools` + `stream`.

La diferencia es `consigna_sistema` ([`app/fecha_hoy.py`](../../app/fecha_hoy.py)):

- `buscar_web` es la **única** tool con internet real (Tavily).
- `buscar_clima` y `tendencia_ropa` son **mocks de clase**.
- Si el juez dijo `usar_web`, el punto 5 obliga a `buscar_web` con
  `query_web` y prohíbe los mocks.
- Si el validador rechazó, el punto 6 pide corregir.

Si el modelo pide tools, el AIMessage se guarda para que `ToolNode` pueda
ejecutarlo. Si redacta una respuesta final, el texto se guarda como `draft`
privado; todavía no es un mensaje visible.

Tras el chatbot, `_despues_chatbot` mira la última llamada:

- hay `tool_calls` → nodo `tools`
- si no → nodo `validador` (ya no se va a `END`)

---

## Nodo 3 — `tools` (Tavily)

`ToolNode(tools)` ejecuta lo que el modelo pidió. Las tools son:

| Tool | Qué es |
|---|---|
| `buscar_web` | Tavily de verdad |
| `fecha_hoy` | Calendario del sistema |
| `buscar_clima` | Mock: `Soleado en {ciudad}` |
| `tendencia_ropa` | Mock: chaqueta ligera |

[`app/buscar_web.py`](../../app/buscar_web.py) llama a Tavily así:

- antepone la fecha de hoy a la query (`17 de agosto de 2026 — …`)
- `search_depth="advanced"`
- `include_answer="advanced"`
- 5 resultados, snippets de hasta 400 caracteres

Sin `TAVILY_API_KEY` no lanza excepción: devuelve un string y el grafo
sigue. El validador verá que no hay dato usable.

Después de `tools` se vuelve al `chatbot` para que redacte (o pida otra
tool). Es el mismo bucle de la lección 02.

---

## Nodo 4 — `validador`

Archivo: [`app/validador.py`](../../app/validador.py).

Orden:

1. **Heurística** (sin red), para que el reintento se vea aunque Gemma
   sea vaga:
   - el juez pidió web y no hay `ToolMessage` de `buscar_web` → rechaza
   - la respuesta contiene `Soleado en …` (el mock) → rechaza
   - la pregunta pide temperatura/exacto y no hay ningún dígito → rechaza
2. Si la heurística no dispara, un segundo `invoke` pide:

```
ok: si|no
motivo: ...
```

3. Si `ok` es False, incrementa `intentos`.
4. `_despues_validador`:
   - `ok` → `publicar` → `END`
   - rechazo y `intentos == 1` → otra vez `juez`
   - rechazo y `intentos == 2` → `END` sin publicar el borrador (no hay bucle infinito)

El usuario nunca ve el borrador antes del `ok`. En el reintento el chatbot vuelve a ver la consigna, ahora con el motivo
del validador, y debería pedir `buscar_web` de verdad.

### Nodo 5 — `publicar`

`publicar_respuesta` es determinista: toma `draft`, crea un `AIMessage` y lo
añade a `messages`. La TUI recibe ese update después de la traza
`validador: ok`, por lo que el globo `bot` siempre aparece después de la
validación.

---

## Qué ve la TUI

[`ui/chat_tui.py`](../../ui/chat_tui.py) ya no es
`START → LLM ⇄ tools → END`. El sidebar tiene cuatro cajas.

Fases del chip:

| Fase | Leyenda |
|---|---|
| `judging` | el juez decide |
| `thinking` / `writing` | en el modelo / el modelo responde |
| `tools` | pide tool · búsqueda |
| `validating` | valida respuesta |
| `retrying` | reintenta |
| `idle` | reposo |

[`ui/chat_lines.py`](../../ui/chat_lines.py) convierte los
updates de LangGraph en filas:

- `juez: web · temperatura actual Barcelona`
- `validador: reintenta · falta el número`

Esas filas no son globos de chat: son trazas del grafo, como `pensar` o
`tool`.

---

## Un turno de ejemplo

Usuario: *qué temperatura hace ahora en Barcelona*

1. **juez** → `usar_web: si`, query `temperatura actual Barcelona 17 agosto 2026`.
2. **chatbot** lee la consigna, pide `buscar_web` (no `buscar_clima`).
3. **tools** llama a Tavily con la query fechada y devuelve °C + fuentes.
4. **chatbot** redacta un `draft`: “Ahora hay 24 °C y cielo despejado.”
5. **validador** ve un número y un `buscar_web` → `ok`.
6. **publicar** emite el globo `bot`.
7. **END**. El grafo vuelve a reposo.

Si en el paso 2 el modelo usara el mock, el validador rechazaría
(“respuesta de mock” o “falta el número”), el juez repetiría con ese
motivo, y la TUI encendería `▲ reintenta`.

---

## Mapa de ficheros

| Fichero | Rol |
|---|---|
| [`app/graph.py`](../../app/graph.py) | Monta el grafo (nodos + aristas). Se lee en clase. |
| [`langgraph/04_chatbot.py`](../../langgraph/04_chatbot.py) | Arranca la TUI sobre ese `graph`. |
| [`app/juez.py`](../../app/juez.py) | Consigna, parseo y rutas del juez. Sin red. |
| [`app/validador.py`](../../app/validador.py) | Heurística, parseo y tope de reintentos. |
| [`app/buscar_web.py`](../../app/buscar_web.py) | Cliente Tavily. |
| [`app/fecha_hoy.py`](../../app/fecha_hoy.py) | Fecha + consigna del chatbot. |
| [`ui/chat_tui.py`](../../ui/chat_tui.py) | Sidebar de cuatro nodos. |
| [`ui/chat_lines.py`](../../ui/chat_lines.py) | Updates → filas `juez` / `validador`. |

Los tests (`tests/test_juez.py`, `test_validador.py`, `test_buscar_web.py`,
TUI y líneas) no llaman a OpenRouter ni a Tavily. Desde la raíz:

```bash
python -m unittest discover -s tests
```

Para continuar:

- [TUI](05_tui.md): cómo el stream se convierte en
  filas y estados visuales.
- [Observabilidad](../observability/observabilidad.md): cómo se instrumenta este mismo
  `graph` sin copiarlo.
- [Tests](../tests.md): qué contratos se prueban sin servicios externos.
