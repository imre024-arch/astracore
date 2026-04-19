import logging
import re

logger = logging.getLogger(__name__)

# Arc states and phrases that contradict them
_ARC_CONTRADICTIONS: dict[str, list[str]] = {
    "idealist":  ["gave up on everything", "betrayed everyone", "lost all hope", "became cynical"],
    "corrupt":   ["completely selfless", "fully redeemed", "sacrificed himself for all"],
    "redeemed":  ["reverted to evil", "betrayed them again", "went back to the dark side"],
    "broken":    ["fully confident", "completely healed", "no longer afraid of anything"],
    "growth":    ["refused to change", "learned nothing", "stayed exactly the same"],
}


def check_consistency(scene_text: str, scene_id: str, story_id: str) -> list[str]:
    """
    Run consistency checks on a written scene against the knowledge graph.
    Logs violations as warnings and writes CONTRADICTS edges to the graph.
    Returns the list of violation strings (empty = clean).
    """
    from knowledge.graph_store import GraphStore
    store = GraphStore(story_id)
    try:
        violations: list[str] = []
        violations += _check_character_arcs(scene_text, store)
        violations += _check_world_rules(scene_text, store)
        violations += _check_character_knowledge(scene_text, store)

        if violations:
            for v in violations:
                # Record violation as a self-loop edge on the scene node
                try:
                    store.add_edge(scene_id, "CONTRADICTS", scene_id, {"violation": v})
                except Exception:
                    pass  # scene node may not exist yet; violation is still returned
            logger.warning(
                "[continuity_guard] %d violation(s) in scene '%s': %s",
                len(violations), scene_id, "; ".join(violations)
            )
        else:
            logger.debug("[continuity_guard] Scene '%s' — no violations", scene_id)

        return violations
    finally:
        store.close()


def _check_character_arcs(scene_text: str, store) -> list[str]:
    violations = []
    text_lower = scene_text.lower()
    for char in store.get_nodes_by_type("Character"):
        name = char.get("name", "")
        arc_state = char.get("arc_state", "").lower()
        if not name or not arc_state or name.lower() not in text_lower:
            continue
        for contradiction in _ARC_CONTRADICTIONS.get(arc_state, []):
            if contradiction.lower() in text_lower:
                violations.append(
                    f"Character '{name}' (arc_state={arc_state!r}) — "
                    f"scene contains '{contradiction}' which contradicts their arc"
                )
    return violations


def _check_world_rules(scene_text: str, store) -> list[str]:
    """
    Checks Location rules stored as 'NO: <thing>' or 'FORBIDDEN: <thing>' entries.
    Violations are flagged when the forbidden thing appears in the scene near the location name.
    """
    violations = []
    text_lower = scene_text.lower()
    for loc in store.get_nodes_by_type("Location"):
        loc_name = loc.get("name", "")
        if not loc_name or loc_name.lower() not in text_lower:
            continue
        rules_raw = loc.get("rules", "")
        rules = rules_raw if isinstance(rules_raw, list) else [rules_raw]
        for rule in rules:
            rule_str = str(rule).strip()
            for prefix in ("no:", "no ", "forbidden:", "not allowed:"):
                if rule_str.lower().startswith(prefix):
                    forbidden = rule_str[len(prefix):].strip().lower()
                    if forbidden and _near(loc_name, forbidden, text_lower):
                        violations.append(
                            f"Location '{loc_name}' rule violated: '{rule_str}' — "
                            f"'{forbidden}' appears in scene"
                        )
    return violations


def _check_character_knowledge(scene_text: str, store) -> list[str]:
    """
    Flags cases where a character seems to know something their Document node says they shouldn't.
    Relies on Document nodes from continuity_planner containing 'does NOT know' lines.
    """
    violations = []
    docs = store.get_nodes_by_type("Document")
    planner_doc = next((d for d in docs if "continuity" in d.get("agent", "")), None)
    if not planner_doc:
        return violations

    content = planner_doc.get("content", "")
    text_lower = scene_text.lower()

    # Extract lines like: "Character X does NOT know Y"
    for match in re.finditer(
        r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+does\s+NOT\s+know\s+(.+?)(?:\n|$)", content
    ):
        char_name = match.group(1).strip()
        unknown_fact = match.group(2).strip().lower()
        # Check if this character is in the scene and seems to reference the unknown fact
        if char_name.lower() in text_lower and unknown_fact in text_lower:
            violations.append(
                f"Character '{char_name}' references '{unknown_fact}' "
                f"but the continuity plan says they do NOT know this yet"
            )
    return violations


def _near(location: str, term: str, text: str, window: int = 200) -> bool:
    """True if term appears within window characters of the location name in text."""
    idx = text.find(location.lower())
    if idx == -1:
        return False
    region = text[max(0, idx - window): idx + len(location) + window]
    return term in region
