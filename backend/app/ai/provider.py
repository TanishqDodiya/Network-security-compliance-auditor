"""AI provider abstraction: one interface, swappable backends, safe fallback.

Beginner idea: the app never talks to OpenAI/Anthropic directly.
It talks to `AIProvider`. If a key is configured we try the real LLM;
if anything fails (no key, no network, bad response) we use the
deterministic fallback so the demo never breaks. API keys stay on the
backend (env vars) and are never sent to the frontend.
"""

import os
from dataclasses import dataclass


@dataclass
class AIConfig:
    provider: str = "none"  # openai | none (more later: anthropic, gemini)
    api_key: str = ""
    model: str = "gpt-4o-mini"

    @property
    def available(self) -> bool:
        return bool(self.api_key) and self.provider in {"openai"}


def load_ai_config() -> AIConfig:
    """Read AI settings from environment. Never hard-code keys."""
    return AIConfig(
        provider=os.getenv("AI_PROVIDER", "none").strip().lower() or "none",
        api_key=os.getenv("AI_API_KEY", "").strip(),
        model=os.getenv("AI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini",
    )
