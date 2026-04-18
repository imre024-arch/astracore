import os
from llm.openai_client import OpenAIClient, LLMClient


def get_client(llm_prefix: str) -> LLMClient:
    base_url = os.getenv(f"{llm_prefix}_LLM_BASE_URL")
    api_key  = os.getenv(f"{llm_prefix}_LLM_API_KEY")
    model    = os.getenv(f"{llm_prefix}_LLM_MODEL")

    missing = [k for k, v in {
        f"{llm_prefix}_LLM_BASE_URL": base_url,
        f"{llm_prefix}_LLM_API_KEY":  api_key,
        f"{llm_prefix}_LLM_MODEL":    model,
    }.items() if v is None]

    if missing:
        raise ValueError(f"Missing required env vars: {missing}")

    return OpenAIClient(base_url=base_url, api_key=api_key, model=model)
