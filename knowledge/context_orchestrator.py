import logging
from typing import Optional

logger = logging.getLogger(__name__)


def build_context(skill: str, story_id: str, scene_id: Optional[str] = None) -> dict:
    from knowledge.graph_store import GraphStore
    store = GraphStore(story_id)
    try:
        global_ctx = _global(scene_id, store)
        skill_ctx = _dispatch(skill, scene_id, store)
        return {**global_ctx, **skill_ctx}
    finally:
        store.close()


# ---------------------------------------------------------------------------
# Global context — injected into every skill pack
# ---------------------------------------------------------------------------

def _global(scene_id: str | None, store) -> dict:
    story = _first(store.get_nodes_by_type("Story"))
    scene = store.get_node(scene_id) if scene_id else {}
    return {
        "story_summary":       story.get("premise", ""),
        "current_scene_goal":  scene.get("goal", ""),
        "plot_point":          scene.get("plot_position", ""),
        "emotional_curve":     scene.get("emotional_curve", ""),
        "tone_style":          story.get("tone", ""),
        "constraints":         story.get("style_notes", ""),
    }


# ---------------------------------------------------------------------------
# Skill-specific builders
# ---------------------------------------------------------------------------

def _dispatch(skill: str, scene_id: str | None, store) -> dict:
    builders = {
        "dialogue":              _dialogue,
        "plot_design":           _plot_design,
        "worldbuilding":         _worldbuilding,
        "character_profiling":   _character_profiling,
        "philosophical":         _philosophical,
        "tension_planner":       _tension_planner,
        "cliche_avoidance":      _cliche_avoidance,
        "style_voice":           _style_voice,
        "pacing":                _pacing,
        "critique":              _critique,
        "writer":                _writer,
        # Writing subagent skills
        "orchestrator":          _orchestrator,
        "architect":             _architect,
        "scene_weaver":          _scene_weaver,
        "dialogue_artist":       _dialogue_artist,
        "emotional_specialist":  _emotional_specialist,
        "pacing_chapter":        _pacing_chapter,
        "style_consistency":     _style_consistency,
        "consistency_manager":   _consistency_manager,
    }
    builder = builders.get(skill, _writer)
    logger.debug("[ContextOrchestrator] building context for skill '%s'", skill)
    return builder(scene_id, store)


def _dialogue(scene_id: str | None, store) -> dict:
    scene = store.get_node(scene_id) if scene_id else {}
    participants = []
    if scene_id:
        chars = store.get_neighbors(scene_id, rel_type="PARTICIPATES_IN", direction="in")
        for c in chars:
            participants.append({
                "name":               c.get("name", ""),
                "personality":        c.get("personality", ""),
                "current_emotion":    c.get("arc_state", ""),
                "motivation":         c.get("desires", ""),
                "relationship_to_others": _rel_summary(c["id"], store),
            })
    return {
        "scene_goal":    scene.get("goal", ""),
        "participants":  participants,
        "conflict":      scene.get("conflict", ""),
        "pacing_level":  scene.get("pacing_level", "medium"),
        "recent_events": _prev_scene_goal(scene_id, store),
    }


def _plot_design(scene_id: str | None, store) -> dict:
    story = _first(store.get_nodes_by_type("Story"))
    scenes = store.get_nodes_by_type("Scene")
    chars = store.get_nodes_by_type("Character")
    return {
        "core_idea":        story.get("premise", ""),
        "genre":            story.get("genre", ""),
        "themes":           story.get("themes", ""),
        "major_characters": [c.get("name", "") for c in chars if c.get("role") in ("protagonist", "antagonist")],
        "story_scope":      story.get("scope", "novel"),
        "target_structure": story.get("structure_model", "3-act"),
        "scene_count":      len(scenes),
    }


def _worldbuilding(scene_id: str | None, store) -> dict:
    story = _first(store.get_nodes_by_type("Story"))
    locs = store.get_nodes_by_type("Location")
    factions = store.get_nodes_by_type("Faction")
    return {
        "genre":       story.get("genre", ""),
        "themes":      story.get("themes", ""),
        "locations":   [{"name": l.get("name", ""), "atmosphere": l.get("atmosphere", "")} for l in locs],
        "factions":    [{"name": f.get("name", ""), "ideology": f.get("ideology", "")} for f in factions],
        "world_rules": story.get("world_rules", ""),
    }


