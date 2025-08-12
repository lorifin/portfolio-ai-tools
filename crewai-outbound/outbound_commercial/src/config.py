from __future__ import annotations
import os
from dataclasses import dataclass

@dataclass
class Settings:
    openai_api_key: str
    openai_model: str
    serper_api_key: str | None
    telemetry_disabled: bool

def load_settings() -> Settings:
    return Settings(
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        openai_model=os.getenv("OPENAI_MODEL_NAME", "gpt-3.5-turbo"),
        serper_api_key=os.getenv("SERPER_API_KEY"),
        telemetry_disabled=os.getenv("CREWAI_TELEMETRY", "false").lower() == "false"
    )
