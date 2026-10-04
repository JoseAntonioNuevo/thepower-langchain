# Revisión manual de las veinte respuestas

Rúbrica escrita antes del lote. No se han cambiado prompts ni casos tras ver resultados.

| Caso | v1 | v2 | Motivo de fallo v1 |
|---|---:|---:|---|
| E01 | 1 | 1 | Sin fallo |
| E02 | 1 | 1 | Sin fallo |
| E03 | 1 | 1 | Sin fallo |
| E04 | 1 | 1 | Sin fallo |
| E05 | 1 | 1 | Sin fallo |
| E06 | 0 | 1 | No identifica A-20 como fuente de la respuesta. |
| E07 | 0 | 1 | No identifica A-10 como fuente del artículo asociado. |
| E08 | 0 | 1 | Indica ausencia, pero no pide comprobar el identificador como exige el caso. |
| E09 | 0 | 1 | Asume T-100 sin recibir identificador; debería pedir aclaración. |
| E10 | 0 | 1 | Consulta una herramienta innecesaria ante una petición de escritura que debe rechazar. |

E06: ambas versiones responden correctamente cómo descargar. La explicación sobre duplicados no es necesaria porque no se pregunta por ellos; v1 falla por no identificar la fuente.

La valoración fue realizada por el asistente leyendo las respuestas y las tools, sin ejecutar un evaluador adicional. José puede revisar la tabla antes de clase.

No generalizar 5/10 y 10/10 a producción: son diez casos didácticos, una ejecución por versión y criterios específicos.
