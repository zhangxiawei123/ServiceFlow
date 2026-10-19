import pytest

from core.llm_config import load_llm_config


_CONFIG_NAMES = (
    "DEEPSEEK_API_KEY",
    "DEEPSEEK_MODEL",
    "DEEPSEEK_BASE_URL",
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_MODEL",
    "ANTHROPIC_BASE_URL",
)


def _clear_config(monkeypatch):
    for name in _CONFIG_NAMES:
        monkeypatch.delenv(name, raising=False)


def test_deepseek_configuration_is_preferred(monkeypatch):
    _clear_config(monkeypatch)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "deepseek-key")
    monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-v4-pro")
    monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "legacy-key")

    assert load_llm_config() == {
        "api_key": "deepseek-key",
        "model": "deepseek-v4-pro",
        "base_url": "https://api.deepseek.com/anthropic",
    }


def test_deepseek_defaults_are_used(monkeypatch):
    _clear_config(monkeypatch)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "deepseek-key")

    assert load_llm_config() == {
        "api_key": "deepseek-key",
        "model": "deepseek-v4-pro",
        "base_url": "https://api.deepseek.com/anthropic",
    }


def test_legacy_anthropic_names_remain_supported(monkeypatch):
    _clear_config(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "legacy-key")
    monkeypatch.setenv("ANTHROPIC_MODEL", "legacy-model")
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://legacy.example/anthropic")

    assert load_llm_config() == {
        "api_key": "legacy-key",
        "model": "legacy-model",
        "base_url": "https://legacy.example/anthropic",
    }


def test_missing_api_key_is_rejected(monkeypatch):
    _clear_config(monkeypatch)

    with pytest.raises(RuntimeError, match="DEEPSEEK_API_KEY"):
        load_llm_config()
