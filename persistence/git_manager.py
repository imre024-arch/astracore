import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def commit(agent_name: str, version: float, agents_repo_path: str) -> None:
    repo_path = Path(agents_repo_path)
    git_dir = repo_path / ".git"

    if not git_dir.exists():
        logger.warning(
            "AGENTS_REPO_PATH is not a git repo — skill update saved but not committed."
        )
        return

    skills_file = repo_path / "agents" / agent_name / "skills.yaml"
    relative = str(skills_file.relative_to(repo_path))
    message = f"skills({agent_name}): update to v{version:.1f}"

    try:
        subprocess.run(
            ["git", "add", relative],
            cwd=repo_path, check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", message],
            cwd=repo_path, check=True, capture_output=True,
        )
        logger.info("Committed skill update for %s at v%.1f", agent_name, version)
    except subprocess.CalledProcessError as e:
        logger.warning(
            "Git commit failed for %s: %s", agent_name, e.stderr.decode().strip()
        )
