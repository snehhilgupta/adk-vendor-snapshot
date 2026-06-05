from google.adk.agents import Agent

root_agent = Agent(
    name="vendor_snapshot",
    model="gemini-2.5-flash",
    instruction="You are a placeholder agent. Reply with the word 'ready' and nothing else.",
)