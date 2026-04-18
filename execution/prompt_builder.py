import logging
import os
import re
from pathlib import Path

from core.exceptions import PromptBudgetError

logger = logging.getLogger(__name__)

DEFAULT_MAX_TOKENS = 2048


def _count_tokens(text: str) -> int:
    return int(len(text.split()) * 1.3)


def build_prompt(
    config: dict,
    skills: dict,
    input_data: str,
    context: dict | None,
) -> str:
    agents_path = Path(os.getenv("AGENTS_REPO_PATH"))
    prompt_file = agents_path / "agents" / config["name"] / "prompt.txt"
    template = prompt_file.read_text(encoding="utf-8")

    max_tokens = config.get("limits", {}).get("max_prompt_tokens", DEFAULT_MAX_TOKENS)

    skill_list = list(skills.get("skills", []))
    rule_list = list(skills.get("rules", []))
    failure_list = list(skills.get("failure_patterns", []))
    ctx_entries = list((context or {}).items())

    def assemble(s_list, r_list, c_list):
        skills_str = "\n".join(f"- {s}" for s in s_list) or "(none)"
        rules_str = "\n".join(f"- {r}" for r in r_list) or "(none)"
        failures_str = "\n".join(f"- {f}" for f in failure_list) or "(none)"
        ctx_str = "\n".join(f"{k}: {v}" for k, v in c_list) or "(empty)"
        substitutions = {
            "input": input_data,
            "skills": skills_str,
            "rules": rules_str,
            "failure_patterns": failures_str,
            "context": ctx_str,
        }
        # Regex replacement so JSON braces in prompt templates are left untouched.
        return re.sub(
            r"\{(" + "|".join(substitutions.keys()) + r")\}",
            lambda m: substitutions[m.group(1)],
            template,
        )

    prompt = assemble(skill_list, rule_list, ctx_entries)
    original_tokens = _count_tokens(prompt)

    if original_tokens <= max_tokens:
        return prompt

    # Step 1: trim context to last 2 entries
    ctx_entries = ctx_entries[-2:]
    prompt = assemble(skill_list, rule_list, ctx_entries)
    if _count_tokens(prompt) <= max_tokens:
        logger.warning(
            "[%s] prompt truncated: %d → %d tokens (context trimmed)",
            config["name"], original_tokens, _count_tokens(prompt),
        )
        return prompt

    # Step 2: trim rules to first 5
    rule_list = rule_list[:5]
    prompt = assemble(skill_list, rule_list, ctx_entries)
    if _count_tokens(prompt) <= max_tokens:
        logger.warning(
            "[%s] prompt truncated: %d → %d tokens (rules trimmed)",
            config["name"], original_tokens, _count_tokens(prompt),
        )
        return prompt

    # Step 3: trim skills to first 3
    skill_list = skill_list[:3]
    prompt = assemble(skill_list, rule_list, ctx_entries)
    if _count_tokens(prompt) <= max_tokens:
        logger.warning(
            "[%s] prompt truncated: %d → %d tokens (skills trimmed)",
            config["name"], original_tokens, _count_tokens(prompt),
        )
        return prompt

    raise PromptBudgetError(
        f"Agent '{config['name']}' prompt exceeds {max_tokens} tokens "
        f"even after all truncation steps."
    )
