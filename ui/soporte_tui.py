"""Chat visual de las etapas de soporte, reutilizando la TUI preparada.

SupportController conserva el editor, chat, teclado y cola de UI de ChatController.
Su panel muestra los nodos reales del soporte, sin juez ni validador ficticios.
Cada mensaje ejecuta run_turn una sola vez; los updates muestran nodos y tools.
Sin SQLite, el historial dura solo esta sesión mediante InMemorySaver. Con SQLite,
se recupera al reabrir con la misma DB y el mismo hilo. Los JSON son respaldo.
"""

import asyncio
import json
import sys
from pathlib import Path

from langgraph.checkpoint.memory import InMemorySaver
from opentui import Box, Signal, Text, render, use_renderer
from ui.chat_lines import ChatLine, lineas_de_update
from ui.chat_tui import (
    BG, BRIGHT, DATO, DIM, SURFACE, ChatController, build_app,
)
from app.soporte.runner import run_turn


class SupportController(ChatController):
    """Conecta el agente de soporte con el chat visual, sin duplicar su lógica."""

    def __init__(self, *, model, cfg, telemetry, args, use_tools, memory):
        super().__init__(None, {}, cfg.model_id, args.hilo)
        self.model, self.cfg, self.telemetry = model, cfg, telemetry
        self.args, self.use_tools, self.memory = args, use_tools, memory
        self.session_memory = InMemorySaver()
        self.node = Signal("listo", name="support_node")
        self.route = Signal("", name="support_route")
        self.count = Signal(0, name="support_count")
        self.errors = Signal("ninguno", name="support_errors")
        self.lines.set([ChatLine("hint", "Escribe una pregunta. Enter envía; Esc sale.")])

    def submit(self, texto):
        # El controlador original administra teclado, worker y mensajes del usuario.
        previous = self.turnos()
        super().submit(texto)
        if self.turnos() != previous:
            self.node.set("inicio")
            self.phase.set("thinking")
            self.status.set("ejecutando…")
            self.route.set("")
            self.count.set(0)
            self.errors.set("ninguno")

    def _update(self, payload):
        # El worker encola cambios; solo drain, en el hilo de UI, toca los Signals.
        for node, state in payload.items():
            if not isinstance(state, dict):
                continue
            lines = lineas_de_update({node: state})
            # Presentar datos de tools como texto legible, dejando el JSON completo
            # en el respaldo. No cambiamos los mensajes que recibe el modelo.
            formatted = []
            for line in lines:
                if line.kind == "dato" and ": " in line.text:
                    name, body = line.text.split(": ", 1)
                    try:
                        data = json.loads(body)
                        values = data.get("datos")
                        if isinstance(values, dict):
                            body = data["id"] + " · " + " · ".join(
                                f"{key}: {value}" for key, value in values.items())
                        else:
                            body = f"{data.get('id', '')} · {data.get('error', 'sin datos')}"
                        line = ChatLine("dato", name + ": " + body)
                    except (ValueError, TypeError, KeyError):
                        pass
                formatted.append(line)
            lines = formatted

            def apply(node=node, state=state, lines=lines):
                self.node.set(node)
                self.status.set(f"nodo {node}")
                if "route" in state:
                    self.route.set(" → ".join(state["route"]))
                if "tool_count" in state:
                    self.count.set(state["tool_count"])
                if "errors" in state:
                    self.errors.set(", ".join(state["errors"]) or "ninguno")
                self._append(lines)

            self._ui(apply)

    def _run_turn(self, texto):
        # Misma ejecución e instrumentación que la consola. No se llama al agente
        # una segunda vez para obtener trazas o generar el archivo de respaldo.
        try:
            record = run_turn(
                model=self.model, cfg=self.cfg, telemetry=self.telemetry,
                question=texto, thread_id=self.thread_id,
                db=self.args.db if self.memory else None,
                memory_saver=None if self.memory else self.session_memory,
                version=self.args.version, source=self.args.prompts,
                scenario=self.args.escenario, use_tools=self.use_tools,
                on_update=self._update,
            )
            if self.args.salida:
                out = Path(self.args.salida)
                out.parent.mkdir(parents=True, exist_ok=True)
                text = json.dumps(record, ensure_ascii=False, indent=2) + "\n"
                out.write_text(text)
                # Conservar todos los turnos además del último resultado.
                archive = out.parent / (out.stem + "-turnos")
                archive.mkdir(exist_ok=True)
                (archive / (record["query_id"] + ".json")).write_text(text)
            self._ui(lambda: self.node.set(record["status"]))
        except Exception as exc:
            # Mostrar el tipo del error, sin volcar credenciales/cuerpos del proveedor.
            message = f"No se pudo completar el turno: {type(exc).__name__}"
            self._ui(lambda: self._append([ChatLine("error", message)]))
        finally:
            self._ui(self._idle)

    def _sidebar(self):
        # El panel se corresponde con el grafo de soporte, no con el avanzado.
        flow = "START → inicio → chatbot"
        flow += "\nchatbot → tools → chatbot\nchatbot → END" if self.use_tools else "\nchatbot → END"
        mode = "SQLite · persiste al salir" if self.memory else "RAM · solo esta sesión"
        return Box(
            Text("Agente de soporte", fg=BRIGHT, bold=True),
            Text(flow, fg=DATO, wrap_mode="word"),
            Text(mode, fg=DIM, wrap_mode="word"),
            Text(lambda: f"Nodo: {self.node()}", fg=BRIGHT),
            Text(lambda: f"Intentos tools: {self.count()} / 2", fg=DATO),
            Text(lambda: "Ruta: " + self.route(), fg=BRIGHT, wrap_mode="word"),
            Text(lambda: "Errores: " + self.errors(), fg=BRIGHT, wrap_mode="word"),
            flex_direction="column", gap=0, width=34, flex_shrink=0,
            border=True, border_style="round", background_color=SURFACE,
            padding=1, title="recorrido",
        )

    def app(self):
        renderer = use_renderer()
        if renderer is not None and self.drain not in renderer._post_process_fns:
            renderer.add_post_process_fn(self.drain)
        return build_app(
            modelo=self.modelo, thread_id=self.thread_id, lines=self.lines,
            busy=self.busy, active_node=self.active_node, active_tools=self.active_tools,
            status=self.status, draft=self.draft, phase=self.phase,
            turnos=self.turnos, on_submit=self.submit, on_quit=self.quit,
            sidebar_factory=self._sidebar,
        )


def run_support_tui(**kwargs):
    """Abre la TUI en una terminal real y espera al turno activo antes del cierre."""
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise ValueError("La TUI necesita la terminal integrada de Cursor o una terminal real")
    controller = SupportController(**kwargs)
    try:
        asyncio.run(render(controller.app))
    finally:
        if controller._worker is not None:
            controller._worker.join()
