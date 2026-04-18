import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from core.engine import Engine
from loaders.workflow_loader import load_workflow


def main():
    load_dotenv()

    # Accept an optional workflow path or name as the first CLI argument.
    # If it's a .yaml path, derive AGENTS_REPO_PATH from it automatically.
    if len(sys.argv) > 1:
        arg = Path(sys.argv[1]).resolve()
        if arg.suffix == ".yaml" and arg.exists():
            # Derive AGENTS_REPO_PATH from the path: workflows/ is two levels under repo root
            os.environ["AGENTS_REPO_PATH"] = str(arg.parent.parent)
            workflow_name = arg.stem
        else:
            workflow_name = sys.argv[1]
    else:
        workflow_name = os.getenv("RUN_MODE")

    engine = Engine()
    workflow = load_workflow(workflow_name)
    initial_input = input("Enter your story idea: ").strip()
    result = engine.run(workflow, initial_input)
    print("\n=== Final Output ===")
    print(result.get("last_output", "No output generated."))
    rejected = result.get("rejected_count", 0)
    if rejected:
        print(f"\n[{rejected} skill update(s) were rejected by the validation gate]")


if __name__ == "__main__":
    main()
