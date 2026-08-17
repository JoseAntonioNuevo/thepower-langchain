"""Comportamiento puro del historial del composer."""

import unittest

from ui.chat_input import HistorialComposer, indice_cursor


class TestHistorialComposer(unittest.TestCase):
    def test_navega_hacia_atras_y_recupera_el_borrador(self):
        historial = HistorialComposer()
        historial.push("primero")
        historial.push("segundo")

        self.assertEqual(historial.anterior("borrador"), "segundo")
        self.assertEqual(historial.anterior("segundo"), "primero")
        self.assertEqual(historial.siguiente(), "segundo")
        self.assertEqual(historial.siguiente(), "borrador")

    def test_no_duplica_envios_consecutivos_y_limita_entradas(self):
        historial = HistorialComposer(limite=2)
        historial.push("uno")
        historial.push("uno")
        historial.push("dos")
        historial.push("tres")

        self.assertEqual(historial.anterior(""), "tres")
        self.assertEqual(historial.anterior("tres"), "dos")
        self.assertEqual(historial.anterior("dos"), "dos")

    def test_siguiente_sin_navegar_devuelve_vacio(self):
        historial = HistorialComposer()
        historial.push("mensaje")

        self.assertEqual(historial.siguiente(), "")

    def test_indice_cursor_linea_y_columna(self):
        self.assertEqual(indice_cursor("", 0), (1, 1))
        self.assertEqual(indice_cursor("hola", 0), (1, 1))
        self.assertEqual(indice_cursor("hola", 4), (1, 5))
        self.assertEqual(indice_cursor("hola\nmundo", 5), (2, 1))
        self.assertEqual(indice_cursor("hola\nmundo", 10), (2, 6))
        self.assertEqual(indice_cursor("hola", 99), (1, 5))


if __name__ == "__main__":
    unittest.main()
