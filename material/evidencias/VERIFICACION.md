# Verificación de S5 y S6 · pruebas técnicas del 2 de octubre de 2026

**Presentaciones revisadas el 04/10/2026:** ocho diapositivas por clase para una introducción de diez minutos, logo original en ambas portadas y guiones ajustados. Las pruebas de código descritas abajo conservan su fecha original.

## Resultado

Paquete técnico y docente preparado localmente. El ensayo oral de José, su ajuste al grupo y la comprobación de la reunión/grabación no se sustituyen por pruebas automáticas. No se ha hecho commit, push ni envío a Laura.

| Área | Evidencia obtenida |
|---|---|
| Suite completa | **91 tests correctos**: 73 existentes + 18 nuevos |
| Entorno limpio de observabilidad | Instalación desde lock y 18 tests nuevos correctos; demos reales ejecutadas |
| Calidad estática | Ruff en núcleo/scripts/tests nuevos y `git diff --check` correctos |
| S5 real | Grafo, chatbot, tools, memoria entre procesos y agente completo |
| Memoria | Hilo A recuerda Alex tras reiniciar; hilo B no conoce el nombre |
| S6 real | Baseline, LangSmith, Langfuse, fallo y retraso |
| Prompts | v1/v2 privados en ambos gestores; hashes comprobados y versiones aplicadas |
| Comparación definitiva | 20 resultados, 10 casos por versión, conversaciones nuevas y modelo/parámetros comunes |
| Lectura remota | Las 20 consultas leídas desde ambas plataformas; una raíz y número esperado de generaciones |
| Privacidad | Lectura remota raíz/hijos sin correo ni marcador sintético originales; tests de payload/Pydantic |
| Capturas | Interfaces reales de LangSmith y Langfuse, con entrada filtrada visible |
| TUI avanzada | Arranque en PTY, saludo real, juez/validador/respuesta y cierre con Esc |
| Presentaciones | 2 PPTX editables de 8 diapositivas, introducción de diez minutos, logo original, notas, diagramas editables y QR |
| QA de presentaciones | Integridad, geometría, fuente, importación y revisión visual de las 16 diapositivas introductorias; corregidos ajuste de flechas, etiqueta de tool y texto de privacidad |
| PDF | Dos respaldos de 8 páginas derivados de los renders revisados; comprobación visual del resultado |
| QR | Original de Laura decodificado; destino AI Engineer comprobado sin enviar formulario |

## Abrir la evidencia

- [Resultados JSON](resultados.json), [CSV](resultados.csv), [tabla](comparacion.md) y [revisión de respuestas](revision-manual.md).
- [Lecturas remotas de 20 consultas](trazas-verificadas.json): IDs, enlaces, nodos y comprobaciones.
- [Verificación específica de privacidad](privacidad-verificada.json).
- [Coste y calidad releídos del servicio](scores-verificados.json).
- [Ensayo técnico por etapa](ensayo-tecnico.json) y [smoke TUI](tui-smoke.md).
- [Captura LangSmith](langsmith-privacidad.png) y [captura Langfuse](langfuse-privacidad.png).
- Recibos estructurales: [S5](S5-langgraph-validacion.json) y [S6](S6-observabilidad-validacion.json).

## Comparación y procedencia

Lote definitivo: `comparacion-20261002T093640Z`, modelo `openai/gpt-6-luna`, a través de OpenRouter. Prompts y casos se congelaron antes del lote. La revisión manual del asistente, con la rúbrica previa, da **v1: 5/10; v2: 10/10**. No es un juez automático ni una valoración realizada por José. Es una muestra didáctica pequeña y no prueba calidad de producción.

El lote definitivo suma **0,0032144 USD informados por OpenRouter**. Es el coste de esas veinte consultas, no el gasto total de preparación. El coste inferido automáticamente por las plataformas puede diferir del proveedor: se conserva el dato de OpenRouter y se registra expresamente como `provider_cost_usd`, sin cambiar tarifas globales de la cuenta.

## Tiempos medidos

Las demos medidas, sin explicación oral, tardaron aproximadamente:

- Chatbot 1,4 s; tools 2,0 s; agente completo 2,9 s.
- Escribir memoria 1,0 s; leer tras reinicio 0,9 s; hilo aislado 1,1 s.
- Baseline 4,1 s; LangSmith 3,0 s; Langfuse 3,4 s.
- Fallo simulado 2,9 s; escenario con dos retrasos controlados 7,4 s.

Son tiempos observados de esas consultas, no una garantía futura. Los guiones reservan bloques de explicación y 10 minutos de preguntas. El lote comparativo se lleva ejecutado; durante el directo basta mostrar casos representativos.

## Fallos detectados y resueltos durante la preparación

1. Timeout del adaptador interpretado en milisegundos y reintentos internos: corregidos y cubiertos por test.
2. Contexto de LangSmith desactivaba el tracer explícito: corregido y comprobado mediante lectura real. Se repitió el lote afectado; el lote preliminar no se usa como evidencia de doble instrumentación.
3. Mensajes Pydantic no recorridos por el filtro inicial: corregido y probado en payload y ambos servicios. El ensayo usó únicamente marcadores ficticios.
4. El lock reducido omitía `langchain`, requerido por el callback de Langfuse: corregido y ensayado desde el entorno limpio.
5. Diferencia entre coste inferido y coste del proveedor: diferenciada y registrada explícitamente, sin inventar valores.

## Límites y preparación humana restante

- José debe leer los guiones, revisar la rúbrica y hacer su ensayo oral antes de cada clase.
- Antes del directo: abrir cuentas, comprobar reunión/pantalla compartida/grabación y ejecutar una consulta breve. No se ha entrado en ninguna reunión ni se ha enviado material a alumnos.
- Las demos principales se verificaron en macOS/Python 3.12. Las instrucciones de Windows no se han ensayado en un dispositivo Windows.
- Los proyectos y prompts se mantienen privados. No se han cambiado permisos, planes de pago ni políticas de retención. El filtrado didáctico no sustituye una política completa de privacidad ni filtra automáticamente la petición al proveedor.
- Los SDK están bloqueados. LangSmith emite avisos de deprecación sobre algunas APIs de lectura/feedback que siguen funcionando con esta versión; revisar antes de reutilizar el curso después de enero de 2027.
- OpenViking no tiene cuenta asignada a este repositorio. Esta entrega y sus aprendizajes quedan documentados localmente, sin utilizar otro tenant.

## Actualización visual con referencias de Drive

Se integró el contenido nuevo usando la presentación LangGraph original como referencia para ambas clases. Se crearon dos copias nativas privadas en las carpetas de cada clase, preservando los originales. Se verificaron 15 diapositivas por deck, notas, tablas nativas y QR; se revisaron todos los renders y se corrigió código antiguo dentro de imágenes, el retorno de las herramientas y el ajuste de un bloque SQLite. Los PowerPoint y PDF locales son exportaciones de estas versiones cloud. Las comprobaciones del código y del modelo anteriores siguen siendo aplicables: esta actualización afecta a presentaciones y enlaces.
