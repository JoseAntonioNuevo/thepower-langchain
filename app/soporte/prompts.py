"""Registro privado de prompts propios y recuperación de versiones inmutables."""

import hashlib
import json
import uuid
from datetime import datetime, timezone
from .config import ROOT
from .graph import local_prompt, prompt_template

MANIFEST = ROOT / "material/profesor/prompts-remotos.json"


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def register_prompts(telemetry):
    if not telemetry.ls or not telemetry.lf:
        raise ValueError("Registrar requiere modo both")
    if MANIFEST.exists():
        manifest = json.loads(MANIFEST.read_text())
        if set(manifest["versions"]) == {"v1", "v2"}:
            return manifest
        name = manifest["name"]
    else:
        name = "thepower-soporte-202610-" + uuid.uuid4().hex[:8]
        manifest = {
            "name": name,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "versions": {},
        }
        MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

    for version in ["v1", "v2"]:
        if version in manifest["versions"]:
            continue
        text = local_prompt(version)
        template = ChatPromptTemplate.from_messages(
            [("system", text), MessagesPlaceholder("messages")]
        )
        telemetry.ls.push_prompt(
            name,
            object=template,
            is_public=False,
            commit_tags=[version],
            description="Práctica privada S5/S6 thePower",
        )
        commit = telemetry.ls.pull_prompt_commit(name + ":" + version)
        lf = telemetry.lf.create_prompt(
            name=name,
            type="text",
            prompt=text,
            labels=[version],
            config={"course_version": version},
            tags=["thepower"],
        )
        manifest["versions"][version] = {
            "sha256": sha(text),
            "langsmith_commit": commit.commit_hash,
            "langfuse_version": lf.version,
        }
        MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def resolve_prompt(version, source, telemetry):
    if source == "local":
        text = local_prompt(version)
        return prompt_template(text), {
            "prompt_version": version,
            "prompt_source": "local",
            "prompt_sha256": sha(text),
        }
    if source != "remote":
        raise ValueError("Fuente inválida")
    manifest = json.loads(MANIFEST.read_text())
    spec = manifest["versions"][version]
    meta = {
        "prompt_version": version,
        "prompt_source": "remote",
        "prompt_sha256": spec["sha256"],
        "langsmith_commit": spec["langsmith_commit"],
        "langfuse_version": spec["langfuse_version"],
    }
    texts = []
    template_meta = {}
    if telemetry.ls:
        p = telemetry.ls.pull_prompt(
            manifest["name"] + ":" + spec["langsmith_commit"], skip_cache=True
        )
        texts.append(p.format_messages(messages=[])[0].content)
        template_meta.update(getattr(p, "metadata", None) or {})
    if telemetry.lf:
        p = telemetry.lf.get_prompt(
            manifest["name"], version=spec["langfuse_version"], cache_ttl_seconds=0
        )
        texts.append(p.prompt)
        template_meta["langfuse_prompt"] = p
    if not texts or any(sha(text) != spec["sha256"] for text in texts):
        raise ValueError("El prompt remoto no coincide con la versión congelada")
    if sha(local_prompt(version)) != spec["sha256"]:
        raise ValueError(
            "El prompt local cambió; no se permite mezclar resultados de versiones distintas"
        )
    return prompt_template(texts[0], template_meta), meta
