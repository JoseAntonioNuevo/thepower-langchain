# Tu guion de directo · Clase 1: LangGraph

**Lunes 5 de octubre de 2026 · 18:30–20:00 · AI Engineer L/X**  
**Para José:** sigue este documento en orden, en una pantalla que no compartas. Usa las diapositivas solo durante los diez primeros minutos; después comparte el editor o la terminal. Los bloques «Di» son frases sugeridas: puedes usarlas tal cual o decirlas con tus palabras.

**La idea que debe quedar al terminar:** un agente tiene un recorrido explícito; el modelo puede pedir herramientas, Python controla su ejecución y un checkpointer conserva la conversación.

## Vista rápida: dónde debes estar a cada hora

| Hora | Pantalla | Acción principal | Resultado que tienes que enseñar |
|---|---|---|---|
| 18:30–18:40 | Presentación 1–8 | Presentarte, QR y objetivo | Entienden qué vamos a construir |
| 18:40–18:50 | Editor + terminal | Grafo fijo | `hola thepower` → `HOLA THEPOWER` |
| 18:50–19:05 | Editor + terminal | Chatbot | Responde sin tools |
| 19:05–19:20 | Editor + terminal | Ticket, artículo y recurso inexistente | Python aporta datos y controla errores |
| 19:20–19:35 | Editor + terminal | Tres procesos, dos conversaciones | A recuerda Alex; B no lo conoce |
| 19:35–19:45 | Editor + terminal | Agente completo, seguimiento y límite | Recupera la referencia del turno anterior; bloquea una tercera tool |
| 19:45–19:50 | Enunciado | Explicar la entrega | Saben qué hacer y qué entregar |
| 19:50–20:00 | Conversación | Preguntas y cierre | Recap de grafo, tools y persistencia |

**Regla para el ritmo:** a las 19:20 entra en memoria aunque no hayas enseñado todo el código de tools. A las 19:45 pasa al ejercicio. La TUI avanzada es opcional y se omite si no sobra tiempo.

**Cómo seguir los comandos:** desde la etapa de chatbot abrimos la TUI con `--tui` y escribimos las preguntas dentro del chat. Enter envía; Esc o «salir» cierra. Primero enseña el código, luego prueba la pregunta y señala el recorrido en el panel. Cambia de pestaña para explicar el código sin cerrar el chat; ciérralo solo al cambiar de etapa o para demostrar el reinicio. Mantén la misma terminal y el mismo valor de `S5_DEMO`. Los JSON se guardan como respaldo, no son la interfaz de la clase.

---

## 0. Antes de empezar · 18:10–18:30

### Abre estas ventanas

- [Presentación S5](/Users/jose/Documents/the-power/1-langGraph/material/presentaciones/S5-langgraph.pptx) y [PDF de respaldo](/Users/jose/Documents/the-power/1-langGraph/material/presentaciones/S5-langgraph.pdf).
- Editor situado en `/Users/jose/Documents/the-power/1-langGraph`.
- Este guion, sin compartirlo.
- [Enunciado del alumno](/Users/jose/Documents/the-power/1-langGraph/material/alumno/S5-enunciado.md).
- [Evidencia guardada para respaldo](/Users/jose/Documents/the-power/1-langGraph/material/evidencias/ensayo-tecnico.json).

### Pestañas de Cursor: cuándo mostrar cada archivo y qué contiene

Deja abiertas estas siete pestañas antes de empezar. Todas las rutas parten de `/Users/jose/Documents/the-power/1-langGraph`.

| Cuándo lo muestras | Archivo | Qué contiene y qué debes señalar |
|---|---|---|
| 18:40 · Grafo fijo | `langgraph/01_grafo.py` | Ejemplo completo sin modelo: `State` con `texto`, nodo `mayusculas`, `StateGraph`, conexiones `START` y `END`, `compile` e `invoke`. Los paneles solo presentan la salida. |
| 18:50 · Chatbot; volver a las 19:05, 19:20 y 19:40 | `app/soporte/graph.py` | Núcleo del agente: estado, prompt, modelo con tools, nodos `inicio`, `chatbot` y `ejecutar_tools`, conexiones y compilación con checkpointer. Explica una parte en cada etapa. |
| 19:05 · Herramientas | `app/soporte/tools.py` | Esquemas `TicketInput` y `ArticuloInput`, carga de JSON, búsqueda mediante `lookup` y funciones `consultar_ticket` y `buscar_articulo`. También contiene los escenarios de fallo y retraso del miércoles. |
| 19:05 · Antes de consultar T-100 | `datos/soporte/tickets.json` | Datos ficticios: estado, asunto, artículo asociado y actualización. Señala T-100 y su referencia a A-10. |
| 19:13 aproximadamente · Antes de consultar A-10 | `datos/soporte/articulos.json` | Contenido de los artículos de ayuda. Señala A-10 y contrasta sus instrucciones con la respuesta. |
| 19:20 · Persistencia | `app/soporte/persistence.py` | `sqlite_memory`: prepara la ruta, abre `SqliteSaver` en un `with`, entrega el checkpointer y cierra la conexión al salir. |
| 19:40 · Pruebas | `tests/test_soporte.py` | Modelo simulado y pruebas del contrato. Muestra `test_parallel_third_is_blocked` y `test_counters_reset_and_threads_isolated`: tercera solicitud bloqueada, reinicio de contadores y separación de hilos. |

