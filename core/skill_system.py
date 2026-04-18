import json
import logging
import os
import re
from pathlib import Path

from core.exceptions import SkillValidationError
from persistence.storage import load_yaml, save_yaml

logger = logging.getLogger(__name__)


def validate_skill_update(feedback: dict, agent_name: str) -> None:
    from loaders.agent_loader import load_agent

    threshold = float(os.getenv("SKILL_VALIDATION_THRESHOLD", "0.6"))
    validator = load_agent("critique_editorial")

    validation_input = (
        f"Rate the following proposed skill update for agent '{agent_name}'. "
        f"Score 0.0-1.0. Reject (score < {threshold}) if rules are vague, contradictory, "
        f"or would degrade output quality.\n\n"
        f"Proposed update:\n"
        f"new_rules: {feedback.get('new_rules', [])}\n"
        f"failures: {feedback.get('failures', [])}\n\n"
        f'Respond with JSON only: {{"score": float, "reason": string}}'
    )

    raw = validator.llm.generate(validation_input)
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        logger.warning("[skill_validation] Could not parse validation response — allowing update")
        return

    result = json.loads(match.group())
    score = float(result.get("score", 1.0))
    reason = result.get("reason", "")

    logger.info("[skill_validation] %s score=%.2f: %s", agent_name, score, reason)

    if score < threshold:
        raise SkillValidationError(f"Rejected (score={score:.2f}): {reason}")


def update_skills(feedback: dict, agent_name: str) -> None:
    agents_path = Path(os.getenv("AGENTS_REPO_PATH"))
    skills_file = agents_path / "agents" / agent_name / "skills.yaml"

    validate_skill_update(feedback, agent_name)

    skills = load_yaml(str(skills_file))
    skills.setdefault("rules", [])
    skills.setdefault("failure_patterns", [])

    skills["rules"].extend(feedback.get("new_rules", []))
    skills["failure_patterns"].extend(feedback.get("failures", []))
    skills["version"] = round(skills.get("version", 1.0) + 0.1, 1)

    save_yaml(str(skills_file), skills)
    logger.info("Skills saved for %s at v%.1f", agent_name, skills["version"])

    if os.getenv("GIT_COMMIT_SKILLS", "true").lower() == "true":
        from persistence.git_manager import commit
        commit(agent_name, skills["version"], str(agents_path))
