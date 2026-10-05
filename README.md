# S5 y S6 · LangGraph y observabilidad

Código de las sesiones del 5 y 7 de octubre de 2026, 18:30–20:00 (Madrid). Ambas reutilizan el soporte de `app/soporte`.

## Instalación

Python 3.12, desde la raíz:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-advanced.lock
python scripts/preflight.py
```

Configura `.env` a partir de `.env.example` solo si no existe. `MODEL_ID` tiene prioridad sobre `OPENROUTER_MODEL`. No compartas ni versiones credenciales. El preflight normal informa de dependencias y configuración; `--online` consume una consulta real. La recepción de trazas se verifica por separado.

Locks: `requirements-core.lock` para S5 sin TUI; `requirements-observability.lock` para S5/S6 en consola; `requirements-advanced.lock` para todo, incluida la TUI.

## Recorrido S5

| Etapa | Comando | Capacidad |
|---|---|---|
| 01 | `python langgraph/01_grafo.py` | Grafo sin modelo |
| 02 | `python langgraph/02_chatbot.py --tui` | Chat, sin tools; RAM de la sesión |
| 03 | `python langgraph/03_herramientas.py --tui` | Tools de lectura; RAM de la sesión |
| 04 | `python langgraph/04_memoria.py --tui --hilo demo` | SQLite, sin tools |
| 05 | `python langgraph/05_agente_completo.py --tui --hilo demo` | Tools y SQLite |

Los ejemplos 02–05 aceptan `--observabilidad off|langsmith|langfuse|both`. El límite es de dos intentos de herramienta por turno; también cuentan los fallidos. Usar otra DB o un hilo nuevo para pruebas limpias. `--salida` permite guardar resultados; la TUI conserva además un archivo por turno. Sin TUI siguen disponibles consola y `--interactivo`.

## Recorrido S6

**[Guía técnica S6: mismos chatbots, trazas, prompts y evaluación](S6-README.md)**.

`observability/01` a `06` cubren referencia sin exportación, LangSmith, Langfuse, incidente, comparación y privacidad. Los lanzadores observan el núcleo de S5: no construyen otro agente. Los prompts remotos se registran en `data/prompts-remotos.json`; se conserva compatibilidad con el manifiesto local antiguo.

## Arquitectura y datos

`app/soporte` separa grafo, herramientas, persistencia, ejecución, configuración, prompts, telemetría, privacidad y evaluación. Modelo, prompt y checkpointer se pueden inyectar para pruebas. Tickets y artículos son ficticios y de solo lectura. `data/` y `resultados/` quedan fuera de Git.

## Tests

```bash
python -m unittest discover -s tests -p 'test_soporte.py'
python -m unittest discover -s tests -p 'test_s6*local.py'
python -m unittest discover -s tests
```

Las pruebas locales usan respuestas o servicios simulados. Una prueba local correcta no demuestra recepción en una plataforma remota. Antes del directo, comprobar una consulta real, el árbol y el masking en ambos servicios.

## Materiales y ampliación

Las presentaciones, notas de Obsidian, guiones y evidencias docentes se distribuyen aparte. La carpeta `material/` se mantiene local y excluida de Git; no es necesaria para registrar prompts desde una copia nueva.

Se conserva el agente avanzado con juez, validador y búsqueda web: `python langgraph/avanzado/04_chatbot.py`. La [guía avanzada original](docs/README-avanzado.md) y el [índice histórico](docs/00_indice.md) documentan esa ampliación, no el recorrido principal de soporte. Las referencias históricas a materiales locales no implican que esos archivos estén presentes en una copia nueva.