**A las 19:45:** muestra el [enunciado S5](/Users/jose/Documents/the-power/1-langGraph/material/alumno/S5-enunciado.md), que contiene los requisitos y la entrega. Este guion se queda en tu pantalla privada.

Los lanzadores siguientes se ejecutan desde la terminal. Puedes abrirlos brevemente para señalar las opciones, pero el código que explicas está en las siete pestañas anteriores:

| Etapa | Archivo que ejecutas | Código que explicas |
|---|---|---|
| Grafo fijo | `langgraph/01_grafo.py` | Estado, nodo y conexiones en ese mismo archivo |
| Chatbot | `langgraph/05_soporte_chatbot.py` | `State`, `prompt_template` y `chatbot` en `app/soporte/graph.py` |
| Herramientas | `langgraph/06_soporte_tools.py` | `app/soporte/tools.py`, `ejecutar_tools` y la conexión condicional en `app/soporte/graph.py` |
| SQLite | `langgraph/07_soporte_memoria.py` | `app/soporte/persistence.py` y `compile(checkpointer=checkpointer)` |
| Agente completo | `langgraph/08_soporte_completo.py` | El mismo grafo, con herramientas y persistencia habilitadas |

**Para orientarte:** los ejemplos 05–08 son lanzadores de un mismo núcleo con distintas opciones. No son cuatro agentes independientes. Puedes decir: «Activamos una capacidad cada vez para entender qué aporta». El código principal de esta práctica está en `app/soporte/graph.py`; `app/graph.py` corresponde al agente avanzado.

**Código comentado para enseñar:** los archivos Python de la práctica incluyen una cabecera en español con su propósito y sus partes, y comentarios junto a las funciones y bloques principales. La descripción de los campos de los JSON está en [LEEME de los datos](/Users/jose/Documents/the-power/1-langGraph/datos/soporte/LEEME.md); los JSON conservan su formato válido.

Entra en la reunión desde Calendario con la cuenta de AI Engineer. Comprueba micrófono, tamaño de letra y pantalla compartida. La grabación es automática: comprueba que sigue activa y no la detengas.

### 18:15 aproximadamente · Preparar la terminal una sola vez

```bash
cd /Users/jose/Documents/the-power/1-langGraph
source .venv/bin/activate
S5_DEMO="s5-$(date +%Y%m%d-%H%M%S)"
python scripts/preflight.py
```

**Entorno de la TUI:** utiliza el entorno actual con `opentui` instalado (lock avanzado). Si preparas un entorno nuevo, instala `requirements-advanced.lock` antes del directo. La TUI se abre en la terminal integrada de Cursor, no en la consola de depuración.

Amplía el panel de terminal para dejar aproximadamente 110 columnas y 35 filas: podrás mostrar chat y recorrido juntos. El historial del chat permite desplazarse; el detalle completo de cada turno queda además en los archivos de respaldo.

**Qué debe pasar:** aparece Python 3.12, el modelo efectivo y las dependencias. No deben faltar las de la práctica. Los valores secretos no aparecen; solo su estado de configuración. Este comando no llama al modelo.

**Por qué usamos `S5_DEMO`:** crea un nombre nuevo para este ensayo. Así no mezclas la memoria con pruebas anteriores. Mantén esta terminal abierta y no vuelvas a ejecutar la asignación de `S5_DEMO` a mitad de la demostración de memoria.

**18:20 aproximadamente · Comando de comprobación, antes de compartir pantalla:**

```bash
python langgraph/08_soporte_completo.py \
  --db "data/$S5_DEMO-comprobacion.sqlite" \
  --hilo "$S5_DEMO-comprobacion" \
  --pregunta 'Consulta el ticket T-100.' \
  --salida "resultados/$S5_DEMO/comprobacion.json"
```

