# Ampliación TUI · comprobación del 02/10/2026

Se abrió `langgraph/04_chatbot.py` en una terminal PTY de 80×24 con el modelo configurado. Se envió «Hola». El recorrido mostró juez «sin web», generación, validador «ok» y respuesta «¡Hola! ¿En qué te puedo ayudar?», volviendo al estado listo. Se cerró con Esc.

Es un smoke funcional de arranque, entrada, respuesta y cierre; no sustituye la comprobación de tamaño de letra y pantalla compartida por José. La suite existente conserva los tests de layout, teclado y composición de la interfaz.
