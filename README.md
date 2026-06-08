# ADK Vendor Snapshot

Learning Google's Agent Development Kit (ADK) by building an enterprise-style agent that takes a vendor name as input and returns a structured snapshot (company basics, product, recent activity, confidence note).

## Why this project

ADK is Google's code-first framework for building agents. This repo is an independent, hands-on study path — each stage adds one ADK primitive on top of the same use case so the learning is cumulative rather than scattered across throwaway examples.

## Stack

- **Framework:** Google ADK (Python, v2.1.0)
- **Model:** Gemini 2.5 Flash via AI Studio (free tier)
- **Python:** 3.14

## Repository structure
adk-vendor-snapshot/
├── docs/                       # one markdown file per stage
│   ├── stage-0-setup.md
│   ├── stage-1-bare-agent.md
│   └── stage-2-grounded-search.md
├── vendor_snapshot/            # the agent package
│   ├── init.py
│   ├── agent.py
│   └── .env                    # API key — not committed
├── .gitignore
└── README.md
## Study path

| Stage | Concept | Status |
|-------|---------|--------|
| 0 | Environment, project skeleton, placeholder agent | ✅ |
| 1 | Single agent, no tools — see training-data limits | ✅ |
| 2 | Built-in Google Search grounding | ✅ |
| 3 | Structured output via Pydantic schema | — |
| 4 | Custom function tool + tool composition | — |
| 5 | Multi-agent SequentialAgent (Researcher → Analyst → Writer) | — |
| 6 | Critic agent with vendor-name-match | — |
| 7 | LoopAgent + callbacks for guardrails | — |
| 8 | Evaluation with `adk eval` | — |
| 9 | Session state and in-process memory | — |
| 10 | Deployment surfaces (architectural read-only) | — |

## Running locally

1. Install ADK: `pip install google-adk`
2. Create `vendor_snapshot/.env` with your AI Studio API key:GOOGLE_GENAI_USE_VERTEXAI=FALSE
GOOGLE_API_KEY=your_key_here
3. From the project root: `adk web`
4. Open http://localhost:8000 and select `vendor_snapshot`

## Notes

This is a learning repo. Code evolves as concepts are introduced — see `docs/` for what each stage teaches, what changed, and what was observed when running it.