# Paquete docente · LangGraph y observabilidad

**S5:** lunes 5 de octubre de 2026 · **S6:** miércoles 7 de octubre de 2026. Ambas de 18:30 a 20:00, Europe/Madrid.

## Abrir antes del directo

| Material | LangGraph | Observabilidad |
|---|---|---|
| Google Slides · edición integrada | [LangGraph](https://docs.google.com/presentation/d/1zdLf5JfQbAfl4EtaO-23HvHKlpaWoWiNwX2UKXkcQKw/edit) | [Observabilidad](https://docs.google.com/presentation/d/1hzYAl_3BanFKr-xkek2CgN55P2dqBpSAKaZVoFGU6a8/edit) |
| Presentación local | [S5-langgraph.pptx](presentaciones/S5-langgraph.pptx) | [S6-observabilidad.pptx](presentaciones/S6-observabilidad.pptx) |
| Respaldo PDF | [S5-langgraph.pdf](presentaciones/S5-langgraph.pdf) | [S6-observabilidad.pdf](presentaciones/S6-observabilidad.pdf) |
| Guion paso a paso del directo | [S5: qué decir, ejecutar y comprobar](profesor/S5-guion.md) | [S6: qué decir, ejecutar y comprobar](profesor/S6-guion.md) |
| Enunciado enviado | [S5](alumno/S5-enunciado.md) | [S6](alumno/S6-enunciado.md) |
| Preparación y errores | [Guía del alumno](alumno/EMPEZAR.md) | [Guía del alumno](alumno/EMPEZAR.md) |
| Solución y contratos | [Referencia](profesor/SOLUCION.md) | [Referencia](profesor/SOLUCION.md) |
| Cobertura | [Matriz](profesor/COBERTURA.md) | [Matriz](profesor/COBERTURA.md) |
| Evidencia actual | [Verificación](evidencias/VERIFICACION.md) | [Verificación](evidencias/VERIFICACION.md) |

Los enunciados transcriben el documento enviado el 29/09. Las guías son material complementario; no cambian requisitos. La solución del profesor está separada de los enunciados, pero vive en este repositorio: compartir la carpeta `alumno` si se quiere entregar solo el ejercicio.

**Para seguir la clase:** abre el guion de S5 o S6 en una pantalla no compartida. El primer bloque indica las ocho diapositivas de la introducción. Los siguientes indican hora, frase sugerida, archivo, comando, resultado esperado y alternativa si falla, sin volver al PowerPoint. Incluye preparación previa y recortes si vas justo de tiempo; no necesitas reconstruir los pasos desde las notas del PPTX.

Las dos presentaciones se utilizan **solo al inicio, de 18:30 a 18:40**. Tienen **8 diapositivas**, con notas que suman diez minutos, el logo original thePower en portada y el QR original. Después se cierra el modo presentación y se sigue el guion desde editor, terminal y plataformas.

LangGraph explica qué es, cómo se relaciona con LangChain y qué construiremos por etapas. Observabilidad sitúa LangSmith/Langfuse, el recorrido de la práctica y qué evidencia queremos obtener. Se mantiene el fondo azul oscuro, los acentos cian/violeta y la tipografía Inter. La versión anterior de quince diapositivas está archivada en `profesor/presentaciones/version-previa-intro-2026-10-04/`.

## Recorrido

Primero `langgraph/01_grafo.py`, después los ejemplos de soporte `05` a `08`. El miércoles se ejecutan `observability/01` a `06`, sobre el mismo núcleo `app/soporte`.

Los ejemplos antiguos `02_tools`, `03_memoria` y `04_chatbot` conservan la demo avanzada original. La TUI requiere dependencias adicionales y no es necesaria para la práctica básica.

## QR

[Original de Laura](assets/qr-ai-engineer.jpg). Se muestra para valorar la **clase anterior**, no para entregar el ejercicio. Se ha decodificado el destino, sin enviar respuestas al formulario.

## Cuándo está lista una clase

Distinguir archivos creados, tests locales, integración remota, revisión visual y ensayo del profesor. La evidencia fechada contiene las verificaciones realizadas y los límites restantes. El ensayo oral, la entrada en la reunión y la confirmación de grabación corresponden a José antes del directo.
