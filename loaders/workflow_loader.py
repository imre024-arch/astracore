import os
import re
from pathlib import Path

from persistence.storage import load_yaml


def resolve_env(value: str) -> str:
    def replacer(match):
        var_name = match.group(1)
        val = os.getenv(var_name)
        if val is None:
            raise ValueError(f"Env var '{var_name}' referenced in workflow is not set")
        return val

    return re.sub(r"\$\{(\w+)\}", replacer, str(value))


def _resolve_node(node):
    if isinstance(node, str):
        return resolve_env(node)
    if isinstance(node, dict):
        return {k: _resolve_node(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_resolve_node(item) for item in node]
    return node


def load_workflow(workflow_name: str) -> dict:
    agents_path = Path(os.getenv("AGENTS_REPO_PATH"))
    workflow_file = agents_path / "workflows" / f"{workflow_name}.yaml"

    if not workflow_file.exists():
        raise FileNotFoundError(f"Workflow not found: {workflow_file}")

    workflow = load_yaml(str(workflow_file))
    return _resolve_node(workflow)
