"""Tests de fecha_hoy. Sin red."""

from datetime import date
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from utilities.fecha_hoy import _texto_fecha, consigna_sistema, fecha_hoy


class TestFechaHoy(unittest.TestCase):
    def test_texto_en_espanol(self):
        self.assertEqual(_texto_fecha(date(2026, 8, 17)), "17 de agosto de 2026")

    def test_consigna_lleva_la_fecha(self):
        texto = consigna_sistema(date(2026, 8, 17))
        self.assertIn("17 de agosto de 2026", texto)
        self.assertIn("buscar_web", texto)
        self.assertIn("No inventes", texto)
        self.assertIn("MOCK", texto)

    def test_consigna_honra_al_juez(self):
        texto = consigna_sistema(
            date(2026, 8, 17),
            usar_web=True,
            query_web="temperatura actual Barcelona",
            motivo_validador="falta el número",
        )
        self.assertIn("obliga a buscar_web", texto)
        self.assertIn("temperatura actual Barcelona", texto)
        self.assertIn("falta el número", texto)

    def test_tool_usa_hoy(self):
        with patch("utilities.fecha_hoy.date") as date_cls:
            date_cls.today.return_value = date(2026, 7, 19)
            self.assertEqual(fecha_hoy.invoke({}), "19 de julio de 2026")
