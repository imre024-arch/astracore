class PromptBudgetError(Exception):
    """Prompt cannot be reduced to fit max_prompt_tokens after all truncation steps."""


class SkillValidationError(Exception):
    """Proposed skill update rejected by critique_editorial validation gate."""


class ToolLimitExceeded(Exception):
    """Agent exceeded max_tool_calls_per_run for a single run() invocation."""