def _character_profiling(scene_id: str | None, store) -> dict:
    story = _first(store.get_nodes_by_type("Story"))
    chars = store.get_nodes_by_type("Character")
    return {
        "world_context":   story.get("premise", ""),
        "theme_alignment": story.get("themes", ""),
        "characters": [
            {
                "name":          c.get("name", ""),
                "role":          c.get("role", ""),
                "arc_type":      c.get("arc_type", ""),
                "arc_state":     c.get("arc_state", ""),
                "fears":         c.get("fears", ""),
                "desires":       c.get("desires", ""),
                "relationships": _rel_summary(c["id"], store),
            }
            for c in chars
        ],
    }


def _philosophical(scene_id: str | None, store) -> dict:
    story = _first(store.get_nodes_by_type("Story"))
    concepts = store.get_nodes_by_type("Concept")
    chars = store.get_nodes_by_type("Character")
    return {
        "themes":             story.get("themes", ""),
        "world_assumptions":  story.get("premise", ""),
        "character_dilemmas": [c.get("description", c.get("name", "")) for c in concepts if c.get("concept_type") == "moral_question"],
        "tone":               story.get("tone", ""),
        "symbols":            [c.get("name", "") for c in concepts if c.get("concept_type") == "symbol"],
        "character_positions": [f"{c.get('name', '')}: {c.get('personality', '')}" for c in chars],
    }


def _tension_planner(scene_id: str | None, store) -> dict:
    scene = store.get_node(scene_id) if scene_id else {}
    events = store.get_nodes_by_type("Event")
    return {
        "scene_goal":            scene.get("goal", ""),
        "stakes":                scene.get("stakes", ""),
        "conflict":              scene.get("conflict", ""),
        "current_tension_level": scene.get("tension_level", "5"),
        "event_chain":           [e.get("name", "") for e in events],
    }


def _cliche_avoidance(scene_id: str | None, store) -> dict:
    scene = store.get_node(scene_id) if scene_id else {}
    story = _first(store.get_nodes_by_type("Story"))
    events = store.get_nodes_by_type("Event")
    chars = store.get_nodes_by_type("Character")
    return {
        "scene_summary":    scene.get("goal", ""),
        "key_events":       [e.get("name", "") for e in events[:5]],
        "character_roles":  [f"{c.get('name', '')} ({c.get('role', '')})" for c in chars],
        "genre":            story.get("genre", ""),
    }


def _style_voice(scene_id: str | None, store) -> dict:
    story = _first(store.get_nodes_by_type("Story"))
    return {
        "target_style":  story.get("style_direction", ""),
        "tone":          story.get("tone", ""),
        "audience":      story.get("target_audience", ""),
        "style_rules":   story.get("style_notes", ""),
    }


def _pacing(scene_id: str | None, store) -> dict:
    scene = store.get_node(scene_id) if scene_id else {}
    all_scenes = store.get_nodes_by_type("Scene")
    pos = next((i for i, s in enumerate(all_scenes) if s.get("id") == scene_id), 0)
    total = len(all_scenes)
    return {
        "tension_level":  scene.get("tension_level", "5"),
        "plot_position":  scene.get("plot_position", "mid"),
        "scene_index":    pos,
        "total_scenes":   total,
        "relative_pos":   f"{pos + 1} of {total}" if total else "unknown",
    }


def _critique(scene_id: str | None, store) -> dict:
    scene = store.get_node(scene_id) if scene_id else {}
    story = _first(store.get_nodes_by_type("Story"))
    return {
        "scene_goal":       scene.get("goal", ""),
        "plot_context":     story.get("premise", ""),
        "expected_tone":    story.get("tone", ""),
        "character_intent": scene.get("conflict", ""),
    }


def _writer(scene_id: str | None, store) -> dict:
    story = _first(store.get_nodes_by_type("Story"))
    chars = store.get_nodes_by_type("Character")
    locs = store.get_nodes_by_type("Location")
    scene = store.get_node(scene_id) if scene_id else {}
    scenes = store.get_nodes_by_type("Scene")
    concepts = store.get_nodes_by_type("Concept")

    loc_names = ", ".join(l.get("name", "") for l in locs if l.get("name"))
    world_summary = f"Genre: {story.get('genre', '')}. Tone: {story.get('tone', '')}."
    if loc_names:
        world_summary += f" Locations: {loc_names}."

    return {
        "world_summary":      world_summary,
        "character_profiles": [
            f"{c.get('name', '')} ({c.get('role', '')}): {c.get('personality', '')}"
            for c in chars
        ],
        "current_scene_plan": (
            f"Goal: {scene.get('goal', '')}. "
            f"Conflict: {scene.get('conflict', '')}. "
            f"Position: {scene.get('plot_position', '')}."
        ),
        "style_rules":        story.get("style_notes", ""),
        "active_constraints": [
            c.get("description", c.get("name", ""))
            for c in concepts if c.get("concept_type") == "theme"
        ],
        "scene_outline": [
            f"Scene {s.get('id', i)}: {s.get('goal', '')}"
            for i, s in enumerate(scenes)
        ],
    }


