"""Configuration for DeepSeek's Anthropic-compatible Messages endpoint."""
import os
from typing import Any, Dict, Mapping, Optional


def load_llm_config(env: Optional[Mapping[str, str]] = None) -> Dict[str, Any]:
    """Return DeepSeek client settings, with legacy Anthropic-name fallback."""
    source = os.environ if env is None else env
    key = (
        source.get("DEEPSEEK_API_KEY", "").strip()
        or source.get("ANTHROPIC_API_KEY", "").strip()
    )
    if not key:
        raise RuntimeError("未设置 DEEPSEEK_API_KEY")

    return {
        "api_key": key,
        "model": (
            source.get("DEEPSEEK_MODEL", "").strip()
            or source.get("ANTHROPIC_MODEL", "").strip()
            or "deepseek-v4-pro"
        ),
        "base_url": (
            source.get("DEEPSEEK_BASE_URL", "").strip()
            or source.get("ANTHROPIC_BASE_URL", "").strip()
            or "https://api.deepseek.com/anthropic"
        ),
    }
