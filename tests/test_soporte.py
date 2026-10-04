"""Pruebas locales del agente de soporte y de sus contratos de S5 y S6.

FakeModel entrega respuestas preparadas y registra los mensajes que recibió,
permitiendo forzar rutas y errores sin consumir APIs. call construye solicitudes
de herramientas e invoke ejecuta un turno de prueba. SoporteTests comprueba
respuestas, herramientas, límites, memoria, prompts y filtrado. ExperimentTests
comprueba la comparación y la configuración con servicios simulados;
PrivacySerializationTests comprueba el filtrado de mensajes serializados.
La persistencia se prueba con una SQLite temporal y un proceso separado.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field
from app.soporte.graph import build_graph, prompt_template
from app.soporte.tools import make_tools
from app.soporte.persistence import sqlite_memory
from app.soporte.privacy import redact
from app.soporte.config import settings


class FakeModel(BaseChatModel):
    responses: list = Field(default_factory=list)
    seen: list = Field(default_factory=list)

    # Identifica el modelo simulado ante LangChain.
    @property
    def _llm_type(self):
        return "scripted-test"

    # Acepta tools sin conexión; las respuestas están preparadas.
    def bind_tools(self, tools, **kwargs):
        return self

    # Registra mensajes y consume la siguiente respuesta o excepción simulada.
    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.seen.append(messages)
        msg = (
            self.responses.pop(0)
            if self.responses
            else AIMessage(content="Respuesta de prueba")
        )
        if isinstance(msg, Exception):
            raise msg
        return ChatResult(generations=[ChatGeneration(message=msg)])


# Construye una solicitud de tool con nombre, argumentos e ID.
def call(name="consultar_ticket", args=None, id="1"):
    return {
        "name": name,
        "args": args if args is not None else {"ticket_id": "T-100"},
        "id": id,
        "type": "tool_call",
    }


# Ejecuta un turno en un hilo conocido con dependencias inyectadas.
def invoke(model, **kwargs):
    graph = build_graph(model, **kwargs)
    return graph.invoke(
        {"messages": [HumanMessage("Consulta T-100")]},
        {"configurable": {"thread_id": "uno"}},
    )


class SoporteTests(unittest.TestCase):
    # Comprueba que una respuesta directa termina sin herramientas.
    def test_direct_response(self):
        r = invoke(FakeModel(responses=[AIMessage(content="Hola")]))
        self.assertEqual(r["tool_count"], 0)
        self.assertEqual(r["status"], "done")

    # Comprueba las dos tools y sus resultados como ToolMessage.
    def test_both_tools_and_returns(self):
        m = FakeModel(
            responses=[
                AIMessage(
                    content="",
                    tool_calls=[
                        call(),
                        call("buscar_articulo", {"articulo_id": "A-10"}, "2"),
                    ],
                ),
                AIMessage(content="Ayuda"),
            ]
        )
        r = invoke(m)
        self.assertEqual(r["tool_count"], 2)
        self.assertEqual([c["ok"] for c in r["calls"]], [True, True])
        self.assertEqual(len([x for x in m.seen[-1] if isinstance(x, ToolMessage)]), 2)

    # Argumento inválido, recurso ausente y fallo consumen un intento.
    def test_invalid_unknown_and_failure_count(self):
        for args, scenario in [
            ({"ticket_id": "bad"}, "normal"),
            ({"ticket_id": "T-999"}, "normal"),
            ({"ticket_id": "T-100"}, "fallo"),
        ]:
            with self.subTest(args=args, scenario=scenario):
                r = invoke(
                    FakeModel(
                        responses=[
                            AIMessage(content="", tool_calls=[call(args=args)]),
                            AIMessage(content="No disponible"),
                        ]
                    ),
                    tools=make_tools(scenario=scenario),
                )
                self.assertEqual(r["tool_count"], 1)
                self.assertTrue(r["errors"])
                self.assertFalse(r["calls"][0]["ok"])

    # Solicita tres tools: ejecuta dos y responde también a la rechazada.
    def test_parallel_third_is_blocked(self):
        r = invoke(
            FakeModel(
                responses=[
                    AIMessage(
                        content="", tool_calls=[call(id=str(i)) for i in range(3)]
                    ),
                    AIMessage(content="Fin"),
                ]
            )
        )
        self.assertEqual(r["tool_count"], 2)
        self.assertEqual([c["executed"] for c in r["calls"]], [True, True, False])
        self.assertEqual(
            len([x for x in r["messages"] if isinstance(x, ToolMessage)]), 3
        )

    # Fuerza tools en la respuesta final y comprueba que no se ejecutan.
    def test_final_model_cannot_execute_more_tools(self):
        r = invoke(
            FakeModel(
                responses=[
                    AIMessage(content="", tool_calls=[call(id="1"), call(id="2")]),
                    AIMessage(content="", tool_calls=[call(id="3")]),
                ]
            )
        )
        self.assertEqual(r["status"], "limit")
        self.assertEqual(r["tool_count"], 2)
        self.assertEqual(
            len([x for x in r["messages"] if isinstance(x, ToolMessage)]), 3
        )

    # Simula un fallo del modelo sin exponer su mensaje privado.
    def test_model_failure_controlled(self):
        r = invoke(FakeModel(responses=[RuntimeError("private-provider-response")]))
        self.assertEqual(r["status"], "model_error")
        self.assertNotIn("private-provider", str(r))

    # Comprueba contador reiniciado en A e historial independiente en B.
    def test_counters_reset_and_threads_isolated(self):
        from langgraph.checkpoint.memory import InMemorySaver

        m = FakeModel(
            responses=[
                AIMessage(content="", tool_calls=[call()]),
                AIMessage(content="T-100"),
                AIMessage(content="Hola"),
                AIMessage(content="Otro"),
            ]
        )
        from langchain_core.runnables import RunnableConfig

        g = build_graph(m, checkpointer=InMemorySaver())
        cfg: RunnableConfig = {"configurable": {"thread_id": "A"}}
        g.invoke({"messages": [HumanMessage("T-100")]}, cfg)
        r = g.invoke({"messages": [HumanMessage("Hola")]}, cfg)
        self.assertEqual(r["tool_count"], 0)
        self.assertEqual(r["errors"], [])
        g.invoke(
            {"messages": [HumanMessage("Otro")]}, {"configurable": {"thread_id": "B"}}
        )
        self.assertNotIn("T-100", str(m.seen[-1]))

    # Escribe desde otro proceso y recupera el estado desde SQLite.
    def test_sqlite_persists_across_processes(self):
        with tempfile.TemporaryDirectory() as d:
            db = str(Path(d) / "memory.sqlite")
            code = """import sys\nfrom tests.test_soporte import FakeModel\nfrom app.soporte.persistence import sqlite_memory\nfrom app.soporte.graph import build_graph\nfrom langchain_core.messages import HumanMessage\nwith sqlite_memory(sys.argv[1]) as saver:\n g=build_graph(FakeModel(),checkpointer=saver)\n g.invoke({'messages':[HumanMessage('identificador-de-prueba')]},{'configurable':{'thread_id':'persistente'}})\n"""
            # tests no es package: añadir el directorio explícitamente en el subprocess.
            code = code.replace(
                "from tests.test_soporte import",
                'sys.path.insert(0,"tests")\nfrom test_soporte import',
            )
            subprocess.run(
                [sys.executable, "-c", code, db], check=True, capture_output=True
            )
            with sqlite_memory(db) as saver:
                g = build_graph(FakeModel(), checkpointer=saver)
                state = g.get_state({"configurable": {"thread_id": "persistente"}})
                self.assertIn("identificador-de-prueba", str(state.values["messages"]))
                self.assertFalse(
                    g.get_state({"configurable": {"thread_id": "otro"}}).values
                )

    # Comprueba el SystemMessage que recibe el modelo.
    def test_prompt_really_used(self):
        m = FakeModel()
        invoke(m, prompt=prompt_template("INSTRUCCION_DISTINTA"))
        self.assertEqual(m.seen[0][0].content, "INSTRUCCION_DISTINTA")

    # Filtra estructuras anidadas sin cambiar el original ni los tokens.
    def test_filter_recurses_without_mutating(self):
        original = {
            "input": {"messages": ["correo aula@example.test SECRET_DEMO_123"]},
            "api_key": "synthetic",
            "input_tokens": 12,
        }
        filtered = redact(original)
        self.assertIn("aula@example.test", str(original))
        self.assertNotIn("aula@example.test", str(filtered))
        self.assertNotIn("SECRET_DEMO_123", str(filtered))
        self.assertEqual(filtered["input_tokens"], 12)

    # Comprueba la prioridad de MODEL_ID sobre OPENROUTER_MODEL.
    def test_config_precedence(self):
        with patch.dict(
            os.environ, {"MODEL_ID": "model-first", "OPENROUTER_MODEL": "model-second"}
        ):
            self.assertEqual(settings().model_id, "model-first")

    # Comprueba off sin trazas y métricas desconocidas en None.
    def test_off_does_not_export_and_missing_metrics_are_null(self):
        from app.soporte.runner import run_turn
        from app.soporte.telemetry import Telemetry
        from app.soporte.config import Settings

        with tempfile.TemporaryDirectory() as d:
            t = Telemetry.open("off")
            r = run_turn(
                model=FakeModel(),
                cfg=Settings("fake", "unused"),
                telemetry=t,
                question="Hola",
                thread_id="x",
                db=Path(d) / "x.db",
            )
            self.assertIsNone(r["cost_usd"])
            self.assertIsNone(r["total_tokens"])
            self.assertIsNone(r["langsmith_run_id"])
            self.assertIsNone(r["langfuse_trace_id"])
            t.close()

    # Comprueba el vaciado de las colas incluso con una excepción.
    def test_flush_even_when_turn_raises(self):
        from app.soporte.telemetry import Telemetry
        from unittest.mock import Mock

        t = Telemetry("off")
        t.flush = Mock()
        with self.assertRaises(RuntimeError):
            with t.turn(
                thread_id="x", model_id="fake", prompt_meta={}, scenario="normal"
            ):
                raise RuntimeError()
        t.flush.assert_called_once()

    # Comprueba el filtrado de atributos antes de exportar spans.
    def test_mask_exported_spans(self):
        from types import SimpleNamespace
        from app.soporte.privacy import mask_spans

        params = SimpleNamespace(
            spans={
                "x": SimpleNamespace(
                    attributes={
                        "input": "aula@example.test SECRET_DEMO_abc",
                        "duration": 2,
                    }
                )
            }
        )
        r = mask_spans(params=params)
        self.assertNotIn("aula@example.test", str(r))
        self.assertNotIn("SECRET_DEMO_abc", str(r))


if __name__ == "__main__":
    unittest.main()


class ExperimentTests(unittest.TestCase):
    # Comprueba diez casos por versión y veinte hilos independientes.
    def test_comparison_has_twenty_clean_threads(self):
        from app.soporte.evaluation import comparison_rows
        from app.soporte.config import ROOT

        cases = json.loads((ROOT / "datos/soporte/evaluacion.json").read_text())
        rows = list(comparison_rows(cases))
        self.assertEqual(len(rows), 20)
        self.assertEqual(len({r[2] for r in rows}), 20)
        self.assertEqual([r[1] for r in rows[:10]], [r[1] for r in rows[10:]])

    # Comprueba timeout y reintentos del cliente sin enviar consultas.
    def test_timeout_milliseconds_and_sdk_retries_disabled(self):
        from app.soporte.config import make_model, Settings

        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "synthetic-test-only"}):
            m = make_model(Settings("fake", "https://example.test"))
        self.assertEqual(m.request_timeout, 45000)
        self.assertIsNone(m.client.sdk_configuration.retry_config)

    # Simula los gestores, aplica el texto y rechaza versiones distintas.
    def test_remote_prompt_hash_and_application(self):
        from unittest.mock import Mock
        from types import SimpleNamespace
        from app.soporte.prompts import resolve_prompt, sha
        from app.soporte.graph import local_prompt

        text = local_prompt("v2")
        manifest = {
            "name": "test",
            "versions": {
                "v2": {
                    "sha256": sha(text),
                    "langsmith_commit": "abc",
                    "langfuse_version": 2,
                }
            },
        }
        t = SimpleNamespace(ls=Mock(), lf=Mock())
        t.ls.pull_prompt.return_value = prompt_template(text)
        t.lf.get_prompt.return_value = SimpleNamespace(prompt=text)
        with patch("app.soporte.prompts.MANIFEST") as path:
            path.read_text.return_value = json.dumps(manifest)
            p, meta = resolve_prompt("v2", "remote", t)
            self.assertEqual(p.invoke({"messages": []}).to_messages()[0].content, text)
            self.assertEqual(meta["prompt_source"], "remote")
            t.lf.get_prompt.return_value = SimpleNamespace(prompt="DISTINTO")
            with self.assertRaises(ValueError):
                resolve_prompt("v2", "remote", t)


class PrivacySerializationTests(unittest.TestCase):
    # Filtra al serializar sin modificar el mensaje Pydantic original.
    def test_pydantic_messages_are_filtered_before_serialization(self):
        message = HumanMessage("aula@example.test SECRET_DEMO_123")
        original = {"messages": [message]}
        filtered = redact(original)
        self.assertNotIn("aula@example.test", json.dumps(filtered))
        self.assertNotIn("SECRET_DEMO_123", json.dumps(filtered))
        self.assertEqual(message.content, "aula@example.test SECRET_DEMO_123")
