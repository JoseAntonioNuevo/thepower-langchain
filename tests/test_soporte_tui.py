"""Pruebas sin red del soporte interactivo: teclado, rutas y una ejecución por turno."""

import asyncio
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from langchain_core.messages import AIMessage
from opentui import test_render
from test_soporte import FakeModel, call
from app.soporte.config import Settings
from app.soporte.runner import run_turn
from app.soporte.telemetry import Telemetry
from ui.soporte_tui import SupportController


class SupportTuiTests(unittest.TestCase):
    def test_stream_observer_runs_once_and_keeps_session_history(self):
        from langgraph.checkpoint.memory import InMemorySaver

        model = FakeModel(responses=[AIMessage(content="Hola Alex"), AIMessage(content="Alex")])
        updates = []
        common = dict(model=model, cfg=Settings("fake", "unused"),
                      telemetry=Telemetry.open("off"), thread_id="A", db=None,
                      memory_saver=InMemorySaver(), use_tools=False, on_update=updates.append)
        first = run_turn(question="Me llamo Alex", **common)
        second = run_turn(question="¿Cómo me llamo?", **common)
        self.assertEqual(len(model.seen), 2)
        self.assertIn("Me llamo Alex", str(model.seen[1]))
        self.assertEqual(first["model_calls"], 1)
        self.assertEqual(second["answer"], "Alex")
        self.assertTrue(any("inicio" in u for u in updates))
        self.assertTrue(any("chatbot" in u for u in updates))

    def test_keyboard_tools_and_visual_panel(self):
        async def exercise():
            with tempfile.TemporaryDirectory() as d:
                model = FakeModel(responses=[AIMessage(content="", tool_calls=[call()]),
                                             AIMessage(content="T-100 está en curso")])
                args = SimpleNamespace(hilo="tui-test", db=Path(d)/"memory.sqlite",
                    version="v2", prompts="local", escenario="normal", salida=Path(d)/"last.json")
                controller = SupportController(model=model, cfg=Settings("fake", "unused"),
                    telemetry=Telemetry.open("off"), args=args, use_tools=True, memory=True)
                setup = await test_render(controller.app, {"width":110, "height":38})
                try:
                    setup.stdin_input.type_text("Consulta T-100")
                    setup.stdin_input.press_enter()
                    controller._worker.join(timeout=5)
                    self.assertFalse(controller._worker.is_alive())
                    controller.drain()
                    frame = setup.capture_char_frame()
                    for expected in ("Agente de soporte", "SQLite", "T-100", "en curso", "tools"):
                        self.assertIn(expected, frame)
                    self.assertNotIn("juez", frame)
                    self.assertNotIn("validador", frame)
                    self.assertEqual(len(model.seen), 2)
                    self.assertEqual(controller.count(), 1)
                    self.assertTrue(args.salida.exists())
                    self.assertEqual(len(list((Path(d)/"last-turnos").glob("*.json"))), 1)
                    Path("/tmp/thepower-support-tui-frame.txt").write_text(frame)
                finally:
                    setup.destroy()
        asyncio.run(exercise())


if __name__ == "__main__":
    unittest.main()
