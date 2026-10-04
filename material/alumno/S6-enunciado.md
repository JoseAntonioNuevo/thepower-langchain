# Enunciado enviado el 29/09/2026

Transcripción del documento enviado a Laura; sin cambios de requisitos.

Sesión 6 · Observability: Langfuse + LangSmith
Gestionar prompts, medir resultados e instrumentar un grafo de LangGraph
Enunciado
Instrumenta un chatbot con memoria y una herramienta para entender cómo responde, cuánto tarda y dónde falla. Utiliza Langfuse y LangSmith, gestiona versiones del prompt y compara sus resultados con datos de ejecución.
Explicación completa del ejercicio
Puedes usar el grafo de la Sesión 5 o crear uno pequeño equivalente. Trabaja con datos sintéticos y configura por variables de entorno el modelo, las claves y los proyectos de Langfuse y LangSmith. No es necesario instalar por tu cuenta las dos plataformas ni desplegar el chatbot.
Registra el recorrido completo. Instrumenta la entrada, cada llamada al modelo, las herramientas y la respuesta final en ambas plataformas. Añade identificador de consulta, conversación, modelo y versión del prompt. Una traza debe permitir relacionar estos pasos, no ser solo una copia de la respuesta. Evita duplicar registros dentro de una misma ejecución.
Gestiona dos prompts. Guarda una versión inicial y otra mejorada en los gestores de prompts de Langfuse y LangSmith. Recupera una versión concreta desde cada servicio y deja constancia de cuál produjo cada respuesta. Trabaja las mejoras con ejemplos de desarrollo y fija los prompts antes de evaluarlos.
Compara con las mismas preguntas. Reserva diez consultas con un resultado esperado y ejecuta ambas versiones con el mismo modelo y parámetros. Puedes enviar cada ejecución a las dos plataformas o realizar dos pasadas identificadas. Registra duración, llamadas a herramientas, errores y tokens. Comprueba que el coste aparece; si falta, revisa el consumo y configura el precio del modelo, sin inventar datos ausentes.
Evalúa y depura. Asigna manualmente un acierto o fallo según criterios escritos antes de la prueba: responder lo solicitado, utilizar la herramienta cuando corresponde y no inventar resultados. Añade una ejecución con un fallo simulado de herramienta y otra con un retraso controlado. Localiza ambos en las trazas y explica qué nodo causó el problema. No se exige todavía un evaluador con Ragas.
Protege la información. No envíes claves ni datos personales a las trazas. En Langfuse utiliza su mecanismo de masking para ocultar campos sensibles antes de enviarlos; en LangSmith configura la ocultación o transformación de inputs y outputs. Prueba el filtrado con un correo ficticio y confirma que queda oculto en ambas plataformas. Mantén los proyectos privados y explica qué datos guardarías y durante cuánto tiempo.
Ampliación opcional. Añade una alerta de latencia o una puntuación automática sencilla. No es necesario construir un panel propio.
Entrega y valoración. Entrega la instrumentación, prompts, resultados y capturas o enlaces accesibles de las dos plataformas. Incluye una comparación breve de cómo ayudan a localizar errores. Se valorarán las trazas completas, el vínculo con la versión del prompt, las métricas interpretadas y la protección de datos.
Dedicación orientativa: 3–5 horas activas con cuentas y chatbot preparados.
Documentación de apoyo: Langfuse con LangGraph · LangSmith con LangGraph · Masking en Langfuse · Privacidad en LangSmith

