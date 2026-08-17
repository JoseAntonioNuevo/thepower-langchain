"""Tests del validador: heurística, parseo y tope de reintentos. Sin red."""

import sys
import unittest
import importlib
from pathlib import Path
from unittest.mock import patch

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, ToolMessage

from utilities.validador import (
    consigna_validador,
    debe_reintentar,
    parsear_veredicto,
    rechazo_heuristico,
    ruta_tras_validador,
)


class TestValidador(unittest.TestCase):
    def test_rechaza_mock_de_clima(self):
        motivo = rechazo_heuristico(
            pregunta="qué tiempo hace en BCN",
            respuesta="Soleado en Barcelona",
            usar_web=False,
            hubo_buscar_web=False,
        )
        self.assertIsNotNone(motivo)
        self.assertIn("mock", motivo.lower())

    def test_rechaza_si_el_juez_pidio_web_y_no_se_uso(self):
        motivo = rechazo_heuristico(
            pregunta="quién ganó el mundial",
            respuesta="Argentina en 2022",
            usar_web=True,
            hubo_buscar_web=False,
        )
        self.assertEqual(motivo, "el juez pidió buscar_web y no se usó")

    def test_rechaza_temperatura_sin_numero(self):
        motivo = rechazo_heuristico(
            pregunta="temperatura exacta en Barcelona",
            respuesta="Hace buen tiempo y está soleado.",
            usar_web=True,
            hubo_buscar_web=True,
        )
        self.assertEqual(motivo, "falta el número")

    def test_acepta_temperatura_con_numero(self):
        motivo = rechazo_heuristico(
            pregunta="temperatura exacta en Barcelona",
            respuesta="Ahora hay 24 °C y cielo despejado.",
            usar_web=True,
            hubo_buscar_web=True,
        )
        self.assertIsNone(motivo)

    def test_parsea_ok(self):
        v = parsear_veredicto("ok: si\nmotivo: incluye la temperatura")
        self.assertTrue(v.ok)
        self.assertIn("temperatura", v.motivo)

    def test_parsea_no(self):
        v = parsear_veredicto("ok: no\nmotivo: falta el número")
        self.assertFalse(v.ok)
        self.assertEqual(v.motivo, "falta el número")

    def test_consigna_trata_tools_como_fuente_de_verdad(self):
        texto = consigna_validador()
        self.assertIn("fuente de verdad", texto)
        self.assertIn("No uses tu conocimiento previo", texto)

    def test_nodo_validador_recibe_la_evidencia_web(self):
        modulo = importlib.import_module("lessons.04_chatbot")
        mensajes = [
            HumanMessage("¿Quién ganó el Mundial de 2026?"),
            ToolMessage(
                content="España ganó la final del Mundial de 2026 por 1-0.",
                name="buscar_web",
                tool_call_id="web-1",
            ),
        ]
        with patch.object(modulo, "model") as modelo:
            modelo.invoke.return_value = AIMessage(
                "ok: si\nmotivo: coincide con buscar_web"
            )
            resultado = modulo.validador(
                {
                    "messages": mensajes,
                    "usar_web": True,
                    "intentos": 0,
                    "draft": "España ganó el Mundial de 2026 por 1-0.",
                }
            )

        prompt = modelo.invoke.call_args.args[0]
        self.assertIn(
            "España ganó la final del Mundial de 2026 por 1-0.",
            prompt[1].content,
        )
        self.assertIn("España ganó el Mundial de 2026 por 1-0.", prompt[1].content)
        self.assertTrue(resultado["ok"])

    def test_chatbot_guarda_borrador_sin_publicarlo(self):
        modulo = importlib.import_module("lessons.04_chatbot")

        class ModeloFalso:
            def stream(self, _mensajes):
                yield AIMessageChunk(content="Respuesta todavía no aprobada.")

        with patch.object(modulo, "model_with_tools", ModeloFalso()):
            resultado = modulo.chatbot(
                {"messages": [HumanMessage("Pregunta de prueba")]}
            )

        self.assertEqual(resultado["draft"], "Respuesta todavía no aprobada.")
        self.assertNotIn("messages", resultado)

    def test_publicar_respuesta_solo_emite_el_borrador_aprobado(self):
        modulo = importlib.import_module("lessons.04_chatbot")
        resultado = modulo.publicar_respuesta(
            {
                "messages": [HumanMessage("Pregunta de prueba")],
                "draft": "Respuesta aprobada.",
            }
        )
        self.assertEqual(len(resultado["messages"]), 1)
        self.assertIsInstance(resultado["messages"][0], AIMessage)
        self.assertEqual(resultado["messages"][0].content, "Respuesta aprobada.")

    def test_validador_ok_ruta_a_publicar(self):
        modulo = importlib.import_module("lessons.04_chatbot")
        self.assertEqual(
            modulo._despues_validador({"ok": True, "intentos": 0}),
            "publicar",
        )

    def test_un_reintento_y_luego_cierra(self):
        self.assertTrue(debe_reintentar(False, 1))
        self.assertFalse(debe_reintentar(False, 2))
        self.assertFalse(debe_reintentar(True, 1))
        self.assertEqual(ruta_tras_validador(False, 1), "juez")
        self.assertEqual(ruta_tras_validador(False, 2), "__end__")
        self.assertEqual(ruta_tras_validador(True, 1), "__end__")


if __name__ == "__main__":
    unittest.main()
