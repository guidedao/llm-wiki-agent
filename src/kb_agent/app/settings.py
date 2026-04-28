from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(slots=True)
class Settings:
    artifacts_dir: Path
    environment: str
    openai_model: str


def load_settings() -> Settings:
    artifacts_dir = Path(os.getenv("ARTIFACTS_DIR", "artifacts"))
    environment = os.getenv("KB_AGENT_ENV", os.getenv("BRIEFING_AGENT_ENV", "local"))
    openai_model = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")
    return Settings(
        artifacts_dir=artifacts_dir,
        environment=environment,
        openai_model=openai_model,
    )
