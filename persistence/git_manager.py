import logging
from pathlib import Path
import git

logger = logging.getLogger(__name__)


def commit(agent_name: str, version: float, agents_repo_path: str) -> None:
    repo_path = Path(agents_repo_path)
    try:
        repo = git.Repo(repo_path)
    except git.InvalidGitRepositoryError:
        logger.warning(
            "AGENTS_REPO_PATH is not a git repo — skill update saved but not committed."
        )
        return

    skills_file = repo_path / "agents" / agent_name / "skills.yaml"
    relative = str(skills_file.relative_to(repo_path))
    repo.index.add([relative])
    repo.index.commit(f"skills({agent_name}): update to v{version:.1f}")
    logger.info("Committed skill update for %s at v%.1f", agent_name, version)
