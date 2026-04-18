import logging
import os
from typing import Protocol

from openai import OpenAI

logger = logging.getLogger(__name__)


class LLMClient(Protocol):
    def generate(self, prompt: str, system: str | None = None) -> str:
        ...


class OpenAIClient:
    def __init__(self, base_url: str, api_key: str, model: str):
        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.model = model

    def generate(self, prompt: str, system: str | None = None) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        logger.debug(
            "[LLM →] model=%s system=%s\n%s",
            self.model,
            system[:80] if system else None,
            prompt,
        )

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.8,
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", "4096")),
        )
        result = response.choices[0].message.content

        logger.debug("[LLM ←] model=%s\n%s", self.model, result)

        return result
