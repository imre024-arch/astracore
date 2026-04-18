import logging

from config.settings import validate
from core.workflow_runtime import execute_workflow

logger = logging.getLogger(__name__)


class Engine:
    def __init__(self):
        logging.basicConfig(
            level=logging.INFO,
            format="%(levelname)s %(name)s: %(message)s",
        )
        validate()

    def run(self, workflow: dict, initial_input: str = "") -> dict:
        context = {
            "input": initial_input,
            "rejected_count": 0,
        }
        logger.info("Starting workflow: %s", workflow.get("name"))
        result = execute_workflow(workflow, context)
        logger.info(
            "Workflow complete. Rejected skill updates: %d",
            result.get("rejected_count", 0),
        )
        return result
