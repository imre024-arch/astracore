import logging
import os
import re
from pathlib import Path

from core.exceptions import SkillValidationError
from persistence.storage import load_yaml, save_yaml

logger = logging.getLogger(__name__)


def _parse_mentor_text(text: str) -> dict:
    """Extract new_rules and failures from mentor plain-text output."""
    new_rules: list[str] = []
    failures: list[str] = []
    current = None

    for line in text.splitlines():
        stripped = line.strip()
        upper = stripped.upper()

        if upper.startswith("NEW_RULES") or upper.startswith("RULES"):
            current = "rules"
        elif upper.startswith("FAIL"):
            current = "failures"
        elif stripped.startswith("-") or stripped.startswith("*"):
            item = stripped.lstrip("-* ").strip()
            if item:
                if current == "rules":
                    new_rules.append(item)
                elif current == "failures":
                    failures.append(item)

    return {"new_rules": new_rules, "failures": failures}


def _parse_validation_score(text: str) -> float:
    """Extract the first float in [0, 1] from a validation response."""
    matches = re.findall(r"\b(0(?:\.\d+)?|1(?:\.0+)?)\b", text)
    if matches:
        return float(matches[0])
    return 1.0  # allow if no score found


def validate_skill_update(feedback_text: str, agent_name: str) -> None:
    from loaders.agent_loader import load_agent

    threshold = float(os.getenv("SKILL_VALIDATION_THRESHOLD", "0.6"))
    validator = load_agent("critique_editorial")

    prompt = (
        f"Rate the following proposed skill update for agent '{agent_name}'. "
        f"Output your score as a decimal between 0.0 and 1.0 on the very first line "
        f"(e.g. '0.85'), then explain your reasoning. "
        f"Reject (score < {threshold}) if rules are vague, contradictory, or would degrade quality.\n\n"
        f"Proposed update:\n{feedback_text}"
    )

    raw = validator.llm.generate(prompt)
    score = _parse_validation_score(raw)
    reason = raw.strip().split("\n", 1)[-1].strip()

    logger.info("[skill_validation] %s score=%.2f: %s", agent_name, score, reason[:120])

    if score < threshold:
        raise SkillValidationError(f"Rejected (score={score:.2f}): {reason[:200]}")


def update_skills(feedback_text: str, agent_name: str) -> None:
    agents_path = Path(os.getenv("AGENTS_REPO_PATH"))
    skills_file = agents_path / "agents" / agent_name / "skills.yaml"

    validate_skill_update(feedback_text, agent_name)

    feedback = _parse_mentor_text(feedback_text)
    new_rules = feedback.get("new_rules", [])
    failures = feedback.get("failures", [])

    if not new_rules and not failures:
        logger.warning("[update_skills] No rules or failures parsed from mentor output — skipping")
        return

    skills = load_yaml(str(skills_file))
    skills.setdefault("rules", [])
    skills.setdefault("failure_patterns", [])
    skills["rules"].extend(new_rules)
    skills["failure_patterns"].extend(failures)
    skills["version"] = round(skills.get("version", 1.0) + 0.1, 1)

    save_yaml(str(skills_file), skills)
    logger.info(
        "Skills saved for %s at v%.1f (+%d rules, +%d failures)",
        agent_name, skills["version"], len(new_rules), len(failures),
    )

    if os.getenv("GIT_COMMIT_SKILLS", "true").lower() == "true":
        from persistence.git_manager import commit
        commit(agent_name, skills["version"], str(agents_path))
