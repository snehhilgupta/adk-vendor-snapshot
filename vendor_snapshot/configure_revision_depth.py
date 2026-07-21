"""
configure_revision_depth.py — Stage 9.3 Step 4 follow-up.

Updates revisions_per_candidate_count from default (1) to 5, to test
whether increasing revision depth changes hedge-chaining behavior, or
whether chaining is driven by something else (e.g. the LLM reading its
own prior fact text rather than tracking discrete revisions).

Note: this REPLACES the customization_configs block, so we must re-declare
the VENDOR_FACTS topic and few-shot example alongside the new setting —
otherwise we'd silently lose Step 3's configuration.
"""
from dotenv import load_dotenv
load_dotenv()

import os
import vertexai
from google.genai.types import Content, Part
from vertexai._genai.types import (
    MemoryBankCustomizationConfig as CustomizationConfig,
    MemoryBankCustomizationConfigConsolidationConfig as ConsolidationConfig,
    MemoryBankCustomizationConfigMemoryTopic as MemoryTopic,
    MemoryBankCustomizationConfigMemoryTopicCustomMemoryTopic as CustomMemoryTopic,
    MemoryBankCustomizationConfigMemoryTopicManagedMemoryTopic as ManagedMemoryTopic,
    ManagedTopicEnum,
    MemoryBankCustomizationConfigGenerateMemoriesExample as GenerateMemoriesExample,
    MemoryBankCustomizationConfigGenerateMemoriesExampleConversationSource as ConversationSource,
    MemoryBankCustomizationConfigGenerateMemoriesExampleConversationSourceEvent as ConversationSourceEvent,
    MemoryBankCustomizationConfigGenerateMemoriesExampleGeneratedMemory as ExampleGeneratedMemory,
    ReasoningEngineContextSpecMemoryBankConfig as MemoryBankConfig,
)

PROJECT = os.environ["GOOGLE_CLOUD_PROJECT"]
LOCATION = os.environ["GOOGLE_CLOUD_LOCATION"]
AGENT_ENGINE_ID = os.environ["AGENT_ENGINE_ID"]

RESOURCE_NAME = f"projects/{PROJECT}/locations/{LOCATION}/reasoningEngines/{AGENT_ENGINE_ID}"


def main():
    client = vertexai.Client(project=PROJECT, location=LOCATION)

    vendor_facts_example = GenerateMemoriesExample(
        conversation_source=ConversationSource(
            events=[
                ConversationSourceEvent(
                    content=Content(role="user", parts=[Part(text="Solace")])
                ),
                ConversationSourceEvent(
                    content=Content(
                        role="model",
                        parts=[Part(text=(
                            "Solace, founded 2001, headquartered in Ottawa, "
                            "Canada, provides an event-driven architecture "
                            "platform for real-time data streaming."
                        ))],
                    )
                ),
            ]
        ),
        generated_memories=[
            ExampleGeneratedMemory(
                fact="Solace was founded in 2001 and is headquartered in Ottawa, Canada."
            ),
            ExampleGeneratedMemory(
                fact="Solace provides an event-driven architecture platform for real-time data streaming."
            ),
        ],
    )

    memory_bank_config = MemoryBankConfig(
        customization_configs=[
            CustomizationConfig(
                memory_topics=[
                    MemoryTopic(managed_memory_topic=ManagedMemoryTopic(
                        managed_topic_enum=ManagedTopicEnum.USER_PERSONAL_INFO)),
                    MemoryTopic(managed_memory_topic=ManagedMemoryTopic(
                        managed_topic_enum=ManagedTopicEnum.USER_PREFERENCES)),
                    MemoryTopic(managed_memory_topic=ManagedMemoryTopic(
                        managed_topic_enum=ManagedTopicEnum.KEY_CONVERSATION_DETAILS)),
                    MemoryTopic(managed_memory_topic=ManagedMemoryTopic(
                        managed_topic_enum=ManagedTopicEnum.EXPLICIT_INSTRUCTIONS)),
                    MemoryTopic(custom_memory_topic=CustomMemoryTopic(
                        label="VENDOR_FACTS",
                        description=(
                            "Factual information about vendors or companies "
                            "researched, including company basics (founding "
                            "year, headquarters, size), product details, "
                            "funding, partnerships, and recent activity."
                        ),
                    )),
                ],
                generate_memories_examples=[vendor_facts_example],
                consolidation_config=ConsolidationConfig(
                    revisions_per_candidate_count=5,
                ),
            )
        ]
    )

    updated = client.agent_engines.update(
        name=RESOURCE_NAME,
        config={"context_spec": {"memory_bank_config": memory_bank_config}},
    )
    print("Instance updated: revisions_per_candidate_count=5")
    print(f"update_time: {updated.api_resource.update_time}")


if __name__ == "__main__":
    main()