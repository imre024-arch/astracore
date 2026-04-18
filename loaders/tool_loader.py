import logging
import os
from pathlib import Path

from persistence.storage import load_yaml

logger = logging.getLogger(__name__)


def execute_tool(tool_name: str, params: dict, context: dict) -> str:
    agents_path = Path(os.getenv("AGENTS_REPO_PATH"))
    tool_file = agents_path / "tools" / f"{tool_name}.yaml"

    if not tool_file.exists():
        raise FileNotFoundError(f"Tool config not found: {tool_file}")

    tool_config = load_yaml(str(tool_file))

    if tool_name == "agent_call_tool":
        from loaders.agent_loader import load_agent
        agent = load_agent(params["agent_name"])
        return agent.run(params["input_text"], context)

    if tool_name == "debate_tool":
        return _run_debate(tool_config.get("config", {}), params, context)

    raise ValueError(f"Unknown tool: '{tool_name}'")


def _run_debate(config: dict, params: dict, context: dict) -> str:
    from loaders.agent_loader import load_agent

    participants = [load_agent(name) for name in config.get("participants", [])]
    turns = int(os.getenv("DEBATE_LOOP_COUNT", "2"))
    transcript = []
    current_input = params.get("input_text", context.get("last_output", ""))

    for _ in range(turns):
        for agent in participants:
            response = agent.run(current_input, context)
            if isinstance(response, dict):
                response = str(response)
            transcript.append(f"[{agent.config['name']}]:\n{response}")
            current_input = response

    return "\n---\n".join(transcript)
