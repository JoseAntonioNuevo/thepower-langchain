# Empezar · S5 y S6

Necesitas Python 3.12, terminal, editor y acceso al modelo. No necesitas frontend, Docker, Tavily ni la TUI para completar estas prácticas. Ejecuta desde la raíz del repositorio.

## Entorno

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-observability.lock
```

En Windows la activación equivalente en PowerShell es `.venv\Scripts\Activate.ps1`. La verificación de este paquete se ha realizado en macOS; el arranque en Windows no se ha comprobado físicamente.

Para la clase 1 basta `requirements-core.lock`. La ampliación con TUI usa `requirements-advanced.lock`. Los tres locks comparten versiones para evitar discrepancias.

Copia `.env.example` a `.env` **solo si aún no tienes uno**. Rellena las variables en tu equipo. Nunca compartas ese archivo. `MODEL_ID` tiene prioridad sobre `OPENROUTER_MODEL`; si ambos están vacíos se utiliza el modelo predeterminado documentado por el preflight. Los parámetros actuales están probados para ese modelo, no para cualquier proveedor.

```bash
python scripts/preflight.py
```

Este comando no llama a APIs. `--online` sí hace una consulta real e instrumenta ambas plataformas; necesita sus claves y puede consumir saldo.

## S5: cinco etapas

```bash
python langgraph/01_grafo.py
python langgraph/05_soporte_chatbot.py --pregunta 'Hola, ¿qué puedes hacer?'
python langgraph/06_soporte_tools.py --pregunta 'Consulta T-100.'
python langgraph/07_soporte_memoria.py --hilo memoria-a --db data/mi-practica.sqlite --pregunta 'Me llamo Alex.'
python langgraph/07_soporte_memoria.py --hilo memoria-a --db data/mi-practica.sqlite --pregunta '¿Cómo me llamo?'
python langgraph/07_soporte_memoria.py --hilo memoria-b --db data/mi-practica.sqlite --pregunta '¿Cómo me llamo?'
python langgraph/08_soporte_completo.py --hilo soporte-a --interactivo
```

Los tres comandos de memoria arrancan procesos distintos. `memoria-a` debe recordar; `memoria-b` no debe conocer el nombre. Para una demostración limpia usa otro nombre de fichero o hilo; no necesitas borrar bases de datos.

- `T-100`: acceso, en curso, artículo `A-10`.
- `T-200`: factura duplicada, resuelto, artículo `A-20`.
- `T-300`: exportación, pendiente de información, artículo `A-30`.
- `T-999`: formato válido pero inexistente.

Todos los datos son ficticios. El grafo permite como máximo dos tools por turno y cuenta intentos fallidos. La memoria por hilo no implementa autenticación.

## S6: seis etapas

```bash
python observability/01_sin_obs.py
python observability/02_langsmith.py
python observability/03_langfuse.py
python observability/04_incidente.py
python observability/04_incidente.py --escenario retraso
python scripts/registrar_prompts.py
python observability/05_comparacion.py
python observability/06_privacidad.py --pregunta 'Mi correo ficticio es aula@example.test y mi marcador sintético SECRET_DEMO_123. Consulta T-100.' --salida resultados/privacidad.json
python scripts/verificar_trazas.py resultados/privacidad.json
```

Configura LangSmith y Langfuse con proyectos propios privados. El nombre remoto del curso se genera una vez y queda registrado en `material/profesor/prompts-remotos.json`. **La copia del profesor apunta a sus prompts**: en una copia propia sustituye ese manifiesto por uno nuevo usando `registrar_prompts.py --nuevo`, que no borra ni sobrescribe los prompts remotos del profesor.

La comparación realiza veinte consultas: diez con cada prompt. Recupera las versiones remotas registradas, verifica sus hashes, usa hilos nuevos y conserva los resultados. No ejecutes el lote repetidamente para intentar obtener mejores puntuaciones. Primero prueba con `datos/soporte/desarrollo.json`.

`--prompts local` usa explícitamente la copia del repositorio; `--prompts remote` falla si no puede verificar las versiones. No hay sustitución silenciosa. Los modos de trazas son `off`, `langsmith`, `langfuse` y `both`.

## Errores habituales

| Síntoma | Comprobación |
|---|---|
| Falta una dependencia | Instalar el lock correspondiente dentro del venv activo |
| Falta una clave | Revisar el nombre indicado por preflight; no imprimir valores |
| LangSmith 403 | Endpoint EU/US debe corresponder a la cuenta; comprobar permisos |
| No aparece una traza | Esperar el envío, comprobar ID con `verificar_trazas.py`; no confundir consola con recepción |
| No recuerda | Mismo fichero SQLite y mismo `--hilo`; otro hilo está aislado |
| Límite de herramientas | Dividir la consulta; no aumentar el límite para ocultar un bucle |
| Coste `null` | No disponible; no significa cero. Verificar consumo/tarifa antes de interpretarlo |
| Caída del proveedor | Mostrar resultados previos identificados como respaldo; no fingir una ejecución nueva |

El filtrado de telemetría sustituye correos y marcadores sintéticos antes de exportar. Es una demostración con reglas limitadas, no un detector universal de datos personales. **No filtra por sí solo lo enviado al proveedor del modelo.** Usar siempre datos sintéticos.

## Tests

```bash
python -m unittest discover -s tests -p 'test_soporte.py'
```

No consumen APIs. La suite completa original también incluye tests de la TUI y requiere el lock avanzado.
