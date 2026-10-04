# Tu guion de directo · Clase 2: observabilidad

**Miércoles 7 de octubre de 2026 · 18:30–20:00 · AI Engineer L/X**  
**Para José:** sigue este documento en orden. Ten el guion en una pantalla no compartida y, después de la introducción, sigue con terminal, código y las dos plataformas.

**La idea que debe quedar al terminar:** que el agente responda no basta; necesitamos reconstruir su ejecución, relacionarla con una versión de prompt y medir resultados sin confundir texto generado con calidad.

## Vista rápida: dónde debes estar a cada hora

| Hora | Pantalla | Acción principal | Resultado que tienes que enseñar |
|---|---|---|---|
| 18:30–18:40 | Presentación 1–8 | QR, conceptos y plan de práctica | Entienden qué vamos a observar y comparar |
| 18:40–18:55 | Terminal + LangSmith | Baseline y LangSmith | Raíz, nodos, modelo y herramienta |
| 18:55–19:10 | Langfuse + terminal | Langfuse | El mismo recorrido, sesión y observaciones |
| 19:10–19:25 | Código + resultados | Prompts y comparación preparada | Versión aplicada y 20 resultados comparables |
| 19:25–19:35 | Resultados + plataformas | Métricas y valoración | Diferencia entre consumo, coste y calidad |
| 19:35–19:45 | Terminal + plataformas | Fallo, retraso y privacidad | Problema localizable y datos ocultos |
| 19:45–19:50 | Enunciado | Ejercicio | Saben qué instrumentar y entregar |
| 19:50–20:00 | Conversación | Preguntas y cierre | Pueden justificar una mejora con evidencia |

**Regla para el ritmo:** la comparación de veinte consultas ya está preparada. No la lances entera durante el directo. A las 19:35 pasa a incidentes y privacidad; a las 19:45, al ejercicio.

---

## 0. Antes de empezar · 18:10–18:30

### Deja abiertas estas ventanas

