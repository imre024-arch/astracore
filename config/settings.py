import os
from dotenv import load_dotenv

load_dotenv()

REQUIRED_VARS = [
    "WRITER_LLM_BASE_URL",
    "WRITER_LLM_API_KEY",
    "WRITER_LLM_MODEL",
    "MENTOR_LLM_BASE_URL",
    "MENTOR_LLM_API_KEY",
    "MENTOR_LLM_MODEL",
    "AGENTS_REPO_PATH",
    "RUN_MODE",
    "CRITIQUE_LOOP_COUNT",
    "DEBATE_LOOP_COUNT",
]


def validate() -> None:
    missing = [v for v in REQUIRED_VARS if not os.getenv(v)]
    if missing:
        raise EnvironmentError(f"Missing required environment variables: {missing}")
