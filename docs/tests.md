# Tests: contratos locales sin red

Los tests del repositorio están diseñados para comprobar la lógica que
controlamos. No necesitan OpenRouter, Tavily ni una terminal interactiva real.

Desde la raíz:

```bash
python -m unittest discover -s tests
```

## Qué se prueba y qué no

Un test no intenta demostrar que Gemma siempre responde bien ni que Tavily
siempre está disponible. Comprueba contratos observables:

- un texto se formatea como esperamos;
- un parser entiende `clave: valor`;
- una ruta manda al nodo correcto;
- una tool construye la query correcta;
- una respuesta se publica solo después de `ok`;
- la TUI pinta lo que recibe.

Las llamadas externas se sustituyen con `unittest.mock.patch`. Así el test es
rápido, determinista y no consume cuota.

## Mapa de tests

| Test | Qué cubre | Por qué importa |
|---|---|---|
| [`test_fecha_hoy.py`](../tests/test_fecha_hoy.py) | Fechas en español y consignas | El modelo debe conocer el día actual y distinguir mocks de web |
| [`test_buscar_web.py`](../tests/test_buscar_web.py) | Query fechada, formato, clave ausente y cliente mockeado | La tool puede fallar sin romper el contrato del grafo |
| [`test_juez.py`](../tests/test_juez.py) | Parseo de `usar_web`, rutas y turno nuevo | El juez debe dejar una decisión utilizable aunque el texto sea imperfecto |
| [`test_validador.py`](../tests/test_validador.py) | Heurística, parseo, evidencia y límite de reintentos | No publicar respuestas sin evidencia ni permitir bucles infinitos |
| [`test_chat_input.py`](../tests/test_chat_input.py) | Historial, borrador y posición del cursor | El composer debe comportarse como un editor pequeño |
| [`test_chat_lines.py`](../tests/test_chat_lines.py) | Mensajes y updates a `ChatLine` | La presentación no debe depender del historial de turnos antiguos |
| [`test_chat_tui.py`](../tests/test_chat_tui.py) | Layout, teclado, Markdown, fases y eventos | Se comprueba la interfaz sin abrir una terminal real |
| [`test_consola.py`](../tests/test_consola.py) | Paneles, colores, spinner y ASCII | Las lecciones 01–03 tienen una salida estable |

## Parsear salidas del LLM

El juez y el validador piden formatos etiquetados:

```text
usar_web: si
query: temperatura actual Barcelona
motivo: pide un número actual
```

```text
ok: si
motivo: incluye la temperatura
```

El código no usa `with_structured_output` para estas demos porque el modelo y
proveedor pueden devolver formatos variables. En su lugar,
`parsear_veredicto()` acepta `si`, `sí`, `yes`, `true` y `1`, y tiene
fallbacks explícitos:

- un juez ilegible no obliga a gastar una búsqueda;
- un validador ilegible rechaza para que el ciclo pueda mostrar un reintento.

Los tests de [`test_juez.py`](../tests/test_juez.py) y
[`test_validador.py`](../tests/test_validador.py) fijan esos contratos.

## Probar la búsqueda sin internet

`test_buscar_web.py` comprueba tres niveles:

1. `_query_fechada()` antepone `17 de agosto de 2026`;
2. `_formatear_busqueda()` mezcla `answer`, títulos, snippets y URLs;
3. `TavilyClient` está mockeado y se verifica la llamada con
   `search_depth="advanced"`, cinco resultados y timeout de 15 segundos.

También se prueban:

- ausencia de `TAVILY_API_KEY` → `FALTA_CLAVE`;
- payload vacío → `Sin resultados.`;
- excepción del cliente → `Error de búsqueda: ...`.

No se necesita una cuenta Tavily para verificar ninguna de estas ramas.

## Probar juez, validador y publicación

Los tests de 04 comprueban reglas que no deben depender de la suerte del LLM:

- si el juez exige web y no hubo `buscar_web`, se rechaza;
- `Soleado en ...` identifica el mock de clima;
- una pregunta de temperatura sin dígitos se rechaza;
- una temperatura con dígitos pasa la heurística;
- el validador recibe la evidencia del `ToolMessage`;
- `chatbot()` guarda el texto en `draft`, no en `messages`;
- `publicar_respuesta()` crea el `AIMessage` solo con un borrador aprobado;
- el primer rechazo vuelve a `juez`, el segundo termina.

El test de evidencia parchea `app.graph.model`; no llama al modelo
real.

## Probar la TUI sin TTY

`opentui.test_render()` crea un renderer de prueba y permite capturar el frame
como texto. Los tests verifican:

- header, sidebar, `START`, `END` y nombres de tools;
- Enter envía y Shift+Enter inserta una línea;
- pegar texto multilínea funciona;
- las flechas recuperan y restauran borradores;
- Esc cierra;
- no se puede enviar mientras `busy=True`;
- Markdown se renderiza sin `**` ni encabezados crudos;
- respuestas largas conservan el composer visible;
- los datos de Tavily no muestran URLs largas ni ruido;
- `aplicar_evento()` cambia entre `judging`, `tools`, `validating` y `retrying`.

El test no arranca `run_tui()` porque esa función exige stdin/stdout TTY. Se
prueba la aplicación desde sus señales y callbacks.

## Cómo leer un fallo

Empieza por la capa más pequeña:

1. `test_juez.py` o `test_validador.py` si falla una ruta;
2. `test_buscar_web.py` si falla una query o un fallback;
3. `test_chat_lines.py` si el evento correcto no aparece como fila;
4. `test_chat_tui.py` si la fila existe pero no se pinta;
5. `test_consola.py` si la salida de una lección está desalineada.

Esta separación ayuda a no arreglar un problema de render cuando el dato ya
llegó mal desde el grafo.

## Mapa de ficheros

| Fichero | Código que protege |
|---|---|
| [`tests/test_juez.py`](../tests/test_juez.py) | [`app/juez.py`](../app/juez.py) |
| [`tests/test_validador.py`](../tests/test_validador.py) | [`app/validador.py`](../app/validador.py) y [`app/graph.py`](../app/graph.py) |
| [`tests/test_buscar_web.py`](../tests/test_buscar_web.py) | [`app/buscar_web.py`](../app/buscar_web.py) |
| [`tests/test_chat_lines.py`](../tests/test_chat_lines.py) | [`ui/chat_lines.py`](../ui/chat_lines.py) |
| [`tests/test_chat_tui.py`](../tests/test_chat_tui.py) | [`ui/chat_tui.py`](../ui/chat_tui.py) |

El objetivo no es tener tests que cubran cada línea. Es fijar los contratos
que permiten cambiar el modelo, la TUI o el proveedor sin perder el control
del flujo.
