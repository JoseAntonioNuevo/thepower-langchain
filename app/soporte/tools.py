"""Dos tools locales: sus errores también consumen presupuesto del turno."""

import json
import time
from langchain_core.tools import tool
from pydantic import BaseModel, Field, ConfigDict
from .config import ROOT


class TicketInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ticket_id: str = Field(pattern=r"^T-\d{3}$")


class ArticuloInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    articulo_id: str = Field(pattern=r"^A-\d{2}$")


def make_tools(*, scenario="normal", delay_s=2.0):
    if scenario not in {"normal", "fallo", "retraso"}:
        raise ValueError("Escenario desconocido")
    if not 0 <= delay_s <= 5:
        raise ValueError("El retraso de aula debe estar entre 0 y 5 segundos")
    tickets = json.loads((ROOT / "datos/soporte/tickets.json").read_text())
    articles = json.loads((ROOT / "datos/soporte/articulos.json").read_text())

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

    @tool(args_schema=TicketInput)
    def consultar_ticket(ticket_id: str) -> str:
        """Consulta el estado y el artículo asociado de un ticket ficticio, p. ej. T-100."""
        return lookup(tickets, ticket_id)

    @tool(args_schema=ArticuloInput)
    def buscar_articulo(articulo_id: str) -> str:
        """Obtiene un artículo de ayuda por su identificador, p. ej. A-10. Solo lectura."""
        return lookup(articles, articulo_id)

    return [consultar_ticket, buscar_articulo]
