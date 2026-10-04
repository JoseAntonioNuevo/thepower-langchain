# Criterios congelados antes de la comparación

Cada caso de `datos/soporte/evaluacion.json` tiene respuesta esperada y herramientas esperadas. Cada versión recibe los mismos datos y parámetros. Los diez casos reservados no se utilizan para mejorar los prompts.

Valorar cada respuesta completa con tres criterios binarios:

1. **Contenido:** responde lo solicitado o pide la aclaración/rechaza la acción que corresponde. En consultas de datos, respeta todos los hechos relevantes del caso esperado.
2. **Herramientas:** emplea las tools necesarias y no ejecuta operaciones innecesarias o inexistentes; nunca supera dos llamadas. Se compara el recorrido observado con la lista esperada.
3. **Fundamentación:** no inventa datos, plazos ni acciones. Las consultas a tickets/artículos identifican su fuente. No es necesario citar una fuente para saludar, aclarar o rechazar una acción.

`quality=1` solo si cumple los tres; `quality=0` si falla alguno. Guardar el motivo de cada fallo. Fallos técnicos del proveedor quedan como no evaluables y se informa cobertura. No convertirlos en aciertos ni ocultarlos.

Esta es una revisión manual del contenido, no un juez LLM automático ni una estimación de calidad en producción. Se conserva el resultado aunque v2 no supere a v1. No ajustar los prompts después de consultar este test.
