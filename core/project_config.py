"""ServiceFlow project settings."""
import os
from typing import Any, Dict


def load_skill_settings(default_root: str) -> Dict[str, Any]:
    """Read ServiceFlow environment variables with explicit defaults."""
    return {
        "root_dir": os.getenv("SERVICEFLOW_SKILLS_DIR", default_root),
        "max_prompt_chars": int(os.getenv(
            "SERVICEFLOW_SKILLS_MAX_PROMPT_CHARS",
            "5000",
        )),
    }
