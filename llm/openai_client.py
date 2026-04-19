import logging
import os
import time
from typing import Protocol

import httpx
from openai import OpenAI, APITimeoutError, APIConnectionError
from openai.types.chat import ChatCompletionMessageParam

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 120.0   # seconds — covers slow local Ollama inference
_DEFAULT_RETRIES = 3
_RETRY_BACKOFF  = 2.0      # seconds; doubles each attempt


class LLMClient(Protocol):
    def generate(self, prompt: str, system: str | None = None) -> str:
        ...


class OpenAIClient:
    def __init__(self, base_url: str, api_key: str, model: str):
        timeout = float(os.getenv("LLM_TIMEOUT", str(_DEFAULT_TIMEOUT)))
        self.client = OpenAI(
            base_url=base_url,
            api_key=api_key,
            timeout=httpx.Timeout(timeout, connect=10.0),
        )
        self.model = model
        self._max_retries = int(os.getenv("LLM_MAX_RETRIES", str(_DEFAULT_RETRIES)))

    def generate(self, prompt: str, system: str | None = None) -> str:
        messages: list[ChatCompletionMessageParam] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        logger.debug(
            "[LLM →] model=%s system=%s\n%s",
            self.model,
            system[:80] if system else None,
            prompt,
        )

        last_exc: Exception | None = None
        delay = _RETRY_BACKOFF

        for attempt in range(1, self._max_retries + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.8,
                    max_tokens=int(os.getenv("LLM_MAX_TOKENS", "4096")),
                )
                result = response.choices[0].message.content or ""
                logger.debug("[LLM ←] model=%s\n%s", self.model, result)
                return result

            except (APITimeoutError, APIConnectionError) as exc:
                last_exc = exc
                if attempt < self._max_retries:
                    logger.warning(
                        "[LLM] %s on attempt %d/%d — retrying in %.1fs",
                        type(exc).__name__, attempt, self._max_retries, delay,
                    )
                    time.sleep(delay)
                    delay *= 2
                else:
                    logger.error(
                        "[LLM] %s — all %d attempts exhausted",
                        type(exc).__name__, self._max_retries,
                    )

        raise last_exc  # type: ignore[misc]
