# AstraCore

A config-driven multi-agent orchestration framework. Agent behavior, skills, tools, and workflows are defined entirely in YAML — the Python engine executes them without hardcoded agent logic.

## How it works

- **Agents** are YAML files (`agent.yaml`, `skills.yaml`, `prompt.txt`). No agent code lives in this repo.
- **Workflows** are YAML step lists. The engine walks them, calling agents and actions in order.
- **Skills evolve** — after each critique/mentor loop, validated rules are appended to `skills.yaml` and committed to Git.
- **Any OpenAI-compatible LLM** works: point `WRITER_LLM_BASE_URL` at Ollama, Groq, or OpenAI.

## Quickstart

```bash
cp .env.example .env        # fill in your LLM endpoints and AGENTS_REPO_PATH
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt
echo "your story idea" | .venv/Scripts/python main.py path/to/workflows/training.yaml
```

## Environment variables

| Variable | Description |
|---|---|
| `WRITER_LLM_BASE_URL/API_KEY/MODEL` | LLM endpoint for writer-type agents |
| `MENTOR_LLM_BASE_URL/API_KEY/MODEL` | LLM endpoint for critique/mentor agents |
| `AGENTS_REPO_PATH` | Absolute path to the `astra-agents` config repo |
| `RUN_MODE` | Workflow name to run (`training` or `writing`) |
| `CRITIQUE_LOOP_COUNT` | Training iterations (default: 3) |
| `DEBATE_LOOP_COUNT` | Debate turns per debate loop (default: 2) |
| `LLM_MAX_TOKENS` | Max tokens per LLM response (default: 4096) |
| `SKILL_VALIDATION_THRESHOLD` | Min score to accept a skill update (default: 0.6) |
| `GIT_COMMIT_SKILLS` | Commit skill updates to Git (default: true) |
| `LOG_LEVEL` | `DEBUG` for full LLM traces, `INFO` for step summaries |

## Guardrails

- **Prompt explosion** — `max_prompt_tokens` per agent; prompt builder truncates context → rules → skills before raising.
- **Skill drift** — mentor output is scored by `critique_editorial` before any skill file is written.
- **Tool overuse** — `max_tool_calls_per_run` per agent; enforced in `AgentRuntime.call_tool()`.

## Repo layout

```
core/          — engine, workflow runner, loop engine, skill system
llm/           — single OpenAI-compatible client + prefix-based router
loaders/       — agent, workflow, and tool loaders
execution/     — prompt builder (with token budgeting) + response parser
persistence/   — YAML storage + Git commit helper
config/        — env var validation
```

Agent definitions, prompts, and workflows live in the companion repo [astra-agents](https://github.com/imre024-arch/astra-agents).