**Qué debe pasar:** respuesta sobre T-100, `tool_count` igual a 1 y `status: "done"`. Esta consulta sí consume API. Si falla, usa la tabla de incidencias del final; no actualices dependencias ni cambies de modelo durante el directo.

### Cómo vas a mostrar los resultados

La TUI muestra mensajes de usuario y asistente, solicitudes y resultados de herramientas, ruta, intentos y errores. Señala esos elementos en pantalla. Los campos siguientes quedan también en el JSON de respaldo; solo ábrelo si necesitas comprobar un detalle:

| Campo | Cómo lo explicas |
|---|---|
| `answer` | Lo que recibiría el usuario |
| `route` | El recorrido de esta ejecución |
| `tool_count` | Cuántos intentos de herramienta se ejecutaron |
| `calls` | Qué herramientas se ejecutaron y si funcionaron |
| `errors` | Qué fallos se controlaron |
| `thread_id` | Qué conversación estamos usando |

La redacción de `answer` puede variar. Comprueba los hechos y el recorrido; no esperes una frase idéntica a este guion.

---

## 1. Introducción completa · 18:30–18:40 · presentación 1–8

Este es el único bloque en el que usas el PowerPoint. Recorre las ocho diapositivas una vez. No ejecutes demos ni abras archivos de código durante estos diez minutos.

**Terminal:** no hay ningún comando que ejecutar entre las 18:30 y las 18:40.

| Hora | Diapositiva | Qué dices y por qué |
|---|---|---|
| 18:30:00–18:30:30 | 1 · LangGraph | «Hoy construiremos un asistente de soporte que consulta datos y recuerda la conversación. LangGraph nos permitirá controlar su recorrido». Presenta el objetivo. |
| 18:30:30–18:31:15 | 2 · Antes de empezar | «Este QR evalúa la clase anterior». Deja unos segundos para escanear. |
| 18:31:15–18:32:30 | 3 · Qué es LangGraph | «Es un framework para diseñar agentes como grafos con estado. Podemos combinar funciones normales y llamadas al modelo». Situar la herramienta antes de mostrar código. |
| 18:32:30–18:34:30 | 4 · LangChain y LangGraph | «LangChain nos da componentes, integraciones y agentes de mayor nivel. LangGraph nos permite diseñar explícitamente los nodos, las rutas, los ciclos y la persistencia. Se complementan: aquí usaremos mensajes y herramientas de LangChain dentro del grafo». No afirmar que LangChain solo permite cadenas lineales. |
| 18:34:30–18:36:00 | 5 · Cómo funciona un grafo | Explica estado, nodos y aristas. «El estado contiene los mensajes y los datos del turno. Los nodos hacen el trabajo y las aristas conectan los pasos. Si hacen falta datos, vamos a una herramienta y volvemos al modelo; si ya podemos responder, terminamos». Un nodo no tiene por qué ser un LLM. |
| 18:36:00–18:37:30 | 6 · Qué vamos a construir | Señala Ticket, Ayuda y Memoria. «El ticket T-100 nos dice qué ocurre y qué artículo tiene asociado. A-10 nos da la ayuda. Conservaremos el contexto para continuar después de reiniciar». Presenta el caso; el código y sus restricciones se explican en la práctica. |
| 18:37:30–18:39:00 | 7 · Cómo lo haremos | Señala las cinco etapas de izquierda a derecha. «Primero una función sin modelo; luego una respuesta del modelo; después acceso a los datos; a continuación guardamos la conversación; por último combinamos todo y comprobamos sus límites». |
| 18:39:00–18:40:00 | 8 · Qué debe funcionar al terminar | Señala Datos, Memoria y Control. «Tiene que responder con datos consultados, recordar en el mismo hilo sin mezclar conversaciones y gestionar errores y límites». Son los tres resultados que comprobaréis juntos. |

