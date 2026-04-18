import logging

logger = logging.getLogger(__name__)


def execute_loop(loop_config: dict, context: dict) -> dict:
    from core.workflow_runtime import execute_step

    count = int(loop_config["count"])
    logger.info("Starting loop: %d iterations", count)

    for i in range(count):
        logger.info("Loop iteration %d/%d", i + 1, count)
        for step in loop_config.get("steps", []):
            context = execute_step(step, context)

    return context
