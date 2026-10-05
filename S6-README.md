# S6 · Observabilidad sobre los chatbots existentes

LangSmith y Langfuse se conectan al mismo núcleo `app/soporte` de S5. No se crea otro agente. `template | with_tools` es la cadena de componentes LangChain dentro del nodo `chatbot`; `StateGraph` coordina su ejecución.

## Preparar el entorno

Python 3.12. Mantener los SDK del lock; no actualizar paquetes individuales antes del ensayo.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-advanced.lock
python scripts/preflight.py
```

Para consola sin TUI: `requirements-observability.lock`. Copiar `.env.example` a `.env` solo si no existe. `MODEL_ID` tiene prioridad sobre `OPENROUTER_MODEL`. La disponibilidad del modelo y las cuentas debe verificarse antes del directo. No versionar `.env`.

## Instrumentar los mismos ejemplos

```bash
python langgraph/02_chatbot.py --tui --observabilidad langsmith --hilo s6-chat
python langgraph/05_agente_completo.py --tui --observabilidad langfuse --hilo s6-soporte
python langgraph/05_agente_completo.py --observabilidad both --hilo s6-ambos --pregunta 'Consulta T-100.' --salida resultados/s6-ambos.json
```

02 sigue sin tools y con RAM en la TUI; 03 añade tools con RAM; 04 conserva SQLite sin tools; 05 combina tools y SQLite. La observabilidad no cambia esas capacidades. El ejemplo 01 de mayúsculas no comparte estas opciones de CLI.

Los lanzadores `observability/01_sin_obs.py`, `02_langsmith.py`, `03_langfuse.py`, `04_incidente.py` y `06_privacidad.py` usan el mismo controlador. `05_comparacion.py` ejecuta el lote. Las páginas de `docs/observability` y `_comun.py` corresponden a la referencia histórica del agente avanzado; no sustituyen este recorrido.

## Prompts sin depender de una carpeta privada

```bash
python scripts/registrar_prompts.py
```

Requiere las dos cuentas. Guarda el manifiesto en `data/prompts-remotos.json`, creando el directorio y escribiendo de forma atómica. Si solo existe el manifiesto antiguo en `material/profesor/prompts-remotos.json`, se copia conservando el original. No sobreescribe un manifiesto nuevo ya existente.

El registro propio se puede repetir si v1/v2 siguen coincidiendo con sus hashes: no crea dos versiones más por repetir la orden. Si cambias los textos, conserva el experimento anterior y registra un lote propio nuevo expresamente con `--nuevo`. No hagas ese cambio después de mirar el test reservado.

```bash
python langgraph/05_agente_completo.py --observabilidad both --prompts remote --version v2 --hilo s6-remoto --pregunta 'Consulta T-100.' --salida resultados/s6-remoto.json
```

La resolución usa commit LangSmith y versión Langfuse concretos, verifica el hash y aplica el texto al modelo. Guardar un prompt en una plataforma no equivale a usarlo. Los clientes se mantienen privados; no se cambian permisos ajenos.

## Comparar y revisar, sin autoasignar calidad

```bash
python observability/05_comparacion.py
```

Consume veinte consultas de usuario (las llamadas al modelo pueden ser más), con diez casos por versión y hilos separados. Usa el mismo modelo/parámetros y conserva resultados parciales. La carpeta de salida lleva fecha y microsegundos. `quality` queda pendiente.

Utilidad opcional local; sustituir la ruta por la del lote generado:

```bash
python scripts/resumir_evaluacion.py resultados/MI-LOTE/resultados.json --salida resultados/MI-LOTE/revision-inicial
```

Genera `revision.csv`, `resumen.md`, `resumen.json` y una copia de los resultados. Completa el CSV como texto: `quality` 0/1, con un `motivo`. No cambies query_id, caso ni versión. Cada nueva salida debe ser un directorio que no exista:

```bash
python scripts/resumir_evaluacion.py resultados/MI-LOTE/resultados.json --revision resultados/MI-LOTE/revision-inicial/revision.csv --salida resultados/MI-LOTE/revision-final
```

No llama a APIs, no sube notas a las plataformas y no modifica el archivo de resultados original. Muestra revisados/pendientes y cobertura de métricas. Coste desconocido no equivale a cero; una suma parcial no es el coste total del lote. `answer_present` solo indica que hay texto. La rúbrica debe fijarse antes del test.

## Fallo, retraso y privacidad

```bash
python observability/04_incidente.py --hilo s6-fallo --pregunta 'Consulta T-100.'
python observability/04_incidente.py --escenario retraso --hilo s6-retraso --pregunta 'Consulta T-100.'
python observability/06_privacidad.py --hilo s6-privacidad --pregunta 'Correo ficticio aula@example.test y marcador SECRET_DEMO_123. Consulta T-100.' --salida resultados/s6-privacidad.json
```

Usar hilos nuevos en cada ensayo. Un turno puede acabar en `done` después de gestionar un fallo de tool: revisar también `errors`, `calls.ok` y los descendientes. Las tools son ficticias, de lectura y limitadas a dos intentos por turno.

El masking protege la exportación de telemetría. No filtra automáticamente la petición al modelo ni el historial SQLite; usar datos sintéticos. Comprobar raíz e hijos en ambos servicios, no solo la consola. Mantener proyectos privados, limitar acceso y verificar la retención real.

```bash
python scripts/verificar_trazas.py resultados/s6-privacidad.json --salida resultados/s6-privacidad-verificada.json
```

## Pruebas y alcance

```bash
python -m unittest discover -s tests -p 'test_s6*local.py'
python -m unittest discover -s tests -p 'test_soporte.py'
python -m unittest discover -s tests
```

La preparación de esta mejora ejecutó **32 pruebas locales** de manifiesto, contrato de prompts con servicios simulados y resumen/revisión, sin SDKs ni red. No se ejecutó de nuevo la suite completa del agente ni una integración con cuentas reales en ese entorno. Hay que ejecutar ambas antes de dar por ensayado el directo.

Los materiales de alumno, guiones y presentaciones se distribuyen aparte. `material/` sigue excluido de Git: estas mejoras no publican el material privado del curso ni restauran aquella carpeta.
