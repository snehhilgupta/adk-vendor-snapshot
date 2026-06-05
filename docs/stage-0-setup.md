# Stage 0 — Environment & Project Skeleton

## Goal

Stand up a working ADK installation, project skeleton, and a placeholder agent that responds to `adk web`. No real agent logic yet — this stage exists to validate the toolchain end-to-end before introducing any ADK concepts.

## Concepts introduced

- **ADK package convention** — an agent is a Python package with `__init__.py` (importing `agent`) and `agent.py` (exposing a top-level `root_agent`). The CLI discovers agents by scanning for this pattern.
- **`Agent` class** — ADK's basic LLM-driven agent (alias for `LlmAgent`). Takes `name`, `model`, `instruction` at minimum.
- **`.env` loading** — ADK loads environment variables from `.env` inside the agent package directory, not the project root.
- **AI Studio vs Vertex AI toggle** — `GOOGLE_GENAI_USE_VERTEXAI=FALSE` routes to AI Studio (consumer, free tier). `TRUE` routes to Vertex AI (enterprise GCP, billed). One flag flips the entire backend.
- **`adk web`** — local FastAPI dev server with chat, Events tab (LLM/tool calls), and State tab (session state).

## What was built