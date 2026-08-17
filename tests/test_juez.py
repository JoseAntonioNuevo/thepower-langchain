"""Tests del juez: parseo y ruta tras el chatbot. Sin red."""

import sys
import unittest
from datetime import date
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.append(str(_ROOT))

from langchain_core.messages import AIMessage, HumanMessage

from app.juez import (
    consigna_juez,
    es_turno_nuevo,
    parsear_veredicto,
    ruta_tras_chatbot,
)


class TestJuez(unittest.TestCase):
    def test_consigna_lleva_la_fecha(self):
        texto = consigna_juez(date(2026, 8, 17))
        self.assertIn("17 de agosto de 2026", texto)
        self.assertIn("usar_web:", texto)

    def test_parsea_si_y_query(self):
        v = parsear_veredicto(
            "usar_web: si\n"
            "query: temperatura actual Barcelona 17 agosto 2026\n"
            "motivo: pide un número actual"
        )
        self.assertTrue(v.usar_web)
        self.assertIn("Barcelona", v.query)
        self.assertIn("número", v.motivo)

    def test_parsea_no(self):
        v = parsear_veredicto("usar_web: no\nquery:\nmotivo: es un saludo")
        self.assertFalse(v.usar_web)
        self.assertEqual(v.motivo, "es un saludo")

    def test_ilegible_no_obliga_web(self):
        v = parsear_veredicto("hola qué tal")
        self.assertFalse(v.usar_web)
        self.assertEqual(v.motivo, "veredicto ilegible")

    def test_ruta_con_tools(self):
        msg = AIMessage(
            content="",
            tool_calls=[{"name": "buscar_web", "args": {"query": "x"}, "id": "1"}],
        )
        self.assertEqual(ruta_tras_chatbot(msg), "tools")

    def test_ruta_sin_tools(self):
        self.assertEqual(ruta_tras_chatbot(AIMessage("hola")), "validador")

    def test_turno_nuevo_vs_reintento(self):
        self.assertTrue(es_turno_nuevo(HumanMessage("hola")))
        self.assertFalse(es_turno_nuevo(AIMessage("hola")))


if __name__ == "__main__":
    unittest.main()
