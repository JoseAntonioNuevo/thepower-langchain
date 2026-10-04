"""Herramientas de solo lectura sobre datos ficticios del asistente de soporte.

TicketInput y ArticuloInput validan los identificadores y rechazan campos extra.
make_tools carga los JSON y devuelve consultar_ticket y buscar_articulo.
lookup comparte la búsqueda y el formato del resultado: éxito, datos o error.
Los escenarios de fallo y retraso permiten explicar incidentes en la clase S6.
El presupuesto de dos intentos se controla en graph.py, no en este archivo.
"""

import json
import time
from langchain_core.tools import tool
from pydantic import BaseModel, Field, ConfigDict
from .config import ROOT


# Argumentos permitidos para consultar_ticket: T- seguido de tres dígitos.
class TicketInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ticket_id: str = Field(pattern=r"^T-\d{3}$")


# Argumentos permitidos para buscar_articulo: A- seguido de dos dígitos.
class ArticuloInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    articulo_id: str = Field(pattern=r"^A-\d{2}$")


# Crea las herramientas con datos locales; todavía no realiza ninguna consulta.
# Cada ejecución del grafo puede recibir sus propias tools o versiones simuladas.
def make_tools(*, scenario="normal", delay_s=2.0):
    # Acotamos los escenarios y el retraso para mantener la demo controlada.
    if scenario not in {"normal", "fallo", "retraso"}:
        raise ValueError("Escenario desconocido")
    if not 0 <= delay_s <= 5:
        raise ValueError("El retraso de aula debe estar entre 0 y 5 segundos")
    # Los JSON son la fuente de verdad de la demo; no hay acceso a tickets reales.
    tickets = json.loads((ROOT / "datos/soporte/tickets.json").read_text())
    articles = json.loads((ROOT / "datos/soporte/articulos.json").read_text())

    # Busca un identificador y devuelve un texto JSON que podrá leer el modelo.
    # Un recurso ausente devuelve ok=False; un fallo simulado lanza una excepción
    # que el nodo ejecutar_tools convierte en un error controlado.
    def lookup(data, key):
        if scenario == "fallo":
            raise TimeoutError("timeout simulado de aula")
        if scenario == "retraso":
            time.sleep(delay_s)
        value = data.get(key)
        return json.dumps(
            {
                "ok": value is not None,
                "id": key,
                "datos": value,
                "error": None if value else "no_encontrado",
            },
            ensure_ascii=False,
        )

    # @tool convierte la función en una herramienta con esquema validado.
    # Su docstring es la descripción enviada al modelo: forma parte del contrato.
    @tool(args_schema=TicketInput)
    def consultar_ticket(ticket_id: str) -> str:
        """Consulta el estado y el artículo asociado de un ticket ficticio, p. ej. T-100."""
        return lookup(tickets, ticket_id)

    # Misma búsqueda, sobre artículos: solo devuelve contenido, no realiza acciones.
    @tool(args_schema=ArticuloInput)
    def buscar_articulo(articulo_id: str) -> str:
        """Obtiene un artículo de ayuda por su identificador, p. ej. A-10. Solo lectura."""
        return lookup(articles, articulo_id)

    # Este catálogo es el que bind_tools ofrece al modelo y el nodo ejecuta.
    return [consultar_ticket, buscar_articulo]
