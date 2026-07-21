"""
create_memory_instance.py — ONE-TIME setup for Stage 9.3.

Creates a single Vertex AI Agent Engine instance (reasoningEngine resource)
to back Memory Bank. We do NOT deploy any agent to Runtime — this instance
exists only to hold long-term memories, keyed by scope/user_id.

Run once. Copy the printed AGENT_ENGINE_ID into .env, then never run again.
"""
from dotenv import load_dotenv
load_dotenv()

import os
import vertexai

PROJECT = os.environ["GOOGLE_CLOUD_PROJECT"]
LOCATION = "us-central1"

def main():
    client = vertexai.Client(project=PROJECT, location=LOCATION)

    agent_engine = client.agent_engines.create()

    resource_name = agent_engine.api_resource.name
    agent_engine_id = resource_name.split("/")[-1]

    print("=" * 60)
    print("Agent Engine instance created.")
    print(f"Full resource name: {resource_name}")
    print(f"AGENT_ENGINE_ID:    {agent_engine_id}")
    print("=" * 60)
    print("Add this line to vendor_snapshot/.env:")
    print(f"AGENT_ENGINE_ID={agent_engine_id}")

if __name__ == "__main__":
    main()