"""
list_memories.py — diagnostic. Lists all memories in the Agent Engine
instance directly via the API, bypassing search_memory's query-matching.
Rerunnable anytime to check ground truth.
"""
from dotenv import load_dotenv
load_dotenv()

import os
import vertexai

client = vertexai.Client(
    project=os.environ["GOOGLE_CLOUD_PROJECT"],
    location=os.environ["GOOGLE_CLOUD_LOCATION"],
)
name = (
    f"projects/{os.environ['GOOGLE_CLOUD_PROJECT']}"
    f"/locations/{os.environ['GOOGLE_CLOUD_LOCATION']}"
    f"/reasoningEngines/{os.environ['AGENT_ENGINE_ID']}"
)

memories = list(client.agent_engines.memories.list(name=name))
print(f"Total memories: {len(memories)}")
for m in memories:
    print(m)
    print("---")