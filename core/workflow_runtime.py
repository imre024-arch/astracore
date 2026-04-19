import logging

from core.exceptions import PromptBudgetError, SkillValidationError, ToolLimitExceeded

logger = logging.getLogger(__name__)


def execute_workflow(workflow: dict, context: dict) -> dict:
    logger.info("Executing workflow: %s", workflow.get("name"))
    for step in workflow.get("steps", []):
        context = execute_step(step, context)
    return context


def execute_step(step: dict, context: dict) -> dict:
    if "loop" in step:
        from core.loop_engine import execute_loop
        return execute_loop(step["loop"], context)

    if "set" in step:
        context.update(step["set"])
        return context

    if "agent" in step:
        return _run_agent_step(step["agent"], context)

    if "action" in step:
        return execute_action(step["action"], context)

    logger.warning("Unknown step format: %s", step)
    return context


def _run_agent_step(agent_name: str, context: dict) -> dict:
    from loaders.agent_loader import load_agent

    agent = load_agent(agent_name)
    input_data = context.get("last_output") or context.get("input", "")

    try:
        result = agent.run(input_data, context)
        if isinstance(result, dict):
            context[f"{agent_name}_output"] = result
            context["last_output"] = str(result)
        else:
            context[f"{agent_name}_output"] = result
            context["last_output"] = result
        context["last_agent"] = agent_name
    except PromptBudgetError as e:
        logger.warning("[%s] PromptBudgetError, skipping step: %s", agent_name, e)
    except ToolLimitExceeded as e:
        logger.warning("[%s] ToolLimitExceeded: %s", agent_name, e)
    except ValueError as e:
        logger.warning("[%s] Bad LLM response, skipping step: %s", agent_name, e)

    return context


def execute_action(action: str, context: dict) -> dict:
    actions = {
        "generate":             _action_generate,
        "validate_skills":      _action_validate_skills,
        "update_skills":        _action_update_skills,
        "optional_debate":      _action_optional_debate,
        "publish_to_wordpress": _action_publish_to_wordpress,
        "save_to_graph":        _action_save_to_graph,
        "export_knowledge":     _action_export_knowledge,
        "build_context":        _action_build_context,
        "continuity_check":     _action_continuity_check,
        "load_prework_doc":     _action_load_prework_doc,
        "update_context":       _action_update_context,
    }
    handler = actions.get(action)
    if handler:
        return handler(context)

    logger.warning("Unknown action: '%s'", action)
    return context


def _action_generate(context: dict) -> dict:
    return context


def _action_validate_skills(context: dict) -> dict:
    context["skill_update_rejected"] = False
    return context


def _action_update_skills(context: dict) -> dict:
    if context.get("skill_update_rejected"):
        logger.info("[update_skills] Skipped — validation rejected this iteration")
        context["skill_update_rejected"] = False
        return context

    from core.skill_system import update_skills

    feedback_text = context.get("mentor_output", "")
    if not feedback_text or not isinstance(feedback_text, str):
        logger.warning("[update_skills] mentor_output is empty or not text — skipping")
        return context

    target = context.get("target_agent", "writer")
    try:
        update_skills(feedback_text, target)
        logger.info("[update_skills] Skills updated for %s", target)
    except SkillValidationError as e:
        logger.warning("[update_skills] Rejected: %s", e)
        context["skill_update_rejected"] = True
        context["rejected_count"] = context.get("rejected_count", 0) + 1

    return context


def _action_optional_debate(context: dict) -> dict:
    from loaders.tool_loader import execute_tool

    try:
        result = execute_tool("debate_tool", {}, context)
        context["debate_output"] = result
        context["last_output"] = result
    except Exception as e:
        logger.warning("[optional_debate] Skipped: %s", e)

    return context


def _action_publish_to_wordpress(context: dict) -> dict:
    from loaders.tool_loader import execute_tool

    try:
        result = execute_tool(
            "wordpress_publish_tool",
            {"content": context.get("publisher_output", context.get("last_output", ""))},
            context,
        )
        context["wordpress_result"] = result
        context["last_output"] = result
        logger.info("[publish_to_wordpress] %s", result)
    except Exception as e:
        logger.error("[publish_to_wordpress] Failed: %s", e)

    return context


def _action_save_to_graph(context: dict) -> dict:
    import os
    from knowledge.graph_store import GraphStore
    from knowledge.graph_writer import write_to_graph

    story_id = os.getenv("STORY_ID", "story_001")
    text = context.get("last_output", "")
    agent_name = context.get("last_agent", "unknown")

    if not text:
        logger.warning("[save_to_graph] No output to save (last_agent=%s)", agent_name)
        return context

    store = GraphStore(story_id)
    try:
        count = write_to_graph(text, agent_name, store)
        logger.info("[save_to_graph] Wrote %d item(s) for agent '%s'", count, agent_name)
        context["graph_items_written"] = context.get("graph_items_written", 0) + count
    except Exception as e:
        logger.error("[save_to_graph] Failed: %s", e)
    finally:
        store.close()

    return context


