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

    if tool_name == "wordpress_publish_tool":
        return _publish_to_wordpress(tool_config.get("config", {}), params, context)

    if tool_name == "knowledgebase_query_tool":
        return _query_knowledgebase(params, context)

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


def _publish_to_wordpress(config: dict, params: dict, context: dict) -> str:
    import base64
    import requests

    base_url = os.getenv("WP_BASE_URL")
    username = os.getenv("WP_USERNAME")
    app_password = os.getenv("WP_APP_PASSWORD")

    if not all([base_url, username, app_password]):
        raise ValueError("WP_BASE_URL, WP_USERNAME, and WP_APP_PASSWORD must be set in .env")

    raw = params.get("content", context.get("publisher_output", context.get("last_output", "")))

    # Parse TITLE: / CONTENT: sections from publisher agent output
    title = "Untitled Story"
    content = raw
    lines = raw.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("TITLE:"):
            title = line[len("TITLE:"):].strip()
        elif line.startswith("CONTENT:"):
            content = "\n".join(lines[i + 1:]).strip()
            break

    # Convert plain text to HTML paragraphs
    html = "\n".join(
        f"<p>{para.strip()}</p>"
        for para in content.split("\n\n")
        if para.strip()
    )

    credentials = base64.b64encode(f"{username}:{app_password}".encode()).decode()
    response = requests.post(
        f"{base_url.rstrip('/')}/wp-json/wp/v2/posts",
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/json",
        },
        json={
            "title": title,
            "content": html,
            "status": config.get("post_status", "publish"),
            "format": config.get("post_format", "standard"),
        },
        timeout=30,
    )
    response.raise_for_status()
    post_url = response.json().get("link", "")
    logger.info("[wordpress] Published '%s': %s", title, post_url)
    return f"Published: {title}\nURL: {post_url}"


def _query_knowledgebase(params: dict, context: dict) -> str:
    from knowledge.graph_store import GraphStore

    story_id = context.get("story_id")
    if not story_id:
        raise ValueError("knowledgebase_query_tool requires 'story_id' in context")

    query_type = params.get("query_type", "all")
    node_id = params.get("node_id", "").strip()

    store = GraphStore(story_id)
    try:
        if node_id:
            node = store.get_node(node_id)
            if not node:
                return f"No node found with id '{node_id}'."
            neighbors = store.get_neighbors(node_id, direction="both")
            lines = [f"[{node.get('type', 'Node')}] {node_id}", _format_props(node)]
            if neighbors:
                lines.append("Neighbors:")
                for n in neighbors:
                    lines.append(f"  - [{n.get('type', '?')}] {n.get('id', '')}: {n.get('name', n.get('id', ''))}")
            return "\n".join(lines)

        nodes = store.get_all_nodes() if query_type == "all" else store.get_nodes_by_type(query_type)
        if not nodes:
            return f"No nodes of type '{query_type}' found in the knowledge graph."

        lines = [f"Knowledge graph — {query_type} ({len(nodes)} nodes):"]
        for n in nodes:
            lines.append(f"\n[{n.get('type', query_type)}] {n.get('id', '')}")
            lines.append(_format_props(n))
        return "\n".join(lines)
    finally:
        store.close()


def _format_props(node: dict) -> str:
    skip = {"id", "type"}
    pairs = [f"  {k}: {v}" for k, v in node.items() if k not in skip and v]
    return "\n".join(pairs) if pairs else "  (no properties)"
