import os
from pathlib import Path

from core.agent_runtime import AgentRuntime
from llm.router import get_client
from persistence.storage import load_yaml


def load_agent(agent_name: str) -> AgentRuntime:
    agents_path = Path(os.getenv("AGENTS_REPO_PATH")) / "agents" / agent_name

    agent_yaml = agents_path / "agent.yaml"
    if not agent_yaml.exists():
        raise FileNotFoundError(f"Agent config not found: {agent_yaml}")

    config = load_yaml(str(agent_yaml))
    config["_agent_path"] = str(agents_path)

    skills_yaml = agents_path / "skills.yaml"
    skills = load_yaml(str(skills_yaml)) if skills_yaml.exists() else {}

    llm = get_client(config["llm"])
    return AgentRuntime(config, skills, llm)
