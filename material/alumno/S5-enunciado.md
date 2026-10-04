# Enunciado enviado el 29/09/2026

Transcripción del documento enviado a Laura; sin cambios de requisitos.

Sesión 5 · LangGraph: State Machines para agentes
Crear un grafo, convertirlo en chatbot y añadir memoria y herramientas
Enunciado
Construye por etapas un asistente de soporte ficticio. Empieza con un grafo sencillo, conviértelo en un chatbot y añade memoria y dos herramientas. El resultado debe mostrar qué camino sigue cada consulta y terminar de forma controlada.
Explicación completa del ejercicio
Usa Python, LangGraph y un modelo con soporte de herramientas, configurado mediante MODEL_ID. Guarda las dependencias en un archivo de bloqueo y las credenciales fuera del repositorio. Basta una terminal o un notebook; no se pide frontend, RAG ni despliegue.
Primero, el grafo. Define el estado con los mensajes, el número de llamadas a herramientas y los errores. Crea nodos y conexiones con StateGraph, un inicio y un final. Haz funcionar primero una respuesta fija; después sustitúyela por una llamada real al modelo. Conserva estas etapas en commits o ejemplos ejecutables.
Después, la conversación. Añade instrucciones de soporte y permite varios turnos. El modelo debe poder contestar directamente o solicitar una herramienta. Representa esa decisión con una conexión condicional: si necesita una herramienta, ejecútala y devuelve su resultado al modelo; si ya puede responder, termina.
Añade memoria. Instala también langgraph-checkpoint-sqlite y utiliza SqliteSaver como checkpointer para conservar el estado entre turnos. Usa un thread_id distinto por conversación. Comprueba que puedes continuar tras reiniciar el programa y que dos conversaciones no mezclan mensajes. Un identificador de conversación separa el estado, pero no sustituye la autenticación de una aplicación pública.
Añade dos herramientas. Implementa consultar_ticket y buscar_articulo sobre un diccionario o archivo JSON ficticio. La primera devuelve el estado de un ticket y la segunda una ayuda breve. Ambas serán de solo lectura. Valida los argumentos y responde de forma controlada si el identificador no existe; nunca ejecutes código o comandos generados por el modelo.
Prueba las rutas. Demuestra una respuesta directa, el uso de cada herramienta, una pregunta que dependa del turno anterior, la continuación tras reinicio y dos conversaciones separadas. Limita a dos llamadas a herramientas por turno. Añade pruebas con respuestas simuladas para comprobar argumentos inválidos, fallos y agotamiento del límite sin provocar más llamadas de pago.
Ampliación opcional. Muestra la respuesta por streaming o incorpora una pausa para pedir confirmación antes de una acción. No añadas operaciones reales de escritura como parte de la demo mínima.
Entrega y valoración. Entrega código, datos ficticios, README y un esquema del grafo con ejemplos de las rutas. Se valorarán la evolución por etapas, el manejo del estado, la memoria persistente, las herramientas validadas y la terminación sin bucles.
Dedicación orientativa: 3–5 horas activas con entorno y acceso al modelo preparados.
Documentación de apoyo: LangGraph: grafos y estado · Persistencia · langgraph-checkpoint-sqlite

