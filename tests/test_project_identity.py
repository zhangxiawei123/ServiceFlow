"""Identity, documentation and configuration checks; no external services or LLM calls."""
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import unquote

import pytest

from core.project_config import load_skill_settings
from core.skill_loader import SkillManager


ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def clean_skill_env(monkeypatch):
    for prefix in ("SERVICEFLOW", "ECHOMIND"):
        for suffix in ("SKILLS_DIR", "SKILLS_MAX_PROMPT_CHARS"):
            monkeypatch.delenv(f"{prefix}_{suffix}", raising=False)
    return monkeypatch


def test_skill_settings_defaults(clean_skill_env):
    assert load_skill_settings("default") == {"root_dir": "default", "max_prompt_chars": 5000}


def test_legacy_skill_environment_still_works(clean_skill_env):
    clean_skill_env.setenv("ECHOMIND_SKILLS_DIR", "legacy")
    clean_skill_env.setenv("ECHOMIND_SKILLS_MAX_PROMPT_CHARS", "2300")
    assert load_skill_settings("default") == {"root_dir": "legacy", "max_prompt_chars": 2300}


def test_serviceflow_environment_has_priority(clean_skill_env):
    clean_skill_env.setenv("ECHOMIND_SKILLS_DIR", "legacy")
    clean_skill_env.setenv("ECHOMIND_SKILLS_MAX_PROMPT_CHARS", "2300")
    clean_skill_env.setenv("SERVICEFLOW_SKILLS_DIR", "current")
    clean_skill_env.setenv("SERVICEFLOW_SKILLS_MAX_PROMPT_CHARS", "4100")
    assert load_skill_settings("default") == {"root_dir": "current", "max_prompt_chars": 4100}


def test_all_document_links_resolve():
    docs = list(ROOT.glob("*.md"))
    for folder in ("wiki", "skills", "data/demo_docs"):
        docs.extend((ROOT / folder).rglob("*.md"))
    missing = []
    for doc in docs:
        for match in re.finditer(r"!?\[[^\]]*\]\(([^)]+)\)", doc.read_text(encoding="utf-8")):
            target = match.group(1).strip().strip("<>")
            if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target) or target.startswith("#"):
                continue
            relative = unquote(target.split("#", 1)[0])
            if relative and not (doc.parent / relative).exists():
                missing.append(f"{doc.relative_to(ROOT)}: {target}")
    assert not missing, "Broken links: " + "; ".join(missing)


def test_frontend_and_api_identity():
    index = (ROOT / "frontend/index.html").read_text(encoding="utf-8")
    api = (ROOT / "api/main.py").read_text(encoding="utf-8")
    assert "<title>ServiceFlow" in index
    assert "EchoMind" not in index
    assert 'title="ServiceFlow 智能客服"' in api
    app = (ROOT / "frontend/app.js").read_text(encoding="utf-8")
    assert 'localStorage.getItem("serviceflow-user-id") || localStorage.getItem("echomind-user-id")' in app


def test_business_skills_load_and_match():
    manager = SkillManager(str(ROOT / "skills"))
    loaded = manager.load()
    assert not manager.errors
    assert len(loaded) == 3
    for role, query in (("general", "你好"), ("technical", "登录报401"), ("billing", "退款多久到账")):
        assert any(skill.matches(query, role) for skill in loaded)
    assert all("ServiceFlow" in skill.content for skill in loaded)


def test_local_deployment_references_use_serviceflow():
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    nginx = (ROOT / "config/nginx/nginx.conf").read_text(encoding="utf-8")
    prometheus = (ROOT / "config/prometheus.yml").read_text(encoding="utf-8")
    assert "  serviceflow:" in compose
    assert "server serviceflow:8000" in nginx
    assert "serviceflow:8000" in prometheus
    assert "CHROMA_HOST=chromadb" in compose
    assert "CHROMA_PORT=8000" in compose
    assert "echomind" not in compose + nginx + prometheus


def test_diagrams_are_valid_and_branded():
    diagrams = list((ROOT / "wiki/assets").rglob("*.svg"))
    assert len(diagrams) == 7
    for path in diagrams:
        tree = ET.parse(path)
        text = " ".join(tree.getroot().itertext())
        assert "SERVICEFLOW" in text
        assert "EchoMind" not in text


def test_demo_knowledge_has_no_fabricated_product_claims():
    docs = json.loads((ROOT / "data/demo_docs/sample_knowledge.json").read_text(encoding="utf-8"))
    assert len(docs) == 6
    combined = " ".join(doc["content"] for doc in docs)
    assert "SOC2" not in combined
    assert "准确率提升至" not in combined
    assert "ServiceFlow" in combined
