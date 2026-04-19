import os
import sys
import uuid
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
    initial_input = input("Enter your story idea (leave blank to pick an existing story): ").strip()

    if not initial_input:
        initial_input = _pick_story_from_knowledgebase()
    else:
        os.environ["STORY_ID"] = f"story_{uuid.uuid4().hex[:8]}"

    result = engine.run(workflow, initial_input)
    print("\n=== Final Output ===")
    print(result.get("last_output", "No output generated."))
    rejected = result.get("rejected_count", 0)
    if rejected:
        print(f"\n[{rejected} skill update(s) were rejected by the validation gate]")


def _pick_story_from_knowledgebase() -> str:
    from knowledge.graph_store import GraphStore

    agents_path = Path(os.environ["AGENTS_REPO_PATH"])
    knowledge_dir = agents_path / "knowledge"

    if not knowledge_dir.exists():
        print("No knowledge base found. Please enter a story idea.")
        return input("Enter your story idea: ").strip()

    stories = sorted(p.name for p in knowledge_dir.iterdir() if p.is_dir())
    if not stories:
        print("No stories in the knowledge base. Please enter a story idea.")
        return input("Enter your story idea: ").strip()

    print("\nAvailable stories:")
    for i, story_id in enumerate(stories, 1):
        print(f"  {i}. {story_id}")

    choice = input(f"\nPick a story [1-{len(stories)}]: ").strip()
    try:
        story_id = stories[int(choice) - 1]
    except (ValueError, IndexError):
        print(f"Invalid choice, using '{stories[0]}'.")
        story_id = stories[0]

    os.environ["STORY_ID"] = story_id

    store = GraphStore(story_id)
    try:
        story_nodes = store.get_nodes_by_type("Story")
        premise = story_nodes[0].get("premise", "") if story_nodes else ""
    finally:
        store.close()

    return premise or f"Continue developing story: {story_id}"


if __name__ == "__main__":
    main()
