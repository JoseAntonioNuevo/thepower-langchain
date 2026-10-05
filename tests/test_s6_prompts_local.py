"""Contrato del módulo de prompts con servicios simulados; no usa SDKs ni red."""
import importlib.util
import json
import sys
import tempfile
import types
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
TEXTS = {"v1": "Prompt inicial", "v2": "Prompt concreto"}


@contextmanager
def isolated_prompts(directory):
    # Namespace privado para no sustituir app.soporte en la suite del repositorio.
    package = types.ModuleType("_s6_prompt_test")
    package.__path__ = [str(ROOT / "app/soporte")]
    config = types.ModuleType("_s6_prompt_test.config")
    config.ROOT = Path(directory)
    graph = types.ModuleType("_s6_prompt_test.graph")
    graph.local_prompt = lambda version: TEXTS[version]
    graph.prompt_template = lambda text, metadata=None: (text, metadata)
    sdk = types.ModuleType("langchain_core.prompts")
    sdk.ChatPromptTemplate = types.SimpleNamespace(from_messages=lambda messages: messages)
    sdk.MessagesPlaceholder = lambda name: name
    modules = {"_s6_prompt_test": package, "_s6_prompt_test.config": config,
               "_s6_prompt_test.graph": graph, "langchain_core.prompts": sdk}
    with patch.dict(sys.modules, modules):
        spec = importlib.util.spec_from_file_location("_s6_prompt_test.prompts", ROOT / "app/soporte/prompts.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        yield module


def fake_services():
    ls, lf = Mock(), Mock()
    ls.pull_prompt_commit.return_value = types.SimpleNamespace(commit_hash="commit-demo")
    lf.create_prompt.side_effect = [types.SimpleNamespace(version=1), types.SimpleNamespace(version=2)]
    return types.SimpleNamespace(ls=ls, lf=lf)


class PromptContractTests(unittest.TestCase):
    def test_register_fresh_clone_creates_manifest(self):
        with tempfile.TemporaryDirectory() as d, isolated_prompts(d) as p:
            t = fake_services()
            result = p.register_prompts(t)
            self.assertEqual(set(result["versions"]), {"v1", "v2"})
            self.assertEqual(json.loads(p.MANIFEST.read_text()), result)
            self.assertEqual(t.ls.push_prompt.call_count, 2)
            self.assertEqual(t.lf.create_prompt.call_count, 2)
            self.assertFalse(t.ls.push_prompt.call_args.kwargs["is_public"])

    def test_complete_manifest_does_not_register_twice(self):
        with tempfile.TemporaryDirectory() as d, isolated_prompts(d) as p:
            t = fake_services()
            p.register_prompts(t)
            p.register_prompts(t)
            self.assertEqual(t.ls.push_prompt.call_count, 2)

    def test_changed_local_prompt_is_rejected(self):
        with tempfile.TemporaryDirectory() as d, isolated_prompts(d) as p:
            t = fake_services()
            p.register_prompts(t)
            with patch.object(p, "local_prompt", return_value="otro texto"):
                with self.assertRaisesRegex(ValueError, "local cambió"):
                    p.register_prompts(t)

    def test_new_registration_does_not_restore_legacy(self):
        with tempfile.TemporaryDirectory() as d, isolated_prompts(d) as p:
            p.LEGACY_MANIFEST.parent.mkdir(parents=True)
            p.LEGACY_MANIFEST.write_text(json.dumps({"name": "old", "versions": {}}))
            result = p.register_prompts(fake_services(), migrate=False)
            self.assertNotEqual(result["name"], "old")
            self.assertEqual(json.loads(p.LEGACY_MANIFEST.read_text())["name"], "old")

    def test_remote_version_is_retrieved_verified_and_applied(self):
        with tempfile.TemporaryDirectory() as d, isolated_prompts(d) as p:
            t = fake_services(); p.register_prompts(t)
            t.ls.pull_prompt.return_value = types.SimpleNamespace(
                metadata={}, format_messages=lambda **kw: [types.SimpleNamespace(content=TEXTS["v2"])])
            t.lf.get_prompt.return_value = types.SimpleNamespace(prompt=TEXTS["v2"])
            template, meta = p.resolve_prompt("v2", "remote", t)
            self.assertEqual(template[0], TEXTS["v2"])
            self.assertEqual(meta["prompt_source"], "remote")
            self.assertEqual(t.lf.get_prompt.call_args.kwargs["version"], 2)
            self.assertTrue(t.ls.pull_prompt.call_args.args[0].endswith(":commit-demo"))

    def test_remote_disagreement_is_rejected(self):
        with tempfile.TemporaryDirectory() as d, isolated_prompts(d) as p:
            t = fake_services(); p.register_prompts(t)
            t.ls.pull_prompt.return_value = types.SimpleNamespace(
                metadata={}, format_messages=lambda **kw: [types.SimpleNamespace(content=TEXTS["v2"])])
            t.lf.get_prompt.return_value = types.SimpleNamespace(prompt="versión incorrecta")
            with self.assertRaisesRegex(ValueError, "remoto no coincide"):
                p.resolve_prompt("v2", "remote", t)

    def test_missing_manifest_has_actionable_error(self):
        with tempfile.TemporaryDirectory() as d, isolated_prompts(d) as p:
            with self.assertRaisesRegex(ValueError, "registrar_prompts.py"):
                p.resolve_prompt("v1", "remote", fake_services())

    def test_local_mode_never_accesses_services(self):
        with tempfile.TemporaryDirectory() as d, isolated_prompts(d) as p:
            template, meta = p.resolve_prompt("v1", "local", None)
            self.assertEqual(template[0], TEXTS["v1"])
            self.assertEqual(meta["prompt_source"], "local")
            self.assertFalse(p.MANIFEST.exists())


if __name__ == "__main__":
    unittest.main()
