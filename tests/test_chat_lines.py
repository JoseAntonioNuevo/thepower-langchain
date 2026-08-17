"""Tests del parser de turnos. Sin terminal ni OpenRouter."""

import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.append(str(_ROOT))

# Mensajes reales de LangChain: el parser no debe depender de la TUI.
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, ToolMessage

from ui.chat_lines import estado_de_update, lineas_de_update, lineas_del_turno


def _pares(lineas):
    """Compara solo (kind, text): el key autoincremental cambia entre tests."""
    return [(l.kind, l.text) for l in lineas]


class TestLineasDelTurno(unittest.TestCase):
    def test_turno_con_tools_y_respuesta(self):
        # Historial de dos turnos: el parser debe quedarse solo con el último.
        mensajes = [
            HumanMessage("hola"),
            AIMessage("hola, ¿qué tal?"),
            HumanMessage("¿Qué ropa me pongo hoy en Madrid?"),
            # El modelo "piensa", pide una tool y aún no escribe texto.
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "buscar_clima",
                        "args": {"ciudad": "Madrid"},
                        "id": "1",
                    }
                ],
                additional_kwargs={"reasoning": "miro el clima"},
            ),
            # ToolNode devuelve el mock de 04_chatbot.py.
            ToolMessage(
                content="Soleado en Madrid",
                name="buscar_clima",
                tool_call_id="1",
            ),
            AIMessage("Hoy hace sol; chaqueta ligera."),
        ]
        # Orden de clase: pensar → tool pedida → dato → respuesta del bot.
        self.assertEqual(
            _pares(lineas_del_turno(mensajes)),
            [
                ("thinking", "miro el clima"),
                ("tool", "buscar_clima(ciudad='Madrid')"),
                ("dato", "buscar_clima: Soleado en Madrid"),
                ("bot", "Hoy hace sol; chaqueta ligera."),
            ],
        )

    def test_no_incluye_turnos_anteriores(self):
        # Tras el segundo human, solo debe quedar la última respuesta.
        mensajes = [
            HumanMessage("me llamo Alex"),
            AIMessage("Hola Alex"),
            HumanMessage("¿cómo me llamo?"),
            AIMessage("Alex"),
        ]
        self.assertEqual(_pares(lineas_del_turno(mensajes)), [("bot", "Alex")])

    def test_update_de_nodo(self):
        # Un chunk de stream_mode="updates" cuando acaba el nodo tools.
        update = {
            "tools": {
                "messages": [
                    ToolMessage(
                        content="Soleado en Madrid",
                        name="buscar_clima",
                        tool_call_id="1",
                    )
                ]
            }
        }
        self.assertEqual(
            _pares(lineas_de_update(update)),
            [("dato", "buscar_clima: Soleado en Madrid")],
        )
        # El sidebar usa esto para pintar el nodo y el nombre de la tool.
        self.assertEqual(estado_de_update(update), ("tools", ["buscar_clima"]))

    def test_estado_llm_pide_tools(self):
        # El nodo chatbot acaba: el LLM pidió dos tools a la vez.
        update = {
            "chatbot": {
                "messages": [
                    AIMessage(
                        content="",
                        tool_calls=[
                            {
                                "name": "buscar_clima",
                                "args": {"ciudad": "Madrid"},
                                "id": "1",
                            },
                            {
                                "name": "tendencia_ropa",
                                "args": {"ciudad": "Madrid"},
                                "id": "2",
                            },
                        ],
                    )
                ]
            }
        }
        # nodo=chatbot (el chunk es del LLM) + los dos nombres, en orden.
        self.assertEqual(
            estado_de_update(update),
            ("chatbot", ["buscar_clima", "tendencia_ropa"]),
        )

    def test_estado_llm_solo_texto(self):
        # Respuesta final sin tools: el sidebar vuelve a LLM y lista vacía.
        update = {"chatbot": {"messages": [AIMessage("Hoy chaquetita")]}}
        self.assertEqual(estado_de_update(update), ("chatbot", []))

    def test_update_de_chatbot_con_ai_message_chunk_muestra_respuesta(self):
        # stream() devuelve AIMessageChunk en el update final, no AIMessage.
        update = {
            "chatbot": {
                "messages": [AIMessageChunk(content="La respuesta final es París.")]
            }
        }
        self.assertEqual(
            _pares(lineas_de_update(update)),
            [("bot", "La respuesta final es París.")],
        )

    def test_update_del_juez(self):
        update = {
            "juez": {
                "usar_web": True,
                "query_web": "temperatura actual Barcelona",
                "motivo_juez": "pide un número",
                "ok": False,
            }
        }
        self.assertEqual(
            _pares(lineas_de_update(update)),
            [("juez", "web · temperatura actual Barcelona")],
        )
        self.assertEqual(estado_de_update(update), ("juez", []))

    def test_update_del_validador(self):
        update = {
            "validador": {
                "ok": False,
                "motivo_validador": "falta el número",
                "intentos": 1,
            }
        }
        self.assertEqual(
            _pares(lineas_de_update(update)),
            [("validador", "reintenta · falta el número")],
        )
        self.assertEqual(estado_de_update(update), ("validador", []))

    def test_respuesta_publicada_aparece_despues_del_ok(self):
        updates = [
            {
                "validador": {
                    "ok": True,
                    "motivo_validador": "respaldada por las tools",
                    "intentos": 0,
                }
            },
            {"publicar": {"messages": [AIMessage("Respuesta aprobada.")]}}
        ]
        lineas = [linea for update in updates for linea in lineas_de_update(update)]
        self.assertEqual(
            _pares(lineas),
            [
                ("validador", "ok · respaldada por las tools"),
                ("bot", "Respuesta aprobada."),
            ],
        )