**Ejemplo oral para la diapositiva 4:** «Para llamar al modelo y representar mensajes y herramientas usaremos LangChain. Para decidir si seguimos hacia una herramienta, volvemos al modelo o terminamos, diseñaremos el recorrido con LangGraph». Añade que los agentes de alto nivel de LangChain también se apoyan en LangGraph: la diferencia aquí es cuánto recorrido defines tú directamente. Referencia para preparar esta explicación: [documentación oficial de LangChain](https://docs.langchain.com/oss/python/langchain/overview#built-on-top-of-langgraph).

**A las 18:40, di:** «Vamos a empezar por un grafo que funciona sin modelo». Sal del modo presentación y comparte el editor. Este cambio de pantalla es una indicación privada para ti. Durante la práctica sigues el guion, sin volver a las diapositivas.

---

## 2. El grafo más pequeño · 18:40–18:50

**Abre:** [01_grafo.py](/Users/jose/Documents/the-power/1-langGraph/langgraph/01_grafo.py).

**Qué contiene y cómo recorrerlo:** la parte superior define el estado, el nodo y las conexiones. La parte inferior, dentro de `if __name__ == "__main__"`, prepara la entrada, llama a `invoke` y presenta el resultado. Este archivo reúne todo el ejemplo sin modelo.

**Enseña en este orden:** `State`, función `mayusculas`, `add_node`, dos `add_edge`, `compile` e `invoke`. Ignora por ahora el código que dibuja los paneles.

**Di:**

> «El estado es el diccionario que viaja por el grafo. Un nodo es una función que lo recibe y devuelve lo que quiere actualizar. Las conexiones marcan por dónde seguimos. Aquí solo hay una ruta: empezar, convertir el texto y terminar.»

**18:45 aproximadamente · Ejecuta el grafo fijo, después de mostrar `State`, el nodo y las conexiones:**

```bash
python langgraph/01_grafo.py
```

**Debe aparecer:** entrada `hola thepower`, salida `HOLA THEPOWER` y un recorrido con un nodo. No se utiliza ninguna API ni clave.

**Por qué lo hacemos:** demuestra que LangGraph organiza una ejecución; no exige que todos los nodos contengan un modelo.

**Pregunta breve:** «Si quisiera guardar además cuántos caracteres tiene el texto, ¿dónde pondría ese dato?» En el estado y en la actualización devuelta por un nodo.

**Si falla:** comprueba que estás en la carpeta correcta y que el entorno está activado. Si no se resuelve en un minuto, enseña el código y la salida prevista; no conviertas la clase en una instalación.

**Transición:** «Ahora vamos a poner una llamada al modelo dentro de ese recorrido.»

---

## 3. Añadir el chatbot · 18:50–19:05

**Abre primero:** [05_soporte_chatbot.py](/Users/jose/Documents/the-power/1-langGraph/langgraph/05_soporte_chatbot.py). Es un lanzador corto: no pases varios minutos explicando sus imports.

**Después abre:** [graph.py del soporte](/Users/jose/Documents/the-power/1-langGraph/app/soporte/graph.py). Busca `prompt_template`, `MessagesPlaceholder` y la función `chatbot` dentro de `build_graph`.

**Qué muestras ahora:** primero `State`, donde `messages` guarda el historial y `add_messages` incorpora mensajes nuevos. Después `prompt_template`, que combina instrucciones de sistema e historial, y `chatbot`, que llama al modelo y devuelve su mensaje. Las herramientas, el contador y las conexiones están en este mismo archivo, pero los explicarás en sus bloques. El lanzador 05 habilita esta etapa sin tools ni SQLite.

**Di:**

> «El mensaje de sistema define el trabajo del asistente. El usuario hace una pregunta y el modelo devuelve un mensaje. El nodo integra ese mensaje en el estado. En esta etapa todavía no le ofrecemos herramientas ni guardamos la conversación entre ejecuciones.»

**18:57 aproximadamente · Ejecuta el chatbot, después de explicar los mensajes y la llamada al modelo:**

```bash
python langgraph/05_soporte_chatbot.py \
  --tui --hilo "$S5_DEMO-chatbot" \
  --salida "resultados/$S5_DEMO/chatbot.json"
```

**Debe pasar:** aparece la respuesta en el chat, en español; el panel muestra cero intentos de herramientas. En `route` puede aparecer `respuesta_final`: en nuestro código significa una llamada sin herramientas. No es un nodo adicional ni un fallo.

**Escribe en la TUI:** `Hola, ¿qué puedes hacer?` y pulsa Enter. Antes de cambiar a herramientas, sal con Esc. El historial de esta etapa está en RAM: continúa mientras está abierta, pero se pierde al salir.

**Aclaración útil:** el prompt menciona soporte, pero en esta etapa no hemos habilitado sus funciones. Que un modelo diga que puede consultar algo no demuestra que lo haya hecho. La evidencia sería una ejecución de herramienta.

**Por qué:** separas generación de texto de acceso a datos reales.

**Muestra la configuración solo si hace falta:** [config.py](/Users/jose/Documents/the-power/1-langGraph/app/soporte/config.py). Explica que el modelo se elige mediante `MODEL_ID`, con compatibilidad con `OPENROUTER_MODEL`. Nunca abras `.env` al compartir pantalla.

**Pregunta:** «Si ahora le pregunto por un ticket, ¿qué nos falta para confiar en la respuesta?» Una herramienta que lea el dato.

**Transición:** «Vamos a darle exactamente dos operaciones de lectura.»

---

## 4. Consultar datos mediante herramientas · 19:05–19:20

### 4.1 Ticket existente · unos 6 minutos

**Abre:** [tools.py](/Users/jose/Documents/the-power/1-langGraph/app/soporte/tools.py) y [tickets.json](/Users/jose/Documents/the-power/1-langGraph/datos/soporte/tickets.json).

Señala el argumento validado, el nombre de la función y los datos ficticios de T-100. No necesitas explicar todos los tipos de Python.

**Orden de pantalla:** primero `tickets.json`, para enseñar el dato que queremos obtener; después `tools.py`. Señala `TicketInput`, que exige el formato `T-100`; `@tool`, que ofrece descripción y esquema al modelo; y `consultar_ticket`, que llama a `lookup`. Esta función busca el dato y devuelve un JSON con `ok`, `id`, `datos` y `error`. Deja los escenarios de fallo y retraso para el miércoles.

**Di:**

> «El modelo no ejecuta esta función por sí solo: devuelve una solicitud. Nuestro nodo valida el argumento, ejecuta Python y devuelve un ToolMessage asociado a esa solicitud. Después el modelo redacta la respuesta con el resultado.»

**19:08 aproximadamente · Ejecuta la consulta del ticket, después de enseñar T-100 y su herramienta:**

```bash
python langgraph/06_soporte_tools.py \
  --tui --hilo "$S5_DEMO-tools" \
  --salida "resultados/$S5_DEMO/tools.json"
```

**Escribe en el chat:** `Consulta el ticket T-100.` y pulsa Enter. Mantén esta TUI abierta para las dos consultas siguientes.

**Debe pasar:** T-100 está **en curso**, hay un error de acceso y no existe una fecha de resolución confirmada. `calls` muestra `consultar_ticket`, `executed: true`, `ok: true`; `tool_count` vale 1. La ruta habitual es `inicio → chatbot → tools → chatbot`.

**Por qué:** puedes contrastar la respuesta con una fuente concreta, el JSON que acabas de enseñar.

**Vuelve un momento a `app/soporte/graph.py`:** señala `add_conditional_edges` y `add_edge("tools", "chatbot")`. Relaciona el código con lo que acabas de ver en `route`: el mensaje del modelo decide si necesita datos; Python ejecuta la herramienta; su resultado vuelve al modelo. Dedica unos dos minutos, sin explicar todavía el contador.

**Señala también, dentro de esos dos minutos:** `model.bind_tools` ofrece las herramientas al modelo; `ejecutar_tools` ejecuta la solicitud; `ToolMessage` asocia el resultado con su `tool_call_id`. Termina mostrando las conexiones al final del archivo. No leas toda la función de arriba abajo.

### 4.2 Artículo · unos 3 minutos

Abre [articulos.json](/Users/jose/Documents/the-power/1-langGraph/datos/soporte/articulos.json).

**Qué contiene y qué señalar:** localiza A-10 y sus instrucciones. Vuelve unos segundos a `tools.py` para mostrar `ArticuloInput` y `buscar_articulo`: el mecanismo es el mismo que para el ticket, con otro esquema y otros datos. Después ejecuta y compara el resumen con el JSON.

**19:13 aproximadamente · Ejecuta la consulta del artículo:**

**En la misma TUI, escribe:** `Consulta el artículo A-10.` y pulsa Enter. No ejecutes otro comando ni cierres el programa.

**Debe pasar:** usa `buscar_articulo`; explica recuperar contraseña, revisar spam y no compartir la contraseña. No se envía ningún correo ni se modifica ninguna cuenta.

**Di:** «La descripción de la herramienta ayuda al modelo a elegirla. Su esquema ayuda a nuestro código a validar la petición.»

### 4.3 Ticket inexistente · unos 4 minutos

**Pantalla:** deja `tickets.json` visible para comprobar que T-999 no existe. Después de ejecutar, muestra `lookup` en `tools.py`: `data.get(key)` no encuentra el recurso y devuelve `ok: false` y `error: "no_encontrado"`. Así explicas de dónde sale el error controlado.

**19:16 aproximadamente · Ejecuta la consulta del ticket inexistente:**

**En la misma TUI, escribe:** `Consulta el ticket T-999.` y pulsa Enter. Mira el resultado de la herramienta y el error del panel. Al terminar este bloque, sal con Esc para abrir la etapa de SQLite.

**Debe pasar:** indica que el ticket no existe y pide comprobar el identificador. La herramienta cuenta como un intento: `tool_count: 1`, `ok: false`, `errors` contiene `no_encontrado`.

**Di:**

> «Este es un error del caso de negocio que sabemos gestionar. El programa puede terminar con `status: done` aunque haya un error de herramienta: ha conseguido responder de forma controlada. Lo incorrecto sería inventar el estado de T-999.»

**Si el modelo no pide la tool o afirma algo distinto:** señala la discrepancia, compara `calls` y el JSON y explica que una respuesta fluida no garantiza el comportamiento correcto. No repitas hasta conseguir una salida bonita. Puedes mostrar la evidencia guardada.

**Transición:** «Ahora las consultas funcionan, pero queremos que recuerde lo hablado después de cerrar el proceso.»

---

## 5. Memoria persistente y dos hilos · 19:20–19:35

**Abre:** [persistence.py](/Users/jose/Documents/the-power/1-langGraph/app/soporte/persistence.py). Enseña el fichero SQLite y el bloque `with`. Luego señala `checkpointer` al compilar el grafo.

**Qué contiene y en qué orden lo muestras:** en `sqlite_memory`, señala la ruta con `Path`, la creación de la carpeta, `SqliteSaver.from_conn_string`, `yield saver` y el cierre administrado por `with`. Vuelve al final de `graph.py` para enseñar `builder.compile(checkpointer=checkpointer)`. Después comparte la terminal y señala `--db` y `--hilo` en los tres comandos: el archivo determina dónde se guarda el estado; el hilo, qué conversación se carga.

**Di:**

> «El historial está en el estado, pero necesitamos un mecanismo que lo guarde y lo vuelva a cargar. SQLite permite conservarlo en disco. El `thread_id` indica qué conversación queremos continuar.»

### Paso A · 19:23 aproximadamente: guardar un dato

**Ejecuta este primer proceso, después de enseñar el checkpointer:**

```bash
python langgraph/07_soporte_memoria.py \
  --db "data/$S5_DEMO.sqlite" \
  --hilo conversacion-a \
  --tui \
  --salida "resultados/$S5_DEMO/memoria-escribir.json"
```

**En la TUI escribe:** `Me llamo Alex.` y pulsa Enter. Debe reconocer el nombre. Espera a que termine la respuesta y sal con Esc: vuelve el prompt de la terminal y el proceso ha terminado.

**Di:** «No hemos dejado el programa esperando: ya se ha cerrado. Ahora iniciamos otro proceso.»

### Paso B · 19:27 aproximadamente: recuperar desde otro proceso

**Ejecuta este segundo proceso cuando el anterior haya terminado. Conserva DB e hilo:**

```bash
python langgraph/07_soporte_memoria.py \
  --db "data/$S5_DEMO.sqlite" \
  --hilo conversacion-a \
  --tui \
  --salida "resultados/$S5_DEMO/memoria-leer.json"
```

**En la nueva TUI escribe:** `¿Cómo me llamo?` y pulsa Enter. Debe responder **Alex**: mismo fichero y mismo hilo, proceso diferente. La pantalla empieza sin los globos anteriores, pero el agente recupera el historial de SQLite. Después de responder, sal con Esc.

### Paso C · 19:31 aproximadamente: demostrar aislamiento

**Ejecuta este tercer proceso. Conserva la DB y cambia únicamente el hilo de conversación:**

```bash
python langgraph/07_soporte_memoria.py \
  --db "data/$S5_DEMO.sqlite" \
  --hilo conversacion-b \
  --tui \
  --salida "resultados/$S5_DEMO/memoria-aislada.json"
```

**En esta TUI escribe:** `¿Cómo me llamo?` y pulsa Enter. No debe saber el nombre: esta conversación es nueva. Después sal con Esc.

**Di:**

> «Persistir no significa compartir todo con todo el mundo. El hilo A conserva su estado; el B empieza vacío. Y esto no es autenticación: en una aplicación pública habría que comprobar quién puede acceder a cada hilo.»

**Por qué:** demuestras dos propiedades diferentes: continuidad e independencia.

**Si A no recuerda:** comprueba primero `--db` y `--hilo`; no vuelvas a asignar `S5_DEMO`. Si B dice Alex, comprueba que no has usado ese hilo en un ensayo anterior. Utiliza una DB nueva para repetir los tres pasos, sin borrar ninguna existente.

**Pregunta:** «¿Qué pasaría usando solo `InMemorySaver`?» Se perdería el estado al cerrar el proceso.

---

## 6. Completar el agente y demostrar el límite · 19:35–19:45

**Reparto de este bloque:** 19:35–19:38 consulta completa; 19:38–19:40 seguimiento; 19:40–19:45 contador y pruebas. Si la API tarda, usa el respaldo y conserva la prueba del límite.

### Unir las dos herramientas · 19:35–19:38

**Pantalla:** TUI para escribir, ver las herramientas y la respuesta y señalar el recorrido y el presupuesto. Si abres `08_soporte_completo.py`, basta señalar que activa herramientas y memoria en el mismo núcleo. Ten disponibles los dos JSON para comprobar la relación T-100 → A-10.

**19:35 · Ejecuta el agente completo:**

```bash
python langgraph/08_soporte_completo.py \
  --db "data/$S5_DEMO.sqlite" \
  --hilo soporte-completo \
  --tui \
  --salida "resultados/$S5_DEMO/completo.json"
```

**Escribe en el chat:** `Consulta T-100 y explícame su artículo de ayuda asociado.` y pulsa Enter. Mantén la TUI abierta para el seguimiento.

**Debe pasar:** consulta T-100, descubre A-10 y consulta ese artículo. La respuesta incluye el estado y la ayuda; `tool_count` es 2. Puede verse `respuesta_final` al agotarse el presupuesto de tools.

**Di:** «Hemos reunido las capacidades de las etapas anteriores: herramientas para obtener los datos y SQLite para conservar la conversación.»

### Hacer una pregunta que dependa del turno anterior · 19:38–19:40

**19:38 · Seguimiento en la misma TUI:** espera a que termine la respuesta anterior y escribe:

> Vuelve a consultar el artículo que acabamos de leer y resúmelo en dos pasos.

Pulsa Enter. No hace falta ejecutar otro comando: la DB y el hilo siguen siendo los mismos.

**Debe pasar:** identifica A-10 a partir del historial, vuelve a usar `buscar_articulo` y resume su ayuda. No hemos incluido el identificador en la pregunta nueva. Lo habitual es una herramienta en este turno; verifica `calls`, la fuente A-10 y un `tool_count` de como máximo 2, sin exigir una redacción idéntica.

**Di:** «La memoria sirve para entender a qué artículo me refiero. La herramienta comprueba su contenido en este turno. El presupuesto se reinicia: haber usado dos herramientas antes no bloquea la conversación entera.»

**Por qué:** compruebas una pregunta dependiente del turno anterior en el chat de soporte completo, además del ejemplo sencillo del nombre. Si pide el identificador o consulta otro artículo, muestra la discrepancia y revisa DB, hilo e historial; no lo presentes como una demostración correcta.

### Comprobar el contador y la tercera llamada · 19:40–19:45

**Sal de la TUI con Esc** cuando haya terminado el seguimiento. La terminal queda disponible para ejecutar los tests.

**Cambio de archivo:** primero `graph.py`, para mostrar la regla; después `tests/test_soporte.py`, para mostrar cómo se comprueba. En `graph.py`, `inicio` reinicia los contadores, `ejecutar_tools` bloquea nuevas ejecuciones al llegar a dos y `chatbot` usa una llamada sin herramientas para la respuesta final. En los tests, señala la solicitud simulada de tres tools y las comprobaciones de `tool_count` y `executed`; después, la segunda prueba, que inicia otro turno y otro hilo.

**Di:** «El modelo puede decidir qué dato necesita, pero el límite lo impone el código. No dependemos de que obedezca una frase del prompt.»

**Abre:** `ejecutar_tools` y el contador en [graph.py](/Users/jose/Documents/the-power/1-langGraph/app/soporte/graph.py).

Señala que cada intento ejecutado consume presupuesto, incluso si falla, y que `inicio` pone el contador a cero para el siguiente turno.

**19:42 aproximadamente · Ejecuta estas dos pruebas sin red, después de enseñar el contador:**

```bash
PYTHONPATH=tests python -m unittest \
  test_soporte.SoporteTests.test_parallel_third_is_blocked \
  test_soporte.SoporteTests.test_counters_reset_and_threads_isolated \
  -v
```

**Debe aparecer:** dos pruebas correctas y `OK`. Abre esos tests en [test_soporte.py](/Users/jose/Documents/the-power/1-langGraph/tests/test_soporte.py).

**Di:**

> «Aquí simulamos deliberadamente que el modelo pide tres herramientas. Ejecutamos dos y rechazamos la tercera. Cada solicitud recibe su respuesta, para no dejar el protocolo a medias. Con una simulación podemos probar siempre este límite, sin esperar a que el modelo lo incumpla por casualidad.»

**Por qué:** separas una demo de comportamiento habitual de una prueba reproducible de una restricción.

**Si vas justo:** enseña solo el resultado del test y las dos condiciones del contador. No abras la suite completa ni expliques toda la interfaz de terminal.

---

## 7. Ejercicio y entrega · 19:45–19:50

Abre [el enunciado S5](/Users/jose/Documents/the-power/1-langGraph/material/alumno/S5-enunciado.md). No necesitas ejecutar ningún comando para explicar la entrega.

**Di:**

> «Vuestra práctica es construir un asistente de soporte por etapas. Necesito poder ejecutar vuestro proyecto, continuar una conversación después de reiniciar y comprobar que las herramientas y sus límites funcionan.»

Recorre esta lista, sin leer el enunciado entero:

- Grafo fijo → chatbot → herramientas y memoria.
- `consultar_ticket` y `buscar_articulo` sobre datos ficticios.
- SQLite, continuidad tras reinicio y dos conversaciones separadas.
- Dos llamadas como máximo por turno, con pruebas de errores.
- Código, datos, README y esquema del grafo.

**Aclara:** «No hace falta frontend, RAG ni despliegue. La dedicación de 3–5 horas es para la práctica con el entorno preparado, no para terminarla durante este directo.»

**19:47 · Ampliación opcional:** solo si ya has cubierto todo y sobra tiempo, ejecuta:

```bash
python langgraph/04_chatbot.py
```

Explica en una frase el juez y validador. Sal con `Esc` y vuelve al enunciado. Si no sobra tiempo, omite este comando y conserva las preguntas de las 19:50.

---

## 8. Preguntas y cierre · 19:50–20:00

**Terminal:** no hay comandos previstos. Vuelve al archivo correspondiente únicamente si ayuda a responder una pregunta.

Si no hay preguntas, usa estas cuatro:

| Pregunta | Respuesta que quieres reforzar |
|---|---|
| ¿Qué diferencia hay entre estado y checkpointer? | Uno contiene los datos; el otro guarda y recupera el estado |
| ¿Quién ejecuta una herramienta? | Python, después de validar la solicitud del modelo |
| ¿Un `thread_id` autentica al usuario? | No; identifica una conversación |
| ¿Por qué probamos los límites con respuestas simuladas? | Para forzar el caso y comprobarlo siempre |

**Cierra diciendo:**

> «Hoy hemos construido y controlado la ejecución. El miércoles usaremos el mismo agente para ver qué ha ocurrido por dentro, medirlo y comparar cambios de prompt.»

Recuerda dónde está el ejercicio en la plataforma. No prometas plazos de entrega que Laura no haya confirmado.

---

## Si algo falla o te quedas sin tiempo

**Máximo un minuto de diagnóstico público por incidencia.** Explica el límite, muestra el respaldo y continúa con el concepto.

| Caso | Qué haces | Qué dices |
|---|---|---|
| Comando no encuentra archivo | Comprueba `pwd`; vuelve al `cd` inicial | «La terminal estaba en otra carpeta» |
| Dependencia o clave ausente | Revisa preflight sin mostrar `.env`; pasa a respaldo | «El entorno no está listo; el recorrido lo tenemos guardado» |
| Proveedor lento o error de modelo | No encadenes reintentos; enseña un resultado previo | «Esto depende de una API; esta salida es del ensayo, no de una ejecución nueva» |
| Respuesta inesperada | Mira tools, argumentos y datos; no la des por correcta | «Vamos a distinguir lo que dijo el modelo de lo que realmente consultó» |
| Fallo de memoria | Comprueba fichero e hilo; usa el test de persistencia si hace falta | «Antes de culpar al modelo, comprobamos qué conversación hemos cargado» |
| PDF/PPTX falla | Usa el otro formato; el código y guion son suficientes | «Seguimos con la demostración» |
| Vas 5 minutos tarde | Omite la segunda consulta de artículo y la TUI | Conserva memoria, límite y ejercicio |
| Vas 10 minutos tarde | Explica el caso inexistente con el resultado guardado | Conserva las tres ejecuciones de memoria y el test del límite |

**Respaldo sin API:** abre [ensayo-tecnico.json](/Users/jose/Documents/the-power/1-langGraph/material/evidencias/ensayo-tecnico.json) y busca `"etapa": "completo"`, `"memoria-leer"` o `"memoria-aislar"`. Son ejecuciones verificadas del 02/10/2026. El grafo fijo y los tests siguen funcionando sin modelo remoto.

**Al terminar:** anota dudas o comandos que quieras ajustar, sin guardar datos de alumnos ni contraseñas. La presentación se usa una sola vez al principio. El resto se sigue desde este guion, el código y los resultados.