# ---------------------------------------------------------------------------
# Writing subagent skill builders
# ---------------------------------------------------------------------------

def _orchestrator(scene_id: Optional[str], store) -> dict:
    story = _first(store.get_nodes_by_type("Story"))
    chars = store.get_nodes_by_type("Character")
    scene = store.get_node(scene_id) if scene_id else {}

    # Load the last finished scene's prose from the graph (written by consistency_manager)
    prev_doc = store.get_node("doc_writing_consistency_manager")
    prev_prose = prev_doc.get("content", "") if prev_doc else ""
    # Extract last ~2000 words to give the Orchestrator the scene ending verbatim
    prev_words = prev_prose.split()
    last_2000 = " ".join(prev_words[-2000:]) if len(prev_words) > 2000 else prev_prose

    # Find the previous scene goal via LEADS_TO edge
    prev_scene_goal = _prev_scene_goal(scene_id, store)

    return {
        "previous_scene_prose":    last_2000 or "None — this is the opening scene.",
        "previous_scene_goal":     prev_scene_goal,
        "current_scene_goal":      scene.get("goal", ""),
        "current_scene_conflict":  scene.get("conflict", ""),
        "current_scene_stakes":    scene.get("stakes", ""),
        "story_premise":           story.get("premise", ""),
        "characters": [
            {
                "name":      c.get("name", ""),
                "arc_state": c.get("arc_state", ""),
                "desires":   c.get("desires", ""),
                "fears":     c.get("fears", ""),
            }
            for c in chars
        ],
    }


def _pacing_chapter(scene_id: Optional[str], store) -> dict:
    story = _first(store.get_nodes_by_type("Story"))
    scenes = store.get_nodes_by_type("Scene")
    scene = store.get_node(scene_id) if scene_id else {}

    # Count scenes since the last chapter break by scanning LEADS_TO chain
    # Approximation: count all written Document nodes as a proxy for written scenes
    written_docs = [
        n for n in store.get_nodes_by_type("Document")
        if n.get("agent", "").startswith("writing/consistency_manager")
    ]

    return {
        "genre":                story.get("genre", ""),
        "tone":                 story.get("tone", ""),
        "total_scene_count":    len(scenes),
        "written_scene_count":  len(written_docs),
        "current_tension_level": scene.get("tension_level", "5"),
        "plot_position":        scene.get("plot_position", "mid"),
        "emotional_curve":      scene.get("emotional_curve", ""),
        "story_structure_model": story.get("structure_model", "3-act"),
    }


def _style_consistency(scene_id: Optional[str], store) -> dict:
    story = _first(store.get_nodes_by_type("Story"))

    # Load the writing style reference from the story bible
    style_doc = store.get_node("doc_prework_story_foundation")
    style_excerpt = ""
    if style_doc:
        content = style_doc.get("content", "")
        # Extract first 800 words as style reference — contains tone and style notes
        words = content.split()
        style_excerpt = " ".join(words[:800])

    return {
        "target_style":         story.get("style_direction", ""),
        "tone":                 story.get("tone", ""),
        "style_notes":          story.get("style_notes", ""),
        "narrative_pov":        story.get("narrative_pov", "third-person limited"),
        "narrative_tense":      story.get("narrative_tense", "past"),
        "style_reference":      style_excerpt,
    }