def _action_export_knowledge(context: dict) -> dict:
    import os
    from pathlib import Path
    from knowledge.graph_store import GraphStore
    from knowledge.export_engine import ExportEngine

    story_id = os.getenv("STORY_ID", "story_001")
    agents_path = Path(os.getenv("AGENTS_REPO_PATH", "."))
    out_dir = agents_path / "knowledge" / story_id
    out_dir.mkdir(parents=True, exist_ok=True)

    store = GraphStore(story_id)
    try:
        engine = ExportEngine(store)
        engine.to_json(str(out_dir / "graph.json"))
        engine.to_yaml(str(out_dir / "graph.yaml"))
        engine.to_markdown(str(out_dir / "story_bible.md"))
        logger.info("[export_knowledge] Exported to %s", out_dir)
        context["knowledge_exported"] = str(out_dir)
    except Exception as e:
        logger.error("[export_knowledge] Failed: %s", e)
    finally:
        store.close()

    return context


def _action_build_context(context: dict) -> dict:
    import os
    from knowledge.context_orchestrator import build_context

    story_id = os.getenv("STORY_ID", "story_001")
    skill = context.get("skill", "writer")
    scene_id = context.get("scene_id")

    try:
        pack = build_context(skill=skill, story_id=story_id, scene_id=scene_id)
        context["skill_context"] = pack
        # Format as readable text so writing agents can consume it via {context}
        context["last_output"] = _format_context_pack(pack)
        logger.info("[build_context] Built context pack for skill '%s'", skill)
    except Exception as e:
        logger.error("[build_context] Failed: %s", e)

    return context


def _action_continuity_check(context: dict) -> dict:
    import os
    from knowledge.continuity_guard import check_consistency

    story_id = os.getenv("STORY_ID", "story_001")
    scene_id = context.get("scene_id", "unknown_scene")
    scene_text = context.get("last_output", "")

    if not scene_text:
        logger.warning("[continuity_check] No scene text to check")
        return context

    try:
        violations = check_consistency(scene_text, scene_id, story_id)
        context["continuity_violations"] = violations
        if violations:
            context["continuity_warning"] = "\n".join(f"- {v}" for v in violations)
    except Exception as e:
        logger.error("[continuity_check] Failed: %s", e)

    return context


def _action_update_context(context: dict) -> dict:
    """Like build_context but preserves last_output — use between chained writing agents."""
    import os
    from knowledge.context_orchestrator import build_context

    story_id = os.getenv("STORY_ID", "story_001")
    skill = context.get("skill", "writer")
    scene_id = context.get("scene_id")

    try:
        pack = build_context(skill=skill, story_id=story_id, scene_id=scene_id)
        context["skill_context"] = pack
        logger.info("[update_context] Updated context pack for skill '%s'", skill)
    except Exception as e:
        logger.error("[update_context] Failed: %s", e)

    return context


def _action_load_prework_doc(context: dict) -> dict:
    import os
    from knowledge.graph_store import GraphStore

    story_id = os.getenv("STORY_ID", "story_001")
    target = context.get("target_agent")
    if not target:
        logger.warning("[load_prework_doc] target_agent not set in context — skipping")
        return context

    agent_key = target.replace("/", "_").replace("-", "_").lower()
    doc_id = f"doc_{agent_key}"

    store = GraphStore(story_id)
    try:
        node = store.get_node(doc_id)
        if node:
            content = node.get("content", "")
            context["last_output"] = content
            logger.info("[load_prework_doc] Loaded doc '%s' (%d chars)", doc_id, len(content))
        else:
            logger.warning("[load_prework_doc] No document found for id '%s'", doc_id)
    except Exception as e:
        logger.error("[load_prework_doc] Failed: %s", e)
    finally:
        store.close()

    return context


def _format_context_pack(pack: dict) -> str:
    lines = []
    for key, value in pack.items():
        if not value:
            continue
        label = key.replace("_", " ").upper()
        if isinstance(value, list):
            lines.append(f"{label}:")
            for item in value:
                lines.append(f"  - {item}")
        elif isinstance(value, dict):
            lines.append(f"{label}:")
            for k, v in value.items():
                lines.append(f"  {k}: {v}")
        else:
            lines.append(f"{label}: {value}")
    return "\n".join(lines)
