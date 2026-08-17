"""Salida compartida de consola para las lecciones 01–03."""

from __future__ import annotations

import io
import os
import time
import unittest
from unittest.mock import patch

from ui.consola import banner, grafo_ascii, panel, spinner


class _TtyBuffer(io.StringIO):
    def isatty(self) -> bool:
        return True


class TestConsola(unittest.TestCase):
    def test_banner_panel_y_grafo_conservan_el_contenido(self):
        salida = "\n".join(
            (
                banner("01", "Grafo explícito", 12),
                panel("estado", "hola thepower\nHOLA THEPOWER"),
                grafo_ascii(["mayusculas"]),
            )
        )

        for trozo in (
            "01",
            "Grafo explícito",
            "12 min",
            "estado",
            "hola thepower",
            "HOLA THEPOWER",
            "START",
            "mayusculas",
            "END",
        ):
            self.assertIn(trozo, salida)

    def test_banner_tiene_bordes_alineados(self):
        lineas = banner("01", "Grafo explícito", 12).splitlines()

        self.assertEqual(len({len(linea) for linea in lineas}), 1)

    def test_no_color_no_emite_secuencias_ansi(self):
        with patch.dict(os.environ, {"NO_COLOR": "1"}):
            salida = banner("01", "Grafo", 12) + panel("estado", "ok")

        self.assertNotIn("\x1b[", salida)

    def test_sin_tty_el_spinner_no_contamina_la_salida(self):
        stream = io.StringIO()

        with spinner("modelo", stream=stream):
            pass

        self.assertEqual(stream.getvalue(), "")

    def test_spinner_limpia_la_linea_al_salir(self):
        stream = _TtyBuffer()

        with spinner("modelo", stream=stream, enabled=True, interval=0.001):
            time.sleep(0.005)

        self.assertIn("modelo", stream.getvalue())
        self.assertTrue(stream.getvalue().endswith("\r"))


if __name__ == "__main__":
    unittest.main()
