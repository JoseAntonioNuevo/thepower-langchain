"""Smoke de layout OpenTUI. Sin OpenRouter."""

import asyncio
import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.append(str(_ROOT))

# Signal: estado reactivo. test_render: pinta la app en un buffer sin TTY real.
from opentui import KeyEvent, Signal, test_render

from ui.chat_lines import ChatLine
from langchain_core.messages import AIMessage, AIMessageChunk

from ui.chat_tui import (
    GrafoEstado,
    _color_espina,
    _cuerpo_juez,
    _cuerpo_llm,
    _cuerpo_tools,
    _cuerpo_validador,
    _frame_spinner,
    _leyenda,
    _mostrar_cursor_textarea,
    _nombre_amigable,
    _nombre_modelo,
    _posicion_cursor_en_textarea,
    _vista_dato,
    aplicar_evento,
    build_app,
)


def _app(**extra):
    """Monta la TUI con signals por defecto; extra pisa lo que el test quiera fijar."""
    defaults = dict(
        modelo="openai/gpt-6-luna",
        thread_id="usuario_123",
        lines=Signal([], name="lines"),
        busy=Signal(False, name="busy"),
        active_node=Signal(None, name="active_node"),
        active_tools=Signal([], name="active_tools"),
        status=Signal("listo", name="status"),
        draft=Signal("", name="draft"),
        on_submit=lambda _t: None,
        on_quit=lambda: None,
        grafo_opacity=Signal(1.0, name="grafo_opacity"),
    )
    defaults.update(extra)
    return build_app(**defaults)


