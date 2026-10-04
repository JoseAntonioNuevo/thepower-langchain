# Verificación de la TUI de soporte · 04/10/2026

Las etapas 05–08 admiten `--tui`. Reutilizan el chat, editor y teclado de la TUI original; el panel muestra el grafo de soporte, sin juez ni validador. El modo consola y la TUI avanzada de 04 se conservan.

## Comprobación local

Suite completa: **93 tests correctos**. Dos pruebas nuevas comprueban que el stream ejecuta una sola vez cada llamada al modelo, conserva el historial de sesión, recibe entrada por teclado, muestra tools y respuesta, y guarda el respaldo. Los tests originales de teclado, layout y agente avanzado siguen pasando.

El frame de prueba de la interfaz está en `tui-soporte-frame.txt`. Utiliza un modelo simulado y no representa una consulta remota.

## Comprobación real en terminal con TTY

Lanzador: `08_soporte_completo.py --tui`, DB y hilo exclusivos del ensayo, observabilidad desactivada. Modelo efectivo: `openai/gpt-6-luna`.

| Consulta escrita en la TUI | Resultado comprobado | Tools | Duración del turno |
|---|---|---|---|
| Consulta T-100 y su artículo de ayuda asociado | T-100 en curso, sin plazo confirmado; artículo A-10 y ayuda de acceso | 2 | 4,118 s |
| Vuelve a consultar el artículo que acabamos de leer y resúmelo en dos pasos | Resuelve la referencia a A-10 desde el historial y vuelve a consultarlo | 1 | 2,029 s |

Ambos turnos terminaron con `status: done`. Esc cerró la TUI con código 0 y devolvió la terminal. Resultados locales en `resultados/ensayo-tui-20261004-a83f-turnos/`; están ignorados por Git.

Esta comprobación cubre el nuevo recorrido visual y el seguimiento real en el agente completo. No equivale a un ensayo cronometrado de toda la clase ni a nuevas lecturas remotas de LangSmith/Langfuse. Las evidencias anteriores de esas integraciones se conservan en VERIFICACION.md.

## Guion y preparación

S5-guion.md abre las etapas con `--tui`, indica qué escribir y cuándo salir. El reinicio de SQLite se demuestra cerrando y reabriendo la TUI con la misma DB e hilo. Para el directo se utiliza el entorno con `requirements-advanced.lock`; preflight informa también de OpenTUI. Los JSON son archivos de respaldo.

OpenViking: sin entrega de memoria porque la selección de cuenta para este repositorio sigue sin resolver. No se ha usado otra cuenta.
