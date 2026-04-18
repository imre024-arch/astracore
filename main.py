import os

from dotenv import load_dotenv

from core.engine import Engine
from loaders.workflow_loader import load_workflow


def main():
    load_dotenv()
    engine = Engine()
    workflow_name = os.getenv("RUN_MODE")
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