class TestChatTuiLayout(unittest.TestCase):
    def test_layout_muestra_header_sidebar_y_lineas(self):
        # El frame de caracteres debe contener cabecera, grafo, chat y composer.
        frame = asyncio.run(self._capture())
        for trozo in (
            "LangGraph",
            "gpt-6-luna",
            "usuario_123",
            "LLM",
            "Luna",
            "tools",
            "START",
            "END",
            "juez",
            "validador",
            "pide tool",
            "vuelve",
            "reintenta",
            "clima",
            "┃",
            "▲",
            "▼",
            "ok",
            "Madrid",
            "tú",
            "pensar",
            "tool",
            "dato",
            "bot",
            "Escribe",
            "mensaje",
            "buscar_clima",
            "enter envía",
            "turno 0",
        ):
            self.assertIn(trozo, frame, f"falta {trozo!r} en:\n{frame}")

    def test_se_puede_escribir_y_enviar(self):
        # El composer real recibe el foco y mantiene el Signal draft como espejo.
        draft = Signal("", name="draft")
        enviados: list[str] = []

        async def _run() -> None:
            setup = await test_render(
                lambda: _app(draft=draft, on_submit=enviados.append),
                {"width": 80, "height": 24},
            )
            try:
                # Teclear actualiza el draft y se ve en el composer.
                setup.stdin_input.type_text("hola madrid")
                self.assertEqual(draft(), "hola madrid")
                frame = setup.capture_char_frame()
                self.assertIn("hola madrid", frame)
                # Enter llama on_submit con ese texto (no hace falta OpenRouter).
                setup.stdin_input.press_enter()
                self.assertEqual(enviados, ["hola madrid"])
            finally:
                setup.destroy()

        asyncio.run(_run())

    def test_pipeline_real_no_duplica_una_tecla(self):
        async def _run() -> None:
            setup = await test_render(
                lambda: _app(),
                {"width": 80, "height": 24},
            )
            try:
                # stdin_input atraviesa el mismo dispatcher que la terminal;
                # mock_input solo invoca los hooks directamente.
                setup.stdin_input.type_text("x")
                lineas_composer = [
                    linea for linea in setup.capture_char_frame().splitlines() if "│  " in linea
                ]
                self.assertTrue(any("│  x" in linea for linea in lineas_composer))
                self.assertFalse(any("│  xx" in linea for linea in lineas_composer))
            finally:
                setup.destroy()

        asyncio.run(_run())

    def test_pipeline_ignora_la_liberacion_de_una_tecla(self):
        async def _run() -> None:
            setup = await test_render(
                lambda: _app(),
                {"width": 80, "height": 24},
            )
            try:
                handlers = setup.renderer._get_event_forwarding()["key"]
                for event_type in ("press", "release"):
                    event = KeyEvent(key="y", sequence="y", event_type=event_type)
                    for handler in handlers:
                        handler(event)
                lineas_composer = [
                    linea for linea in setup.capture_char_frame().splitlines() if "│  " in linea
                ]
                self.assertTrue(any("│  y" in linea for linea in lineas_composer))
                self.assertFalse(any("│  yy" in linea for linea in lineas_composer))
            finally:
                setup.destroy()

        asyncio.run(_run())

    def test_shift_enter_inserta_linea_y_enter_envia(self):
        enviados: list[str] = []

        async def _run() -> None:
            setup = await test_render(
                lambda: _app(on_submit=enviados.append),
                {"width": 80, "height": 24},
            )
            try:
                setup.stdin_input.type_text("primera")
                event = KeyEvent(key="return", shift=True)
                for handler in setup.renderer._get_event_forwarding()["key"]:
                    handler(event)
                setup.stdin_input.type_text("segunda")
                self.assertEqual(enviados, [])
                setup.stdin_input.press_enter()
                self.assertEqual(enviados, ["primera\nsegunda"])
            finally:
                setup.destroy()

        asyncio.run(_run())

    def test_pegar_texto_multilinea_llega_al_composer(self):
        async def _run() -> None:
            setup = await test_render(
                lambda: _app(),
                {"width": 80, "height": 24},
            )
            try:
                setup.mock_input.paste_bracketed_text("línea uno\nlínea dos")
                frame = setup.capture_char_frame()
                self.assertIn("línea uno", frame)
                self.assertIn("línea dos", frame)
            finally:
                setup.destroy()

        asyncio.run(_run())

    def test_flechas_recuperan_historial_desde_composer_vacio(self):
        enviados: list[str] = []

        async def _run() -> None:
            setup = await test_render(
                lambda: _app(on_submit=enviados.append),
                {"width": 80, "height": 24},
            )
            try:
                setup.stdin_input.type_text("primero")
                setup.stdin_input.press_enter()
                setup.stdin_input.press_arrow("up")
                frame = setup.capture_char_frame()
                self.assertIn("primero", frame)
                setup.stdin_input.press_arrow("down")
                self.assertIn("Escribe", setup.capture_char_frame())
            finally:
                setup.destroy()

        asyncio.run(_run())

    def test_flechas_desde_borrador_restauran_el_borrador(self):
        async def _run() -> None:
            setup = await test_render(
                lambda: _app(),
                {"width": 80, "height": 24},
            )
            try:
                setup.stdin_input.type_text("primero")
                setup.stdin_input.press_enter()
                setup.stdin_input.type_text("borrador")
                setup.stdin_input.press_arrow("up")
                self.assertIn("primero", setup.capture_char_frame())
                setup.stdin_input.press_arrow("down")
                self.assertIn("borrador", setup.capture_char_frame())
            finally:
                setup.destroy()

        asyncio.run(_run())

    def test_editar_mensaje_recuperado_escribe_al_final(self):
        enviados: list[str] = []

        async def _run() -> None:
            setup = await test_render(
                lambda: _app(on_submit=enviados.append),
                {"width": 80, "height": 24},
            )
            try:
                setup.stdin_input.type_text("primero")
                setup.stdin_input.press_enter()
                setup.stdin_input.press_arrow("up")
                setup.stdin_input.type_text("!")
                setup.stdin_input.press_enter()
                self.assertEqual(enviados, ["primero", "primero!"])
            finally:
                setup.destroy()

        asyncio.run(_run())

    def test_escape_cierra_el_tui_desde_el_composer(self):
        salidas: list[bool] = []

        async def _run() -> None:
            setup = await test_render(
                lambda: _app(on_quit=lambda: salidas.append(True)),
                {"width": 80, "height": 24},
            )
            try:
                setup.stdin_input.press_escape()
                self.assertEqual(salidas, [True])
            finally:
                setup.destroy()

        asyncio.run(_run())

    def test_composer_busy_no_envia(self):
        enviados: list[str] = []

        async def _run() -> None:
            setup = await test_render(
                lambda: _app(
                    busy=Signal(True, name="busy"),
                    on_submit=enviados.append,
                ),
                {"width": 80, "height": 24},
            )
            try:
                self.assertIn("trabajando", setup.capture_char_frame())
                setup.stdin_input.type_text("no mandar")
                setup.stdin_input.press_enter()
                self.assertEqual(enviados, [])
                frame = setup.capture_char_frame()
                self.assertIn("no mandar", frame)
            finally:
                setup.destroy()

        asyncio.run(_run())

    def test_globo_bot_renderiza_markdown(self):
        # El LLM suele devolver MD: en el globo no deben verse los marcadores.
        frame = asyncio.run(self._capture_md())
        self.assertIn("Madrid", frame)
        self.assertIn("hace sol", frame)
        self.assertIn("chaqueta ligera", frame)
        self.assertNotIn("**", frame)
        self.assertNotIn("# Madrid", frame)
        self.assertNotIn("`tendencia_ropa`", frame)
        self.assertIn("tendencia_ropa", frame)

    def test_globo_bot_envuelve_respuesta_larga(self):
        # Una frase más ancha que max_width=50 no puede recortarse a "vencer a A".
        texto = (
            "España ganó el Mundial de 2026 tras vencer a Argentina "
            "en la final de Nueva York."
        )
        frame = asyncio.run(self._capture_bot(texto, width=80, height=22))
        self.assertIn("España", frame)
        self.assertIn("Argentina", frame)
        self.assertIn("Nueva York", frame)
        self.assertIn("mensaje", frame)
        self.assertIn("Escribe", frame)
        # El composer sigue en pantalla: el globo no se come el borde inferior.
        lineas = frame.splitlines()
        self.assertTrue(
            any("mensaje" in linea or "Escribe" in linea for linea in lineas[-6:]),
            f"composer fuera de vista:\n{frame}",
        )

    def test_posicion_cursor_fallback_y_visual(self):
        class _SinVista:
            plain_text = "hola"
            cursor_offset = 4
            _editor_view = None

        self.assertEqual(_posicion_cursor_en_textarea(_SinVista()), (4, 0))

        class _Vista:
            visual_col = 3
            visual_row = 1

        class _ConVista:
            _editor_view = type("V", (), {"get_visual_cursor": staticmethod(lambda: _Vista())})()

        self.assertEqual(_posicion_cursor_en_textarea(_ConVista()), (3, 1))

    def test_cursor_apagado_si_no_hay_foco(self):
        class _TA:
            _focused = False
            _x = 2
            _y = 3
            _layout_width = 20
            _layout_height = 2
            plain_text = ""
            cursor_offset = 0
            _editor_view = None

        # No debe lanzar: sin foco no pide caret al terminal.
        _mostrar_cursor_textarea(_TA(), encendido=True)
        _TA._focused = True
        _mostrar_cursor_textarea(_TA(), encendido=False)

    def test_leyenda_del_grafo(self):
        # Chip: fase del turno + etiqueta amigable, no el id crudo.
        self.assertEqual(_leyenda("judging", []), "el juez decide")
        self.assertEqual(_leyenda("retrying", []), "reintenta")
        self.assertEqual(_leyenda("thinking", []), "en el modelo")
        self.assertEqual(_leyenda("tools", ["buscar_clima"]), "pide tool · clima")
        self.assertEqual(
            _leyenda("tools", ["buscar_clima", "buscar_web"]),
            "pide tool · 2",
        )
        self.assertEqual(_leyenda("writing", []), "el modelo responde")
        self.assertEqual(_leyenda("validating", []), "valida respuesta")
        self.assertEqual(_leyenda("idle", []), "reposo")
        self.assertEqual(_leyenda(None, []), "reposo")

    def test_nombre_modelo_corto(self):
        self.assertEqual(_nombre_modelo("google/gemma-4-31b-it"), "Gemma 4 31B")
        self.assertEqual(_nombre_modelo("gemma-4-31b-it"), "Gemma 4 31B")
        self.assertEqual(_nombre_modelo("openai/gpt-6-luna"), "Gpt 6 Luna")

    def test_spinner_y_espina(self):
        self.assertEqual(_frame_spinner(0), "⠋")
        self.assertIn(_frame_spinner(3), "⠋⠙⠹⠸⠼⠴⠦⠧")
        self.assertEqual(_color_espina(False, 0.9, "#9d7cd8"), "#a9b1d6")
        self.assertEqual(_color_espina(True, 0.8, "#9d7cd8"), "#9d7cd8")
        self.assertEqual(_color_espina(True, 0.2, "#9d7cd8"), "#1a1b26")

    def test_cuerpos_con_detalle(self):
        self.assertIn("generando", _cuerpo_llm("thinking", "Gemma 4 31B", detalle="hola"))
        self.assertIn("hola", _cuerpo_llm("thinking", "Gemma 4 31B", detalle="hola"))
        self.assertIn("clima · Madrid", _cuerpo_tools([], detalle=["clima · Madrid"], aqui=True))
        self.assertIn("aquí", _cuerpo_tools(["buscar_clima"], aqui=True, spinner="⠋"))
        self.assertIn("decide", _cuerpo_juez("judging", detalle="web · BCN"))
        self.assertIn("¿buscar web?", _cuerpo_juez("idle"))
        self.assertIn("valida", _cuerpo_validador("validating", detalle="reintenta"))
        self.assertIn("¿respuesta ok?", _cuerpo_validador("idle"))

    def test_aplicar_evento_tokens_y_tools(self):
        estado = GrafoEstado()
        estado = aplicar_evento(
            estado,
            "messages",
            (AIMessageChunk(content="Hoy "), {"langgraph_node": "chatbot"}),
        )
        self.assertEqual(estado.phase, "thinking")
        self.assertIn("Hoy", estado.llm_detalle)
        estado = aplicar_evento(
            estado,
            "messages",
            (
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "buscar_clima",
                            "args": {"ciudad": "Madrid"},
                            "id": "1",
                        }
                    ],
                ),
                {"langgraph_node": "chatbot"},
            ),
        )
        self.assertEqual(estado.phase, "tools")
        self.assertEqual(estado.tools, ["buscar_clima"])
        self.assertTrue(any("clima" in d for d in estado.tool_detalle))
        estado = aplicar_evento(
            estado,
            "tasks",
            {"name": "chatbot", "id": "x", "input": {}, "triggers": ["tools"]},
        )
        self.assertEqual(estado.phase, "writing")

    def test_aplicar_evento_juez_y_validador(self):
        estado = aplicar_evento(
            GrafoEstado(),
            "tasks",
            {"name": "juez", "id": "j", "input": {}},
        )
        self.assertEqual(estado.phase, "judging")
        estado = aplicar_evento(
            estado,
            "updates",
            {
                "juez": {
                    "usar_web": True,
                    "query_web": "temperatura actual Barcelona",
                    "motivo_juez": "número",
                    "ok": False,
                }
            },
        )
        self.assertEqual(estado.phase, "judging")
        self.assertIn("Barcelona", estado.juez_detalle)
        estado = aplicar_evento(
            estado,
            "tasks",
            {"name": "validador", "id": "v", "input": {}},
        )
        self.assertEqual(estado.phase, "validating")
        self.assertTrue(estado.hubo_validacion)
        estado = aplicar_evento(
            estado,
            "updates",
            {"validador": {"ok": False, "motivo_validador": "falta el número", "intentos": 1}},
        )
        self.assertEqual(estado.validador_detalle, "reintenta · falta el número")
        estado = aplicar_evento(
            estado,
            "tasks",
            {"name": "juez", "id": "j2", "input": {}},
        )
        self.assertEqual(estado.phase, "retrying")

    def test_una_tool_no_se_lista_dos_veces(self):
        # El stream a veces manda tool_calls y tool_call_chunks en el mismo mensaje.
        chunk = AIMessage(
            content="",
            tool_calls=[
                {"name": "buscar_web", "args": {"query": "final"}, "id": "1"},
            ],
        )
        chunk.tool_call_chunks = [
            {"name": "buscar_web", "args": {"query": "final"}, "id": "1", "index": 0},
        ]
        estado = aplicar_evento(
            GrafoEstado(),
            "messages",
            (chunk, {"langgraph_node": "chatbot"}),
        )
        self.assertEqual(estado.tools, ["buscar_web"])
        self.assertEqual(len(estado.tool_detalle), 1)
        cuerpo = _cuerpo_tools(estado.tools, detalle=estado.tool_detalle, aqui=True)
        self.assertEqual(cuerpo.count("búsqueda"), 1)

    def test_nombre_amigable_de_tools(self):
        self.assertEqual(_nombre_amigable("fecha_hoy"), "fecha")
        self.assertEqual(_nombre_amigable("buscar_clima"), "clima")
        self.assertEqual(_nombre_amigable("tendencia_ropa"), "tendencia")
        self.assertEqual(_nombre_amigable("buscar_web"), "búsqueda")
        self.assertEqual(_nombre_amigable("otra_tool"), "otra_tool")

    def test_vista_dato_omite_urls_y_snippets(self):
        # El volcado de Tavily no debe llegar crudo al globo del usuario.
        nombre, cuerpo = _vista_dato(
            "buscar_web: España 2-1 Argentina. Ferran Torres marcó el 2-1.\n"
            "- FIFA — Resumen de la final\n"
            "  https://www.fifa.com/final-2026-very-long-url-path\n"
            "- YouTube — 81450 views Image 3 Final #{equipoLocal}\n"
            "  https://www.youtube.com/watch?v=xxxx\n"
        )
        self.assertEqual(nombre, "buscar_web")
        self.assertIn("Ferran Torres", cuerpo)
        self.assertIn("· FIFA", cuerpo)
        self.assertIn("· YouTube", cuerpo)
        self.assertNotIn("https://", cuerpo)
        self.assertNotIn("81450 views", cuerpo)
        self.assertNotIn("#{equipoLocal}", cuerpo)

    def test_dato_en_pantalla_no_vuelca_urls(self):
        frame = asyncio.run(self._capture_dato_sucio())
        self.assertIn("dato", frame)
        self.assertIn("buscar_web", frame)
        self.assertIn("Ferran", frame)
        self.assertIn("FIFA", frame)
        self.assertNotIn("https://www.fifa.com", frame)
        self.assertNotIn("#{equipoLocal}", frame)

    async def _capture(self) -> str:
        # Un turno de ejemplo ya pintado: hint, tú, pensar, tool, dato, bot.
        lines = Signal(
            [
                ChatLine("hint", "Prueba: ¿Qué ropa me pongo hoy en Madrid?", "h0"),
                ChatLine("human", "hola", "u1"),
                ChatLine("thinking", "voy a mirar el clima", "t1"),
                ChatLine("tool", "buscar_clima(ciudad='Madrid')", "c1"),
                ChatLine("dato", "buscar_clima: Soleado en Madrid", "d1"),
                ChatLine("bot", "Hoy chaquetita", "b1"),
            ],
            name="lines",
        )
        setup = await test_render(
            lambda: _app(
                lines=lines,
                # Tools activas: el grafo debe decir "pide tool" y "clima".
                active_node=Signal("tools", name="active_node"),
                active_tools=Signal(["buscar_clima"], name="active_tools"),
                phase=Signal("tools", name="phase"),
                status=Signal("tool clima", name="status"),
            ),
            {"width": 100, "height": 40},
        )
        try:
            return setup.capture_char_frame()
        finally:
            setup.destroy()

    async def _capture_md(self) -> str:
        lines = Signal(
            [
                ChatLine(
                    "bot",
                    "# Madrid\n\nHoy **hace sol**. Lleva:\n\n- chaqueta ligera\n\nY `tendencia_ropa`.",
                    "b-md",
                ),
            ],
            name="lines",
        )
        setup = await test_render(
            lambda: _app(lines=lines),
            {"width": 100, "height": 24},
        )
        try:
            return setup.capture_char_frame()
        finally:
            setup.destroy()

    async def _capture_dato_sucio(self) -> str:
        lines = Signal(
            [
                ChatLine("hint", "Prueba: ¿Quién marcó en la final?", "h0"),
                ChatLine(
                    "dato",
                    "buscar_web: España 2-1. Ferran Torres marcó el 2-1.\n"
                    "- FIFA — Resumen de la final\n"
                    "  https://www.fifa.com/final-2026-very-long-url-path\n"
                    "- YouTube — 81450 views #{equipoLocal}\n"
                    "  https://www.youtube.com/watch?v=xxxx\n",
                    "d-sucio",
                ),
                ChatLine("bot", "Ferran Torres marcó el 2-1 de España.", "b1"),
            ],
            name="lines",
        )
        setup = await test_render(
            lambda: _app(lines=lines),
            {"width": 100, "height": 32},
        )
        try:
            return setup.capture_char_frame()
        finally:
            setup.destroy()

    async def _capture_bot(self, texto: str, *, width: int, height: int) -> str:
        lines = Signal(
            [
                ChatLine("tool", "buscar_web(query='ganador mundial fútbol 2026')", "c1"),
                ChatLine("dato", "buscar_web: España ganó el Mundial 2026.", "d1"),
                ChatLine("bot", texto, "b1"),
            ],
            name="lines",
        )
        setup = await test_render(
            lambda: _app(lines=lines),
            {"width": width, "height": height},
        )
        try:
            return setup.capture_char_frame()
        finally:
            setup.destroy()


if __name__ == "__main__":
    unittest.main()