def _architect(scene_id: Optional[str], store) -> dict:
    story = _first(store.get_nodes_by_type("Story"))
    chars = store.get_nodes_by_type("Character")
    scenes = store.get_nodes_by_type("Scene")
    locs = store.get_nodes_by_type("Location")
    scene = store.get_node(scene_id) if scene_id else {}
    return {
        "genre":            story.get("genre", ""),
        "tone":             story.get("tone", ""),
        "world_rules":      story.get("world_rules", ""),
        "structure_model":  story.get("structure_model", "3-act"),
        "characters": [
            {
                "name":      c.get("name", ""),
                "role":      c.get("role", ""),
                "arc_state": c.get("arc_state", ""),
                "desires":   c.get("desires", ""),
                "fears":     c.get("fears", ""),
            }
            for c in chars
        ],
        "locations":        [{"name": l.get("name", ""), "atmosphere": l.get("atmosphere", "")} for l in locs],
        "scene_plan": {
            "goal":         scene.get("goal", ""),
            "conflict":     scene.get("conflict", ""),
            "stakes":       scene.get("stakes", ""),
            "tension_level": scene.get("tension_level", "5"),
            "plot_position": scene.get("plot_position", ""),
            "emotional_curve": scene.get("emotional_curve", ""),
        },
        "scene_outline": [
            f"Scene {s.get('id', i)}: {s.get('goal', '')}" for i, s in enumerate(scenes)
        ],
        "previous_scene_goal": _prev_scene_goal(scene_id, store),
    }


def _scene_weaver(scene_id: Optional[str], store) -> dict:
    story = _first(store.get_nodes_by_type("Story"))
    chars = store.get_nodes_by_type("Character")
    locs = store.get_nodes_by_type("Location")
    return {
        "world_summary": (
            f"Genre: {story.get('genre', '')}. "
            f"Tone: {story.get('tone', '')}. "
            f"Rules: {story.get('world_rules', '')}."
        ),
        "style_notes":  story.get("style_notes", ""),
        "character_profiles": [
            {
                "name":        c.get("name", ""),
                "personality": c.get("personality", ""),
                "arc_state":   c.get("arc_state", ""),
                "fears":       c.get("fears", ""),
                "desires":     c.get("desires", ""),
            }
            for c in chars
        ],
        "locations": [
            {"name": l.get("name", ""), "atmosphere": l.get("atmosphere", ""), "rules": l.get("rules", "")}
            for l in locs
        ],
    }


def _dialogue_artist(scene_id: Optional[str], store) -> dict:
    chars = store.get_nodes_by_type("Character")
    scene = store.get_node(scene_id) if scene_id else {}
    return {
        "scene_conflict": scene.get("conflict", ""),
        "character_profiles": [
            {
                "name":         c.get("name", ""),
                "personality":  c.get("personality", ""),
                "arc_state":    c.get("arc_state", ""),
                "voice_notes":  c.get("voice_notes", ""),
                "education":    c.get("education", ""),
                "speech_style": c.get("speech_style", ""),
                "relationships": _rel_summary(c["id"], store),
            }
            for c in chars
        ],
    }


def _emotional_specialist(scene_id: Optional[str], store) -> dict:
    scene = store.get_node(scene_id) if scene_id else {}
    story = _first(store.get_nodes_by_type("Story"))
    return {
        "scene_goal":       scene.get("goal", ""),
        "stakes":           scene.get("stakes", ""),
        "tension_level":    scene.get("tension_level", "5"),
        "emotional_curve":  scene.get("emotional_curve", ""),
        "plot_position":    scene.get("plot_position", ""),
        "genre":            story.get("genre", ""),
        "tone":             story.get("tone", ""),
        "previous_scene":   _prev_scene_goal(scene_id, store),
    }


def _consistency_manager(scene_id: Optional[str], store) -> dict:
    chars = store.get_nodes_by_type("Character")
    locs = store.get_nodes_by_type("Location")
    # Load continuity_planner document for knowledge-state rules
    continuity_doc = store.get_node("doc_prework_continuity_planner")
    continuity_text = continuity_doc.get("content", "") if continuity_doc else ""
    return {
        "character_profiles": [
            {
                "name":          c.get("name", ""),
                "arc_state":     c.get("arc_state", ""),
                "physical_desc": c.get("physical_description", ""),
                "known_facts":   c.get("known_facts", ""),
                "relationships": _rel_summary(c["id"], store),
            }
            for c in chars
        ],
        "world_context": [
            {"name": l.get("name", ""), "rules": l.get("rules", ""), "atmosphere": l.get("atmosphere", "")}
            for l in locs
        ],
        "continuity_data": continuity_text,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _first(nodes: list[dict]) -> dict:
    return nodes[0] if nodes else {}


def _rel_summary(node_id: str, store) -> str:
    neighbors = store.get_neighbors(node_id, direction="out")
    if not neighbors:
        return ""
    return ", ".join(n.get("name", n["id"]) for n in neighbors[:5])


def _prev_scene_goal(scene_id: str | None, store) -> str:
    if not scene_id:
        return ""
    prev = store.get_neighbors(scene_id, rel_type="LEADS_TO", direction="in")
    return prev[0].get("goal", "") if prev else ""
