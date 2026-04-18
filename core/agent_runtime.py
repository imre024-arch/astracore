import logging
import os

from core.exceptions import ToolLimitExceeded

logger = logging.getLogger(__name__)

DEFAULT_MAX_TOOL_CALLS = 5


class AgentRuntime:
    def __init__(self, config: dict, skills: dict, llm):
        self.config = config
        self.skills = skills
        self.llm = llm
        self._tool_call_count = 0

        override = os.getenv("MAX_TOOL_CALLS_OVERRIDE")
        if override is not None:
            self._max_tool_calls = int(override)
        else:
            self._max_tool_calls = config.get("limits", {}).get(
                "max_tool_calls_per_run", DEFAULT_MAX_TOOL_CALLS
            )

    def run(self, input_data: str, context: dict | None = None) -> str | dict:
        from execution.prompt_builder import build_prompt
        from execution.response_parser import parse_response

        self._tool_call_count = 0
        prompt = build_prompt(self.config, self.skills, input_data, context or {})
        raw = self.llm.generate(prompt, system=self.config.get("system"))
        return parse_response(raw, self.config["output_format"])

    def call_tool(self, tool_name: str, params: dict, context: dict) -> str:
        from loaders.tool_loader import execute_tool

        if self._tool_call_count >= self._max_tool_calls:
            raise ToolLimitExceeded(
                f"Agent '{self.config['name']}' reached max_tool_calls_per_run "
                f"({self._max_tool_calls}). Skipping tool '{tool_name}'."
            )
        self._tool_call_count += 1
        return execute_tool(tool_name, params, context)
