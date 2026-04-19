import logging
import re

logger = logging.getLogger(__name__)


def write_to_graph(text: str, agent_name: str, store) -> int:
    """
    Parse agent output and write to graph.
    Always stores the full text as a Document node (reliable fallback for context retrieval).
    Also parses any NODE:/EDGE: blocks into typed graph nodes.
    Returns total count of items written.
    """
    if not text or not text.strip():
        logger.warning("[graph_writer] Empty output from agent '%s', skipping", agent_name)
        return 0

    count = 0

    # Always persist the raw document so context_orchestrator can retrieve it by agent type
    agent_key = agent_name.replace("/", "_").replace("\\", "_")
    store.add_node(
        node_id=f"doc_{agent_key}",
        node_type="Document",
        properties={"agent": agent_name, "content": text},
    )
    count += 1

    # Parse structured NODE:/EDGE: blocks if the agent included them
    count += _parse_graph_blocks(text, store)

    return count


def _parse_graph_blocks(text: str, store) -> int:
    """Extract and write NODE:/EDGE: blocks. Returns count written."""
    count = 0
    blocks = _split_blocks(text)
    for block in blocks:
        lines = [ln for ln in block.strip().splitlines() if ln.strip()]
        if not lines:
            continue
        first = lines[0].strip()
        if re.match(r"^NODE\s*:", first, re.IGNORECASE):
            node_type = first.split(":", 1)[1].strip()
            _write_node(node_type, lines[1:], store)
            count += 1
        elif re.match(r"^EDGE\s*:", first, re.IGNORECASE):
            _write_edge(first.split(":", 1)[1].strip(), store)
            count += 1
    if count:
        logger.debug("[graph_writer] Parsed %d structured NODE/EDGE blocks", count)
    return count


def _split_blocks(text: str) -> list[str]:
    blocks, current = [], []
    for line in text.splitlines():
        if line.strip():
            current.append(line)
        else:
            if current:
                blocks.append("\n".join(current))
                current = []
    if current:
        blocks.append("\n".join(current))
    return blocks


def _write_node(node_type: str, lines: list[str], store) -> None:
    props: dict = {}
    node_id: str | None = None
    for line in lines:
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip().lower()
        value = value.strip()
        if key == "id":
            node_id = _slugify(value)
        else:
            props[key] = value
    if not node_id:
        name = props.get("name", node_type)
        node_id = f"{node_type.lower()}_{_slugify(name)}"
    store.add_node(node_id, node_type, props)


def _write_edge(edge_text: str, store) -> None:
    # Format: from_id REL_TYPE to_id
    parts = edge_text.split(None, 2)
    if len(parts) < 3:
        logger.warning("[graph_writer] Malformed EDGE line: '%s'", edge_text)
        return
    from_id, rel_type, to_id = _slugify(parts[0]), parts[1].upper(), _slugify(parts[2].split()[0])
    store.add_edge(from_id, rel_type, to_id)


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9_]", "_", text.lower().strip())[:64]
