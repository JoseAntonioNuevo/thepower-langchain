# S5 y S6 · LangGraph y observabilidad

Paquete docente para **5 y 7 de octubre de 2026, 18:30–20:00 (Madrid)**.

**[Abrir materiales, guiones, presentaciones y evidencias](material/README.md)**

## Instalación y comprobación

Python 3.12. Desde la raíz del repositorio:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-advanced.lock
python scripts/preflight.py
```

Copia `.env.example` a `.env` solo si no existe y rellena las claves localmente. `MODEL_ID` tiene prioridad sobre `OPENROUTER_MODEL`. No compartas ni versiones `.env`. El preflight normal no usa red; `--online` sí consume una consulta real y comprueba las dos integraciones.

- `requirements-core.lock`: S5, sin TUI.
- `requirements-observability.lock`: S5 + S6.
- `requirements-advanced.lock` / `requirements.txt`: todo, incluida la ampliación original.

## Recorrido principal

| Clase | Comando / carpeta | Qué demuestra |
|---|---|---|
| S5 etapa 1 | `python langgraph/01_grafo.py` | Grafo fijo sin modelo |
| S5 etapa 2 | `python langgraph/05_soporte_chatbot.py --tui` | Mensajes y modelo |
| S5 etapa 3 | `python langgraph/06_soporte_tools.py --tui` | Tools locales validadas |
| S5 etapa 4 | `python langgraph/07_soporte_memoria.py --hilo demo --tui` | SQLite y continuidad |
| S5 etapa 5 | `python langgraph/08_soporte_completo.py --hilo demo --tui` | Agente completo con máximo dos tools |
| S6 | `observability/01` a `06` | Baseline, plataformas, incidente, comparación y privacidad |

La TUI de soporte reutiliza el chat y teclado de la interfaz original, con un panel para los nodos reales del soporte. Sin SQLite conserva historial en RAM durante esa sesión; con SQLite continúa tras cerrar y abrir. `--salida` guarda el último resultado y todos los turnos en una carpeta de respaldo. Sin `--tui` siguen disponibles las ejecuciones de consola y `--interactivo`.

Comandos exactos, reinicio y errores: **[Empezar](material/alumno/EMPEZAR.md)**.

## Arquitectura

`app/soporte` es el núcleo común de ambas clases. Modelo, prompt y checkpointer son inyectables. Los scripts de S6 lo instrumentan sin construir otro agente. Los datos de tickets/artículos son ficticios; todas las herramientas son de lectura.

`data/` contiene SQLite y `resultados/` las ejecuciones; ambos están ignorados. Usa otro fichero o hilo para una demo limpia. Los prompts remotos tienen versiones inmutables en un manifiesto propio; no se sobrescriben prompts ajenos.

## Tests

```bash
python -m unittest discover -s tests -p 'test_soporte.py'
# Suite completa: requiere el lock avanzado
python -m unittest discover -s tests
```

Los tests no consumen APIs. Las pruebas reales se ejecutan expresamente y quedan identificadas en material/evidencias.

## Ampliación original

Se conserva el agente con juez, validador, búsqueda web y TUI. Arranque: `python langgraph/04_chatbot.py`, tras instalar el lock avanzado. Los ejemplos antiguos `02_tools.py` y `03_memoria.py` siguen disponibles, pero no sustituyen la memoria SQLite de la práctica.

La [guía avanzada original](docs/README-avanzado.md) conserva el contexto histórico de construcción; sus referencias al recorrido de observabilidad son anteriores a este paquete. [Documentación del agente avanzado](docs/00_indice.md).

## Evidencia de preparación

Consultar **[VERIFICACION](material/evidencias/VERIFICACION.md)** para saber qué se ejecutó realmente. Una presentación creada, un test local y una traza leída desde el servicio son pruebas distintas. El ensayo oral y la entrada en la reunión quedan a cargo del profesor.
