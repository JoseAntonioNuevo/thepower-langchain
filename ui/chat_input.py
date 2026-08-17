"""Estado puro del editor de mensajes: historial y borrador recuperable."""

from __future__ import annotations


class HistorialComposer:
    """Historial pequeño tipo shell para el composer del chatbot.

    ``anterior`` inicia la navegación y conserva el texto que el usuario estaba
    escribiendo. ``siguiente`` recorre hacia el presente y lo restaura al salir
    del historial.
    """

    def __init__(self, limite: int = 50) -> None:
        if limite < 1:
            raise ValueError("limite debe ser mayor que cero")
        self.limite = limite
        self._mensajes: list[str] = []
        self._indice: int | None = None
        self._borrador = ""

    @property
    def navegando(self) -> bool:
        """Indica si las flechas están recorriendo mensajes previos."""
        return self._indice is not None

    def push(self, mensaje: str) -> None:
        """Guarda un mensaje no vacío, sin duplicados consecutivos."""
        mensaje = mensaje.strip()
        if not mensaje:
            return
        if not self._mensajes or self._mensajes[-1] != mensaje:
            self._mensajes.append(mensaje)
            del self._mensajes[:-self.limite]
        self._indice = None
        self._borrador = ""

    def anterior(self, actual: str) -> str:
        """Devuelve el mensaje anterior y guarda ``actual`` como borrador."""
        if not self._mensajes:
            return actual
        if self._indice is None:
            self._borrador = actual
            self._indice = len(self._mensajes)
        self._indice = max(0, self._indice - 1)
        return self._mensajes[self._indice]

    def siguiente(self) -> str:
        """Avanza hacia el presente y restaura el borrador al final."""
        if self._indice is None:
            return ""
        if self._indice < len(self._mensajes) - 1:
            self._indice += 1
            return self._mensajes[self._indice]
        borrador = self._borrador
        self._indice = None
        self._borrador = ""
        return borrador


def indice_cursor(texto: str, offset: int) -> tuple[int, int]:
    """Línea y columna 1-based del cursor. `offset` es en caracteres, no en celdas."""
    # Fallback si el editor nativo no da coordenadas visuales.
    offset = max(0, min(int(offset), len(texto)))
    anterior = texto[:offset]
    linea = anterior.count("\n") + 1
    columna = offset - anterior.rfind("\n")
    return linea, columna
