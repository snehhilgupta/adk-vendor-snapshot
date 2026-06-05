# Stage 0 — Environment & Project Skeleton

## Goal

Stand up a working ADK installation, project skeleton, and a placeholder agent that responds to `adk web`. No real agent logic yet — this stage exists to validate the toolchain end-to-end before introducing any ADK concepts.

## Concepts introduced

- **ADK package convention** — an agent is a Python package with `__init__.py` (importing `agent`) and `agent.py` (exposing a top-level `root_agent`). The CLI discovers agents by scanning for this pattern.
- **`Agent` class** — ADK's basic LLM-driven agent (alias for `LlmAgent`). Takes `name`, `model`, `instruction` at minimum.
- **`.env` loading** — ADK loads environment variables from `.env` inside the agent package directory, not the project root.
- **AI Studio vs Vertex AI toggle** — `GOOGLE_GENAI_USE_VERTEXAI=FALSE` routes to AI Studio (consumer, free tier). `TRUE` routes to Vertex AI (enterprise GCP, billed). One flag flips the entire backend.
- **`adk web`** — local FastAPI dev server with chat, Events tab (LLM/tool calls), and Traces tab (timing breakdown).

## What was built

```
adk-vendor-snapshot/
├── .gitignore
├── README.md
├── docs/
│   └── stage-0-setup.md
└── vendor_snapshot/
    ├── __init__.py
    ├── agent.py
    └── .env
```

### `vendor_snapshot/__init__.py`
```python
from . import agent
```

### `vendor_snapshot/agent.py`
```python
from google.adk.agents import Agent

root_agent = Agent(
    name="vendor_snapshot",
    model="gemini-2.5-flash",
    instruction="You are a placeholder agent. Reply with the word 'ready' and nothing else.",
)
```

### `vendor_snapshot/.env` (not committed)
```
GOOGLE_GENAI_USE_VERTEXAI=FALSE
GOOGLE_API_KEY=<AI Studio key>
```

## How to run

From the project root:

```cmd
adk web
```

Open http://localhost:8000, select `vendor_snapshot` from the dropdown, send any message. Expect the agent to reply with `ready`.

## Observations

`adk web` started cleanly on port 8000. Dev UI loaded at http://localhost:8000 with `vendor_snapshot` listed in the agent dropdown.

Sent `Hi` as a test message. Agent responded with `ready` — matches the instruction exactly.

**Traces tab** showed the call structure:
- `vendor_snapshot` (1.88s total)
  - `call_llm` (1.86s)
    - `generate_content gemini-2.5-flash` (1.86s)

~98% of turn time was the Gemini API round-trip. Useful baseline — local agent overhead is negligible at this stage; latency will grow with tool calls and multi-agent chains in later stages.

**Events tab** showed two events for the turn:
- #1 — user message ("Hi")
- #2 — agent response ("ready")

Events did not expand to show LLM request/response detail in this ADK version. Richer events expected in later stages once tool calls and state mutations are introduced.

## Gotchas hit

- **Python 3.14 on Windows** — ADK 2.1.0 installs cleanly on 3.14 (wheels available), but the `adk.exe` Scripts directory isn't on PATH by default. Fix: `setx PATH "%PATH%;C:\Users\<user>\AppData\Local\Python\pythoncore-3.14-64\Scripts"`, restart terminal.
- **`.env` location** — must be inside the agent package (`vendor_snapshot/.env`), not the project root. ADK looks for it relative to the agent module.
- **`.gitignore` placement** — must be at the project root, not inside the agent package. Easy to misplace when creating via VS Code right-click on the wrong folder.

## Next stage

Stage 1 — replace the placeholder instruction with a real vendor-snapshot prompt. Run it against test vendors and observe where training-data-only output breaks down (stale data, missing recent activity, possible fabrication). That failure motivates Stage 2's grounding via Google Search.