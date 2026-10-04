# Matriz de cobertura del ejercicio

Los checks finales y sus fechas se registran en `../evidencias/VERIFICACION.md`. Esta tabla ubica la implementación; por sí sola no certifica una ejecución remota.

| Requisito | Ejemplo o implementación | Verificación |
|---|---|---|
| Grafo fijo y evolución | 01_grafo, 01–05 | Grafo sin red + comandos de ensayo |
| Modelo configurable | app/soporte/config.py | Precedencia y preflight |
| Dependencias bloqueadas | requirements-core/observability/advanced.lock | Instalación limpia |
| Dos tools de soporte | datos/soporte y tools.py | Uso de cada tool y respuesta asociada |
| Validación y ausentes | Esquemas Pydantic + lookup | Argumento inválido, T-999, timeout |
| Dos tools por turno | graph.py | Tercera bloqueada; múltiples solicitudes; rechazo final |
| Reinicio de contadores | Nodo inicio | Segundo turno conserva historial y reinicia presupuesto |
| SQLite y dos conversaciones | persistence.py, 07_soporte_memoria | Subprocess y ensayo real A/A/B |
| Sin frontend ni cloud | CLI Python | Lock básico sin OpenTUI |
| Mismo grafo en S6 | runner.py | Todos los modos usan build_graph |
| Trazas completas | telemetry.py | Lectura remota raíz/hijos y número de modelos |
| No duplicar consumo | callbacks en una invocación | Modelo invocado una vez por paso; árbol remoto |
| Dos prompts aplicados | prompts.py | Hash remoto/local, metadatos y SystemMessage real |
| Diez casos por versión | evaluacion.json, evaluation.py | 20 filas e hilos únicos; mismo test |
| Calidad manual | rubrica-evaluacion.md | Revisión de veinte respuestas con motivos |
| Tokens/coste/latencia | runner.py | Datos reales del proveedor; ausentes null |
| Fallo y retraso | make_tools(escenario) | Dos ejecuciones y trazas independientes |
| Filtrado | privacy.py | Mensajes Pydantic y export; readback de ambas plataformas |
| Flush en error | telemetry.turn/close | Test finally + lectura después del cierre |
| Material docente | Guiones S5/S6 + PPTX/PDF | Render, notas, QR decodificado y 90 minutos |
| Enunciados fieles | material/alumno/S5 y S6 | Transcripción del DOCX enviado el 29/09 |
| Respaldo identificado | material/evidencias | Archivos fechados y guía de recuperación |

## Valoración sugerida del ejercicio S5

No es una nueva rúbrica oficial de la escuela. Revisar: etapas comprensibles; grafo correcto; herramientas y errores; memoria tras reinicio; aislamiento y límites; reproducción/documentación. Una interfaz bonita no compensa incumplir persistencia o límites.

## Valoración sugerida del ejercicio S6

Revisar: trazas en ambos servicios; versiones realmente aplicadas; comparación sin contaminación; métricas interpretadas; incidentes localizables; protección y retención de datos; evidencia accesible. No pedir Ragas ni mejoras obligatorias de v2 sobre v1.

## Retención para el laboratorio

Usar únicamente datos sintéticos y proyectos privados. Anotar la retención efectiva de la cuenta en el ensayo; no cambiar políticas compartidas. Para material local, conservar únicamente los resultados sintéticos necesarios para las clases y retirar copias de trabajo al terminar el curso. No atribuir al SDK una política de retención que pertenece al servicio.
