"""ServiceFlow project settings with legacy deployment compatibility."""
import os
from typing import Any, Dict


def load_skill_settings(default_root: str) -> Dict[str, Any]:
    """Prefer ServiceFlow names, retaining old deployments without rewriting secrets."""
    return {
        "root_dir": os.getenv(
            "SERVICEFLOW_SKILLS_DIR", os.getenv("ECHOMIND_SKILLS_DIR", default_root)
        ),
        "max_prompt_chars": int(os.getenv(
            "SERVICEFLOW_SKILLS_MAX_PROMPT_CHARS",
            os.getenv("ECHOMIND_SKILLS_MAX_PROMPT_CHARS", "5000"),
        )),
    }
