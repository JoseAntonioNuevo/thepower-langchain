"""Tests de buscar_web. Sin red ni Tavily real."""

import os
import sys
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.append(str(_ROOT))

from app.buscar_web import (
    FALTA_CLAVE,
    _formatear_busqueda,
    _query_fechada,
    buscar_web,
)


class TestBuscarWeb(unittest.TestCase):
    def test_formatea_answer_y_resultados(self):
        texto = _formatear_busqueda(
            {
                "answer": "En Madrid se lleva chaqueta ligera.",
                "results": [
                    {
                        "title": "Moda Madrid",
                        "url": "https://ejemplo.test/moda",
                        "content": "Chaquetas ligeras y zapatillas.",
                    },
                    {
                        "title": "Tendencias",
                        "url": "https://ejemplo.test/tendencias",
                        "content": "Colores claros.",
                    },
                ],
            }
        )
        self.assertIn("En Madrid se lleva chaqueta ligera.", texto)
        self.assertIn("Moda Madrid — Chaquetas ligeras y zapatillas.", texto)
        self.assertIn("https://ejemplo.test/moda", texto)
        self.assertIn("Tendencias", texto)

    def test_snippet_largo_no_se_corta_a_160(self):
        largo = "24 °C " * 40
        texto = _formatear_busqueda(
            {
                "answer": "24 °C en Barcelona.",
                "results": [
                    {
                        "title": "AEMET",
                        "url": "https://ejemplo.test/clima",
                        "content": largo,
                    }
                ],
            }
        )
        self.assertGreater(len(texto), 160)
        self.assertIn("24 °C", texto)

    def test_query_lleva_la_fecha(self):
        self.assertEqual(
            _query_fechada("clima Madrid", date(2026, 8, 17)),
            "17 de agosto de 2026 — clima Madrid",
        )

    def test_sin_resultados(self):
        self.assertEqual(_formatear_busqueda({}), "Sin resultados.")

    def test_sin_clave(self):
        with patch.dict(os.environ, {"TAVILY_API_KEY": ""}, clear=False):
            os.environ.pop("TAVILY_API_KEY", None)
            os.environ.pop("DEMO_FORCE_TOOL_ERROR", None)
            self.assertEqual(buscar_web.invoke({"query": "Madrid"}), FALTA_CLAVE)

    def test_search_mockeado(self):
        payload = {
            "answer": "Soleado.",
            "results": [
                {
                    "title": "AEMET",
                    "url": "https://ejemplo.test/clima",
                    "content": "Sol en Madrid.",
                }
            ],
        }
        with (
            patch.dict(os.environ, {"TAVILY_API_KEY": "test-key"}, clear=False),
            patch("app.buscar_web.TavilyClient") as cliente_cls,
            patch("app.buscar_web.date") as date_cls,
        ):
            os.environ.pop("DEMO_FORCE_TOOL_ERROR", None)
            date_cls.today.return_value = date(2026, 8, 17)
            cliente_cls.return_value.search.return_value = payload
            texto = buscar_web.invoke({"query": "clima Madrid"})
        self.assertIn("Soleado.", texto)
        self.assertIn("AEMET", texto)
        cliente_cls.assert_called_once_with(api_key="test-key")
        cliente_cls.return_value.search.assert_called_once_with(
            "17 de agosto de 2026 — clima Madrid",
            search_depth="advanced",
            include_answer="advanced",
            max_results=5,
            chunks_per_source=3,
            timeout=15,
        )

    def test_error_de_busqueda(self):
        with (
            patch.dict(os.environ, {"TAVILY_API_KEY": "test-key"}, clear=False),
            patch("app.buscar_web.TavilyClient") as cliente_cls,
        ):
            os.environ.pop("DEMO_FORCE_TOOL_ERROR", None)
            cliente_cls.return_value.search.side_effect = RuntimeError("timeout")
            texto = buscar_web.invoke({"query": "Madrid"})
        self.assertEqual(texto, "Error de búsqueda: timeout")


if __name__ == "__main__":
    unittest.main()