- [Presentación S6](/Users/jose/Documents/the-power/1-langGraph/material/presentaciones/S6-observabilidad.pptx) y [PDF de respaldo](/Users/jose/Documents/the-power/1-langGraph/material/presentaciones/S6-observabilidad.pdf).
- [Proyecto de LangSmith](https://eu.smith.langchain.com/o/e6f8ad5b-010d-4617-b512-043325e50a5d/projects/p/4db7912a-e386-4633-930e-021bf74c4f8d).
- [Trazas del proyecto de Langfuse](https://cloud.langfuse.com/project/cmsxqyfid00q8ad0cfhii7xxt/traces).
- [Comparación preparada](/Users/jose/Documents/the-power/1-langGraph/material/evidencias/comparacion.md), [revisión de respuestas](/Users/jose/Documents/the-power/1-langGraph/material/evidencias/revision-manual.md) y [resultados completos](/Users/jose/Documents/the-power/1-langGraph/material/evidencias/resultados.json).
- [Captura LangSmith](/Users/jose/Documents/the-power/1-langGraph/material/evidencias/langsmith-privacidad.png) y [captura Langfuse](/Users/jose/Documents/the-power/1-langGraph/material/evidencias/langfuse-privacidad.png), por si no cargan las plataformas.
- [Enunciado S6](/Users/jose/Documents/the-power/1-langGraph/material/alumno/S6-enunciado.md).

Inicia sesión antes de compartir pantalla. Comprueba cuenta del programa, reunión, micrófono y grabación automática. No abras pestañas de claves de API durante la clase.

### Prepara la terminal: copia una vez

```bash
cd /Users/jose/Documents/the-power/1-langGraph
source .venv/bin/activate
S6_DEMO="s6-$(date +%Y%m%d-%H%M%S)"
python scripts/preflight.py
```

**Debe pasar:** dependencias presentes y variables de las dos plataformas configuradas. Que una variable exista no demuestra que la clave siga siendo válida.

Haz una comprobación real previa con un hilo propio:

```bash
python langgraph/05_agente_completo.py \
  --observabilidad both --prompts remote --version v2 \
  --hilo "$S6_DEMO-comprobacion" \
  --pregunta 'Consulta el ticket T-100.' \
  --salida "resultados/$S6_DEMO/comprobacion.json"
```

Luego verifica recepción:

```bash
python scripts/verificar_trazas.py \
  "resultados/$S6_DEMO/comprobacion.json" \
  --salida "resultados/$S6_DEMO/comprobacion-trazas.json"
```

**Debe pasar:** los checks de ambas plataformas salen `True`. La primera orden consume API; la segunda lee trazas ya existentes y no genera otra respuesta. Puede tardar más que la generación: hazlo antes del directo.

**No ejecutes ahora `registrar_prompts.py --nuevo`:** los prompts del profesor ya están registrados. No necesitas crear versiones nuevas ni cambiar etiquetas para esta clase.

### Campos que vas a señalar

| Campo | Qué significa |
|---|---|
| `query_id` | Identificador de esta consulta |
| `thread_id` | Conversación que agrupa turnos |
| `langsmith_run_id` / `langfuse_trace_id` | Cómo localizar cada traza |
| `prompt_source`, `prompt_version` | De dónde viene el prompt y qué versión se aplicó |
| `model_calls`, `tool_count` | Llamadas al modelo e intentos de herramienta; son contadores distintos |
| `duration_s`, `total_tokens`, `cost_usd` | Tiempo, consumo y coste recogidos en nuestra ejecución |
| `answer_present` | Existe texto de respuesta; no demuestra corrección |
| `quality` | Valoración posterior según la rúbrica; `null` significa no valorado |

---

## 1. Introducción completa · 18:30–18:40 · presentación 1–8

Este es el único bloque en el que usas el PowerPoint. Recorre las ocho diapositivas una vez; las demos empiezan después.

| Hora | Diapositiva | Qué dices y por qué |
|---|---|---|
| 18:30:00–18:30:30 | 1 · Portada | «Hoy observaremos el mismo agente del lunes para entender qué ha pasado y comparar cambios». Logo thePower visible. |
| 18:30:30–18:31:15 | 2 · QR | Recordar que evalúa la clase anterior y dar tiempo para escanear. |
| 18:31:15–18:32:30 | 3 · Qué es observabilidad | «La respuesta final no cuenta todo el recorrido. Necesitamos saber qué pasos hizo el agente, cuánto consumió y dónde falló». |
| 18:32:30–18:34:00 | 4 · Dos plataformas | «LangSmith y Langfuse comparten capacidades de trazas, prompts y evaluación. Vamos a ver ambas sobre el mismo agente». No presentar sus funciones compartidas como exclusivas. |
| 18:34:00–18:35:30 | 5 · Qué veremos | Explicar consulta, conversación, pasos y métricas. «Que exista texto no demuestra que sea correcto; un dato ausente tampoco equivale a cero». |
| 18:35:30–18:37:00 | 6 · Qué haremos | Instrumentar, aplicar dos versiones de prompt, comparar casos y localizar un fallo/retraso. Comprobar datos filtrados. |
| 18:37:00–18:39:00 | 7 · Cómo lo haremos | Baseline → trazas → prompts → comparación → privacidad. «El lote de veinte resultados está preparado; mostraremos casos para disponer de tiempo para explicar». |
| 18:39:00–18:40:00 | 8 · Qué debe demostrarse | Relacionar resultado y prompt, interpretar métricas/fallos y verificar filtrado remoto. |

**A las 18:40, di:** «Ya sabemos qué queremos observar. Cerramos la presentación y ejecutamos primero el agente sin exportar trazas». Sal del modo presentación. El resto se sigue desde terminal, código, resultados y las plataformas.

---

## 2. Baseline y LangSmith · 18:40–18:55

### Baseline · primeros 3 minutos

**Ejecuta:**

```bash
python observability/01_sin_obs.py \
  --hilo "$S6_DEMO-baseline" \
  --pregunta 'Consulta el ticket T-100.' \
  --salida "resultados/$S6_DEMO/baseline.json"
```

**Debe pasar:** respuesta válida sobre T-100 y una herramienta. Los identificadores de LangSmith y Langfuse son `null`: esta demo no exporta trazas, aunque tengas claves en `.env`.

**Di:**

> «Nuestra consola ya muestra un resumen porque lo programamos así. Lo que todavía no tenemos aquí es un árbol remoto, navegable y guardado, con todos los pasos y sus tiempos.»

**Por qué:** estableces una referencia. Si el agente falla sin instrumentación, el primer sitio que revisar es el agente, no la plataforma de trazas.

**Transición:** «Ahora registramos la misma pregunta en LangSmith».

### Ejecutar y localizar · unos 3 minutos

```bash
python observability/02_langsmith.py \
  --hilo "$S6_DEMO-langsmith" \
  --pregunta 'Consulta el ticket T-100.' \
  --salida "resultados/$S6_DEMO/langsmith.json"
```

**Debe pasar:** respuesta válida y `langsmith_run_id` no nulo; `langfuse_trace_id` es `null`.

**Haz:** abre el proyecto de LangSmith, actualiza el listado y entra en la ejecución reciente llamada `thepower-soporte`. Usa el ID de la consola para confirmar que es esa, y no una del ensayo.

Si el listado no ayuda, el JSON de la comprobación previa contiene el enlace en `langsmith_url`. Puedes mostrar esa ejecución anterior identificándola como comprobación previa.

### Leer el árbol · unos 6 minutos

Señala en orden:

1. **Raíz `thepower-soporte`:** representa una consulta completa.
2. **`inicio`:** prepara los contadores del turno.
3. **Primer `chatbot` y su llamada `ChatOpenRouter`:** el modelo solicita consultar el ticket.
4. **`tools` → `consultar_ticket`:** argumento T-100 y resultado real de la función.
5. **Segundo `chatbot`:** redacta la respuesta utilizando el resultado.

Puede haber nodos auxiliares como `RunnableSequence` o `ChatPromptTemplate`. Son parte de la instrumentación; no hace falta explicar todos. Algunas interfaces los ocultan para simplificar el árbol.

**Di:**

> «Una consulta del usuario ha necesitado más de una llamada al modelo. Aquí puedo distinguir el tiempo del modelo, el de la herramienta y la respuesta final. Si hubiera un fallo, sabría en qué paso empezar a buscar.»

**Abre como máximo un fragmento de código:** [telemetry.py](/Users/jose/Documents/the-power/1-langGraph/app/soporte/telemetry.py), cliente y callback de LangSmith. No recorras el fichero entero.

### Idea para cerrar el bloque · unos 3 minutos

Muestra `thread_id`, nombre del modelo y metadatos. Explica que una conversación puede contener varias consultas y, por tanto, varias trazas.

**Por qué:** evita confundir una llamada al modelo, una consulta y una conversación.

**Si no aparece la traza:** espera unos segundos y actualiza una vez. Si sigue sin aparecer, muestra la captura de respaldo y el ID de una ejecución verificada. No anuncies que llegó solo porque la terminal terminó.

**Transición:** «Ahora vamos a observar la misma lógica en Langfuse.»

---

## 3. Langfuse: observaciones y sesiones · 18:55–19:10

**Ejecuta:**

```bash
python observability/03_langfuse.py \
  --hilo "$S6_DEMO-langfuse" \
  --pregunta 'Consulta el ticket T-100.' \
  --salida "resultados/$S6_DEMO/langfuse.json"
```

**Debe pasar:** `langfuse_trace_id` tiene valor y `langsmith_run_id` es `null`.

**Haz:** en Langfuse, abre la traza reciente por su ID. Señala raíz, generaciones del modelo, herramienta, entrada y salida. Después localiza la sesión correspondiente al hilo.

**Di:**

> «No hemos cambiado las reglas del agente. Hemos cambiado dónde registramos lo que ocurre. Una generación es una llamada al modelo; la traza completa contiene también otras operaciones.»

Señala `answer_present`:

> «Aquí vale uno porque hay respuesta. No significa que sea correcta. Si el modelo inventara un dato pero escribiera texto, esta métrica seguiría valiendo uno.»

Muestra los tokens y el coste, pero reserva su interpretación para el bloque siguiente. Avisa de que el coste inferido por el panel puede diferir del comunicado por el proveedor.

**Por qué:** enseñas a leer la plataforma y también a no sacar conclusiones que la métrica no permite.

**Explica el cierre:** «Los SDK pueden enviar datos en lotes. Por eso esperamos al envío con `flush` y cerramos correctamente el cliente. Salir de la terminal no garantiza por sí solo que la traza esté guardada.»

**Si falla:** usa la captura de Langfuse. No intentes recrear claves o configurar una cuenta durante el directo.

**Transición:** «Ya vemos las ejecuciones. Ahora necesitamos saber exactamente qué instrucciones produjeron cada una.»

---

## 4. Prompts versionados y comparación · 19:10–19:25

### Ver las dos versiones · unos 4 minutos

Abre [v1.txt](/Users/jose/Documents/the-power/1-langGraph/prompts/soporte/v1.txt) y [v2.txt](/Users/jose/Documents/the-power/1-langGraph/prompts/soporte/v2.txt), uno junto al otro.

**Di:**

> «La primera versión define un asistente de soporte de forma general. La segunda concreta cuándo consultar, cuándo pedir un identificador, cómo responder si falla una herramienta y por qué no debe afirmar acciones de escritura.»

Abre [prompts-remotos.json](/Users/jose/Documents/the-power/1-langGraph/material/profesor/prompts-remotos.json). Este manifiesto contiene identificadores y hashes, no claves. Señala la correspondencia de v1/v2 con el commit de LangSmith y la versión de Langfuse. No leas los hashes completos.

### Demostrar que se aplica el prompt remoto · unos 4 minutos

```bash
python langgraph/05_agente_completo.py \
  --observabilidad both --prompts remote --version v2 \
  --hilo "$S6_DEMO-remoto" \
  --pregunta 'Consulta el ticket T-100.' \
  --salida "resultados/$S6_DEMO/remoto.json"
```

**Debe pasar:** `prompt_source: "remote"`, `prompt_version: "v2"`, las identidades remotas y los IDs de ambas trazas. Se ejecuta una respuesta y se registra en las dos plataformas; no se llama dos veces al modelo por usar dos observadores.

Abre [prompts.py](/Users/jose/Documents/the-power/1-langGraph/app/soporte/prompts.py), función `resolve_prompt`. Señala la recuperación, la comprobación del hash y la construcción del prompt que recibe el modelo.

**Di:** «Versionarlo en una web no basta. Debemos recuperar esa versión y utilizarla realmente. Si las copias no coinciden, nuestro programa avisa en lugar de fingir que está usando la versión correcta.»

### Mostrar el experimento preparado · unos 7 minutos

Abre [evaluacion.json](/Users/jose/Documents/the-power/1-langGraph/datos/soporte/evaluacion.json) y después [la tabla de comparación](/Users/jose/Documents/the-power/1-langGraph/material/evidencias/comparacion.md).

**Di:**

> «Este lote se ejecutó durante la preparación, el 2 de octubre. Son diez casos con dos prompts: veinte resultados. Los prompts se fijaron antes de evaluar y cada caso empezó con un hilo vacío. No estamos ejecutando el lote ahora.»

Señala mismos casos, mismo modelo y parámetros, datos iguales e hilos separados. Explica que los ejemplos de desarrollo están en otro fichero.

Abre [la revisión manual](/Users/jose/Documents/the-power/1-langGraph/material/evidencias/revision-manual.md). Resultado del ensayo: **5/10 para v1 y 10/10 para v2**.

**Aclara:** «Es la revisión de estas respuestas con esta rúbrica, realizada por el asistente durante la preparación. No es un benchmark ni demuestra que v2 vaya a acertar siempre. Lo interesante es poder explicar cada fallo.»

**Caso para enseñar:** E09, «¿Qué estado tiene mi ticket?». En el ensayo v1 asumió T-100; v2 pidió el identificador. Abre `resultados.json`, busca `"case_id": "E09"` y compara las dos respuestas.

**Si la respuesta nueva de la demo cambia:** no alteres la tabla anterior. Son ejecuciones diferentes. No edites v2 después de mirar los casos reservados para intentar mejorar el resultado.

**Transición:** «Ahora vamos a interpretar los números sin confundir rapidez, coste y corrección.»

---

## 5. Métricas y valoración · 19:25–19:35

**Haz:** deja a la vista una fila de la comparación y su resultado completo. Explica cuatro cosas, en este orden:

1. **Latencia:** nuestro `duration_s` mide la ejecución del runner hasta el punto en que guarda el tiempo, incluido el envío inicial de trazas; no es exactamente el tiempo de una única llamada al modelo ni todo el tiempo del proceso de terminal.
2. **Consumo:** tokens y número de llamadas. Dos tools no significan necesariamente dos llamadas al modelo.
3. **Coste:** `cost_usd` y el score/feedback `provider_cost_usd` conservan el valor informado por OpenRouter. El coste automático del panel puede usar otra estimación; no lo presentes como factura.
4. **Calidad:** exige leer el resultado y aplicar criterios, no solo comprobar que hay texto.

**Di:**

> «Un resultado rápido puede ser incorrecto. Una respuesta larga puede no aportar nada. Y un coste ausente no es cero: significa que no tenemos ese dato.»

Para enseñar la calidad, abre [la rúbrica](/Users/jose/Documents/the-power/1-langGraph/material/profesor/rubrica-evaluacion.md): contenido correcto, uso adecuado de herramientas y fundamentación. Los tres deben cumplirse para `quality=1`.

**Ejemplo E06:** v1 explica cómo descargar la factura, pero no identifica A-20 como fuente; v2 sí. Úsalo para explicar por qué necesitas criterios escritos antes de puntuar, y que esa puntuación describe la rúbrica concreta.

**Dato opcional:** las veinte consultas del lote definitivo sumaron **0,0032144 USD informados por OpenRouter**. No es el coste de toda la preparación ni una tarifa universal para veinte preguntas.

**Por qué:** la observabilidad sirve para tomar decisiones, pero solo si conoces qué se está midiendo y de dónde sale cada valor.

---

## 6. Fallo, retraso y datos ocultos · 19:35–19:45

### 6.1 Fallo controlado · 19:35–19:38

```bash
python observability/04_incidente.py \
  --hilo "$S6_DEMO-fallo" \
  --pregunta 'Consulta el ticket T-100.' \
  --salida "resultados/$S6_DEMO/fallo.json"
```

**Debe pasar:** la tool provoca un timeout simulado. `errors` contiene `TimeoutError`, la llamada figura con `ok: false` y la respuesta explica que no ha podido consultar. Puede terminar con `status: "done"` porque el agente gestionó el fallo; el número de intentos puede variar hasta el límite de dos.

**Haz:** abre la traza y localiza `consultar_ticket`, el error y la respuesta posterior.

**Di:** «No hemos roto Internet ni el proveedor. Hemos provocado un fallo reproducible en una herramienta para aprender a encontrarlo.»

### 6.2 Retraso controlado · 19:38–19:40

```bash
python observability/04_incidente.py \
  --escenario retraso \
  --hilo "$S6_DEMO-retraso" \
  --pregunta 'Consulta el ticket T-100.' \
  --salida "resultados/$S6_DEMO/retraso.json"
```

**Debe pasar:** la tool devuelve el dato correcto, pero tarda aproximadamente dos segundos adicionales por llamada. `errors` debe estar vacío si no hay una incidencia externa. El tiempo total incluye también al modelo y puede variar.

**Di:** «Lento y fallido son problemas distintos. La traza nos permite ver dónde se ha consumido el tiempo.»

### 6.3 Privacidad · 19:40–19:45

```bash
python observability/06_privacidad.py \
  --hilo "$S6_DEMO-privacidad" \
  --pregunta 'Mi correo ficticio es aula@example.test y mi marcador sintético SECRET_DEMO_123. Consulta T-100.' \
  --salida "resultados/$S6_DEMO/privacidad.json"
```

**Debe pasar:** en la salida guardada y en las trazas aparecen `[EMAIL_OCULTO]` y `[SECRETO_OCULTO]`. No deben aparecer los originales en la raíz ni en sus nodos hijos.

**Haz:** abre input de la raíz y de una llamada al modelo en ambas plataformas. No basta con mirar la respuesta final. Si el tiempo o la carga de las UIs no acompaña, usa las dos capturas verificadas y explica que proceden del ensayo.

**Di:**

> «Esto filtra la telemetría antes de enviarla. No significa que hayamos filtrado automáticamente lo que recibe el proveedor del modelo ni lo que guarda la base local. Por eso usamos datos ficticios. Este filtro es un ejemplo limitado, no un detector universal de datos personales.»

**Comprobación auxiliar, solo si hay tiempo:**

```bash
python scripts/verificar_trazas.py \
  "resultados/$S6_DEMO/privacidad.json" \
  --salida "resultados/$S6_DEMO/privacidad-comprobada.json"
```

Los checks deben ser `True`. La lectura puede tardar: no consumas el bloque del ejercicio esperándola. No pruebes con datos reales de alumnos.

---

## 7. Qué tienen que entregar · 19:45–19:50

Abre [el enunciado S6](/Users/jose/Documents/the-power/1-langGraph/material/alumno/S6-enunciado.md).

**Di:**

> «La práctica consiste en poder demostrar cómo funciona vuestro chatbot, comparar dos versiones de sus instrucciones y localizar un fallo. La evidencia importa tanto como el código.»

Recorre los entregables:

- Chatbot con memoria y herramienta instrumentado en las dos plataformas.
- Dos versiones de prompt guardadas, recuperadas y realmente aplicadas.
- Diez consultas reservadas y comparación con las mismas condiciones.
- Latencia, tools, errores, tokens y coste cuando esté disponible.
- Valoración con criterios previos, fallo simulado y retraso.
- Filtrado demostrado, proyectos privados y explicación de qué datos conservarían y durante cuánto tiempo.
- Código, prompts, resultados y capturas o enlaces accesibles para la revisión.

**Aclara:** no se pide Ragas, un dashboard propio, desplegar el chatbot ni autoalojar las plataformas. Las 3–5 horas son una orientación del trabajo autónomo con el entorno listo.

No les pidas compartir claves ni hacer públicas sus trazas para entregar el ejercicio. El acceso de revisión debe ser el adecuado para la escuela.

---

## 8. Preguntas y cierre · 19:50–20:00

| Pregunta para activar la conversación | Respuesta que quieres reforzar |
|---|---|
| ¿Una traza es una conversación? | No; puede representar una consulta, y una conversación contener varias |
| ¿Por qué guardar la versión del prompt? | Para relacionar un resultado con las instrucciones exactas |
| ¿Por qué diez hilos limpios por versión? | Para que la memoria de un caso no cambie el siguiente |
| ¿`answer_present=1` significa acierto? | No; solo existencia de texto |
| ¿Qué significa coste `null`? | Dato ausente, no coste cero |
| ¿El masking protege también la petición al modelo? | No automáticamente; es otra frontera |

**Cierra diciendo:**

> «El lunes controlábamos la ejecución. Hoy hemos añadido evidencia: sabemos qué pasó, con qué instrucciones, cuánto consumió y dónde falló. El siguiente cambio del agente ya lo podemos comparar con una referencia.»

---

## Si falla una demo o vas tarde

**No ejecutes el lote entero para depurar durante la clase. No cambies credenciales, permisos ni dependencias en directo.**

| Caso | Qué haces | Cómo lo explicas |
|---|---|---|
| Responde, pero no aparece la traza | Confirma ID y proyecto, actualiza una vez; después usa respaldo | «Generación y recepción remota son comprobaciones distintas» |
| Error 403 en LangSmith | Comprueba región y permisos fuera del directo | «Una clave y un endpoint deben corresponder a la misma cuenta/región» |
| Falta un prompt remoto o hash no coincide | No ejecutes `--nuevo`; muestra manifiesto y evidencia previa | «El programa se detiene para no atribuir una respuesta a la versión equivocada» |
| Proveedor no responde | Usa resultados guardados del 02/10 | «Esto es una ejecución anterior identificada, no una nueva» |
| El panel muestra otro coste | Contrasta con `provider_cost_usd` y `cost_method` | «La estimación del panel y el dato del proveedor pueden diferir» |
| Algún check de privacidad da `False` | No lo declares correcto; usa la evidencia validada y revisa después | «Hemos detectado un incumplimiento; no vamos a ocultarlo» |
| Vas 5 minutos tarde | Muestra prompts/versiones con la ejecución previa; omite la nueva llamada remota | Conserva comparación, métricas y privacidad |
| Vas 10 minutos tarde | Usa la captura de una plataforma y el retraso guardado | Mantén un fallo en directo y explica el filtrado |

**Respaldo principal:** [resultados.json](/Users/jose/Documents/the-power/1-langGraph/material/evidencias/resultados.json), [trazas-verificadas.json](/Users/jose/Documents/the-power/1-langGraph/material/evidencias/trazas-verificadas.json) y las dos capturas abiertas al principio. Para fallo/retraso busca esas `etapa` en [ensayo-tecnico.json](/Users/jose/Documents/the-power/1-langGraph/material/evidencias/ensayo-tecnico.json).

**Después de la clase, fuera de los 90 minutos:** si quieres repetir el experimento completo con los prompts ya registrados, ejecuta `python observability/05_comparacion.py`. Consume veinte consultas y deja resultados nuevos en `resultados/comparacion-...`; no sobrescribe la evidencia preparada. La calidad queda pendiente de revisión en el nuevo lote: el script no se pone notas a sí mismo.

Anota las dudas docentes para el siguiente ensayo. No cambies los criterios de la evaluación reservada después de ver sus resultados. La presentación se usa una sola vez al principio. El resto se sigue desde este guion, el código y las plataformas.
