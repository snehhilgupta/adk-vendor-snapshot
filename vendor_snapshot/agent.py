from google.adk.agents import Agent, SequentialAgent
from google.adk.tools import google_search
from google.adk.tools.agent_tool import AgentTool
from pydantic import BaseModel, Field
from typing import Optional

class VendorSnapshot(BaseModel):
    company_name: str = Field(description="Canonical company name")
    founded: Optional[str] = Field(default=None, description="Year founded")
    headquarters: Optional[str] = Field(default=None, description="HQ location")
    employee_band: Optional[str] = Field(default=None, description="Employee count band: 1-10, 11-50, 51-200, 201-1000, 1000+")
    product_summary: str = Field(description="What the product does, 2-3 sentences max")
    recent_activity: Optional[str] = Field(default=None, description="Funding, releases, news — last 12 months")
    confidence_note: str = Field(description="Data quality caveat — sources, gaps, fabrication risk")

RESEARCHER_INSTRUCTION = """
You are a vendor research assistant with access to Google Search. The user will give you a vendor name. Use Google Search to find current information before responding.

Produce a concise vendor snapshot covering:

1. Company basics: HQ location, founding year, employee count band (1-10, 11-50, 51-200, 201-1000, 1000+)
2. Product / what they do: one-paragraph summary of their main offering
3. Recent activity: any funding, product launches, partnerships, leadership changes in the last 12 months — with specific dates and source URLs
4. Confidence note: how confident you are in the above, what sources you relied on, and what could not be verified

Rules:
- Always search before responding. Do not rely on training data alone.
- If search results do not contain reliable information about the vendor, say so explicitly. Do not fabricate.
- For "recent activity," cite the source URL inline next to each item.
- If a field is unknown after searching, say "unknown" rather than guessing.
- Use direct, factual language. No marketing copy.
""".strip()

VERIFIER_INSTRUCTION = """
You are a funding claim verifier with access to Google Search. You will receive a funding claim in this format:
- Company name
- Claimed amount
- Claimed date

Search for at least two independent sources that confirm or contradict this claim. Return one of three verdicts:
- CONFIRMED: at least two independent sources corroborate the claim. List the sources.
- CONTRADICTED: sources found that conflict with the claim. Explain the discrepancy.
- UNVERIFIABLE: insufficient independent sources found. State what was and was not found.

Be specific. Cite URLs. Do not guess.
""".strip()

ORCHESTRATOR_INSTRUCTION = """
You are a vendor research orchestrator. When given a vendor name:

1. Call vendor_researcher to gather raw vendor information.
2. For each funding claim found in the research output, call vendor_verifier with the company name, claimed amount, and claimed date.
3. Combine the research output and all verification verdicts into a single comprehensive summary. Include each verdict inline next to the relevant funding claim.

Return the combined summary as plain prose. Do not format as JSON.
""".strip()

FORMATTER_INSTRUCTION = """
You are a data formatter. You will receive raw vendor research text in the orchestrator_summary state variable below:

<orchestrator_summary>
{orchestrator_summary}
</orchestrator_summary>

Extract the information from orchestrator_summary and return it as a structured JSON object matching the required schema exactly.

Rules:
- Do not add information not present in orchestrator_summary.
- If a field is not present in the input, set it to null.
- confidence_note must always be populated — summarize the sourcing quality from the input.
- Include any funding verification verdicts in the confidence_note field.
- Do not search. Do not reason beyond what is in orchestrator_summary.
""".strip()

researcher = Agent(
    name="vendor_researcher",
    model="gemini-2.5-flash",
    instruction=RESEARCHER_INSTRUCTION,
    tools=[google_search],
)

verifier = Agent(
    name="vendor_verifier",
    model="gemini-2.5-flash",
    instruction=VERIFIER_INSTRUCTION,
    tools=[google_search],
)

orchestrator = Agent(
    name="vendor_orchestrator",
    model="gemini-2.5-flash",
    instruction=ORCHESTRATOR_INSTRUCTION,
    tools=[AgentTool(agent=researcher), AgentTool(agent=verifier)],
    output_key="orchestrator_summary",
)

formatter = Agent(
    name="vendor_formatter",
    model="gemini-2.5-flash",
    instruction=FORMATTER_INSTRUCTION,
    output_schema=VendorSnapshot,
)

root_agent = SequentialAgent(
    name="vendor_snapshot",
    sub_agents=[orchestrator, formatter],
)