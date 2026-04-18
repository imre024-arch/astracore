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
    except PromptBudgetError:
        raise
    except ToolLimitExceeded as e:
        logger.warning("[%s] ToolLimitExceeded: %s", agent_name, e)

    return context


def execute_action(action: str, context: dict) -> dict:
    if action == "generate":
        return context

    if action == "validate_skills":
        context["skill_update_rejected"] = False
        return context

    if action == "update_skills":
        if context.get("skill_update_rejected"):
            logger.info("[update_skills] Skipped — validation rejected this iteration")
            context["skill_update_rejected"] = False
            return context

        from core.skill_system import update_skills

        feedback = context.get("mentor_output", {})
        if not isinstance(feedback, dict):
            logger.warning("[update_skills] mentor_output is not a dict — skipping")
            return context

        try:
            update_skills(feedback, "writer")
            logger.info("[update_skills] Skills updated for writer")
        except SkillValidationError as e:
            logger.warning("[update_skills] Rejected: %s", e)
            context["skill_update_rejected"] = True
            context["rejected_count"] = context.get("rejected_count", 0) + 1

        return context

    if action == "optional_debate":
        from loaders.tool_loader import execute_tool

        try:
            result = execute_tool("debate_tool", {}, context)
            context["debate_output"] = result
            context["last_output"] = result
        except Exception as e:
            logger.warning("[optional_debate] Skipped: %s", e)

        return context

    logger.warning("Unknown action: '%s'", action)
    return context
