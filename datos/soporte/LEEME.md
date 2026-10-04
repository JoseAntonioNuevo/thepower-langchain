# Datos ficticios del agente de soporte

Los JSON se mantienen sin comentarios para que sigan siendo válidos. Las herramientas de `app/soporte/tools.py` los cargan y consultan en modo de solo lectura.

## tickets.json · etapa 03

Cada clave es un identificador de ticket, como `T-100`. Su registro contiene:

| Campo | Qué representa |
|---|---|
| `estado` | Situación actual del ticket |
| `asunto` | Problema que describe |
| `articulo` | Identificador de la ayuda asociada |
| `actualizacion` | Información disponible para responder sin inventar detalles |

T-100 está en curso y remite a A-10. No tiene una fecha de resolución confirmada. T-999 no existe: se utiliza para demostrar el error controlado.

## articulos.json · etapa 03

Cada clave identifica un artículo, como `A-10`. `titulo` describe la ayuda y `texto` contiene sus instrucciones. A-10 explica la recuperación de acceso, la revisión de spam y que no se debe compartir la contraseña.

## Cómo se utilizan

`consultar_ticket` y `buscar_articulo` validan el formato de su argumento y llaman a `lookup`. Esta función devuelve `ok`, `id`, `datos` y `error`. El nodo `ejecutar_tools` entrega ese resultado al modelo mediante un `ToolMessage`; después el modelo redacta la respuesta.

Estos datos son ficticios. Las herramientas no modifican los archivos ni realizan acciones sobre cuentas.
