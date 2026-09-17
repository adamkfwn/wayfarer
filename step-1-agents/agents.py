"""
Step 1: Build the three Wayfarer agents and run every alert through them.

Usage:
    python agents.py
"""

import json
import os
import re
import sys
from contextlib import ExitStack
from pathlib import Path
from typing import Literal

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import FileSearchTool, PromptAgentDefinition
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from openai import OpenAI
from openai.types.responses.response_input_param import FunctionCallOutput
from pydantic import BaseModel, Field, ValidationError, model_validator

from tools import LOOKUP_TOOLS, call_tool


def _find_repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / ".env").exists():
            return parent
    return Path(__file__).resolve().parents[1]


load_dotenv(_find_repo_root() / ".env")

PROJECT_CONNECTION_STRING = os.getenv("PROJECT_CONNECTION_STRING")
MODEL_DEPLOYMENT_NAME = os.getenv("MODEL_DEPLOYMENT_NAME", "gpt-5.4")

STEP_DIR = Path(__file__).resolve().parent
ALERTS_PATH = STEP_DIR / "alerts.json"
POLICIES_DIR = STEP_DIR / "policies"
RESULTS_PATH = STEP_DIR / "results.jsonl"

TRIAGE_AGENT = "alert-triage-agent"
TRAVEL_AGENT = "travel-context-agent"
RESPONSE_AGENT = "response-agent"
VECTOR_STORE_NAME = "wayfarer-policies"

AlertType = Literal[
    "impossible_travel",
    "unfamiliar_location",
    "new_device",
    "leaked_credentials",
    "mfa_fatigue",
    "token_anomaly",
]
Severity = Literal["low", "medium", "high", "critical"]
Disposition = Literal["dismiss", "require_mfa", "block_and_revoke", "escalate_human"]


class Triage(BaseModel):
    alert_id: str
    alert_type: AlertType
    severity: Severity
    summary: str


class TravelContext(BaseModel):
    alert_id: str
    explained: bool
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[str]


class ResponsePlan(BaseModel):
    alert_id: str
    disposition: Disposition
    severity: Severity
    requires_approval: bool
    policy_citation: str
    user_message: str
    rationale: str

    @model_validator(mode="after")
    def _block_requires_approval(self) -> "ResponsePlan":
        if self.disposition == "block_and_revoke":
            self.requires_approval = True
        return self


JSON_ONLY = (
    "Reply with a single JSON object and nothing else: no markdown, no code fences, no prose. "
    "All identifiers you receive are pseudonymous and IP addresses are masked; repeat them as given."
)

TRIAGE_INSTRUCTIONS = f"""
You are the alert triage agent for Aid Nordic, a humanitarian NGO.
You receive one Entra ID or Defender identity alert as JSON.
Classify it and assign an initial severity. Do not decide the response.

alert_type must be one of: impossible_travel, unfamiliar_location, new_device,
leaked_credentials, mfa_fatigue, token_anomaly. Trust the alert's own alert_type
unless the detail clearly describes a different type.

Initial severity: leaked_credentials is critical; mfa_fatigue, token_anomaly and
impossible_travel are high; unfamiliar_location and new_device are medium.
Travel context is applied later by another agent, so do not lower severity here.

{JSON_ONLY}
Schema: {{"alert_id": str, "alert_type": str, "severity": "low|medium|high|critical", "summary": str}}
"""

TRAVEL_INSTRUCTIONS = f"""
You are the travel context agent for Aid Nordic, a humanitarian NGO.
You receive an alert and its triage as JSON. Decide whether the activity is explained
by an approved trip on a compliant, registered device.

Always call lookup_traveller with the alert's user_id and lookup_device with the alert's
device_id before answering. An activity is explained only when all of these hold:
- an approved trip has start <= alert date <= end,
- the trip destination matches the alert location,
- the alert's device_id is the traveller's registered device and it is compliant,
- the alert_type is impossible_travel, unfamiliar_location or new_device.
leaked_credentials, mfa_fatigue and token_anomaly are never explained by travel.

Set confidence between 0 and 1. A sign-in on any date from trip start to trip end
inclusive is inside the trip. A sign-in up to 48 hours before the start or after the end
is a trip-boundary case: not explained, note the boundary in the evidence. Transit hubs,
VPN egress and unregistered devices during a trip are not explained either. The first
sign-in from the home country in an impossible_travel pair is the departure and does not
count against the traveller. List each fact you relied on as one evidence string.

{JSON_ONLY}
Schema: {{"alert_id": str, "explained": bool, "confidence": float, "evidence": [str]}}
"""

RESPONSE_INSTRUCTIONS = f"""
You are the response agent for Aid Nordic, a humanitarian NGO.
You receive an alert, its triage and its travel context as JSON. Propose the response.

Use file search over the Aid Nordic policies to find the rule that applies, and cite it
as file name plus section, for example "incident-playbook.md section 3.4".
disposition must be one of: dismiss, require_mfa, block_and_revoke, escalate_human.
severity is the final severity stated by the playbook section you apply, not the triage severity.
If no policy section clearly covers the case, return escalate_human and say why.

Rules that always hold:
- block_and_revoke always has requires_approval true.
- leaked_credentials always has requires_approval true, whatever the disposition.
- Approved travel never explains leaked_credentials, mfa_fatigue or token_anomaly.

user_message is the draft message to the staff member. For dismiss it may be empty.
Otherwise it says what was observed, what is proposed and what to do next, in plain
language, without IP addresses or technical identifiers, and states that the decision
was prepared with AI assistance and reviewed by the IT Security team.

{JSON_ONLY}
Schema: {{"alert_id": str, "disposition": str, "severity": "low|medium|high|critical",
"requires_approval": bool, "policy_citation": str, "user_message": str, "rationale": str}}
"""


def connect() -> tuple[AIProjectClient, OpenAI]:
    client = AIProjectClient(endpoint=PROJECT_CONNECTION_STRING, credential=DefaultAzureCredential())
    return client, client.get_openai_client().with_options(max_retries=8)


def ensure_vector_store(openai_client: OpenAI) -> str:
    existing = next((s for s in openai_client.vector_stores.list() if s.name == VECTOR_STORE_NAME), None)
    if existing:
        return existing.id
    store = openai_client.vector_stores.create(name=VECTOR_STORE_NAME)
    with ExitStack() as stack:
        files = [stack.enter_context(open(path, "rb")) for path in sorted(POLICIES_DIR.glob("*.md"))]
        openai_client.vector_stores.file_batches.upload_and_poll(store.id, files=files)
    return store.id


def agent_definitions(openai_client: OpenAI) -> list[tuple[str, PromptAgentDefinition]]:
    vector_store_id = ensure_vector_store(openai_client)
    return [
        (TRIAGE_AGENT, PromptAgentDefinition(model=MODEL_DEPLOYMENT_NAME, instructions=TRIAGE_INSTRUCTIONS)),
        (
            TRAVEL_AGENT,
            PromptAgentDefinition(model=MODEL_DEPLOYMENT_NAME, instructions=TRAVEL_INSTRUCTIONS, tools=LOOKUP_TOOLS),
        ),
        (
            RESPONSE_AGENT,
            PromptAgentDefinition(
                model=MODEL_DEPLOYMENT_NAME,
                instructions=RESPONSE_INSTRUCTIONS,
                tools=[FileSearchTool(vector_store_ids=[vector_store_id])],
            ),
        ),
    ]


def create_agents(client: AIProjectClient, openai_client: OpenAI) -> None:
    for name, definition in agent_definitions(openai_client):
        version = client.agents.create_version(agent_name=name, definition=definition)
        print(f"Created {version.name} (version {version.version})")


def ensure_agents_deployed(client: AIProjectClient, openai_client: OpenAI) -> None:
    existing = {agent.name for agent in client.agents.list()}
    for name, definition in agent_definitions(openai_client):
        if name in existing:
            print(f"Found existing: {name}")
            continue
        client.agents.create_version(agent_name=name, definition=definition)
        print(f"Deployed: {name}")


def run_agent(openai_client: OpenAI, agent_name: str, input_text: str) -> str:
    agent_ref = {"agent_reference": {"name": agent_name, "type": "agent_reference"}}
    conversation = openai_client.conversations.create()
    response = openai_client.responses.create(input=input_text, conversation=conversation.id, extra_body=agent_ref)
    while any(item.type == "function_call" for item in response.output):
        response = openai_client.responses.create(
            input=_tool_outputs(response), conversation=conversation.id, extra_body=agent_ref
        )
    openai_client.conversations.delete(conversation_id=conversation.id)
    return response.output_text


def _tool_outputs(response) -> list[FunctionCallOutput]:
    return [
        FunctionCallOutput(
            type="function_call_output",
            call_id=item.call_id,
            output=call_tool(item.name, json.loads(item.arguments)),
        )
        for item in response.output
        if item.type == "function_call"
    ]


def parse_json(text: str) -> dict:
    without_citations = re.sub(r"【[^】]*】", "", text).strip()
    without_fences = re.sub(r"^```(?:json)?\s*|\s*```$", "", without_citations)
    return json.loads(without_fences)


def _handoff(**parts) -> str:
    return json.dumps(
        {key: value.model_dump() if isinstance(value, BaseModel) else value for key, value in parts.items()}
    )


def triage_alert(openai_client: OpenAI, alert: dict) -> dict:
    triage = Triage.model_validate(parse_json(run_agent(openai_client, TRIAGE_AGENT, json.dumps(alert))))
    context = TravelContext.model_validate(
        parse_json(run_agent(openai_client, TRAVEL_AGENT, _handoff(alert=alert, triage=triage)))
    )
    plan = ResponsePlan.model_validate(
        parse_json(
            run_agent(openai_client, RESPONSE_AGENT, _handoff(alert=alert, triage=triage, travel_context=context))
        )
    )
    return _merge(alert, triage, context, plan)


def _merge(alert: dict, triage: Triage, context: TravelContext, plan: ResponsePlan) -> dict:
    return {
        "alert_id": alert["alert_id"],
        "user_id": alert["user_id"],
        "alert_type": triage.alert_type,
        "severity": plan.severity,
        "initial_severity": triage.severity,
        "summary": triage.summary,
        "explained": context.explained,
        "confidence": context.confidence,
        "evidence": context.evidence,
        "disposition": plan.disposition,
        "requires_approval": plan.requires_approval or triage.alert_type == "leaked_credentials",
        "policy_citation": plan.policy_citation,
        "user_message": plan.user_message,
        "rationale": plan.rationale,
    }


def load_alerts() -> list[dict]:
    with open(ALERTS_PATH) as f:
        return json.load(f)["alerts"]


def triage_all(openai_client: OpenAI, alerts: list[dict]) -> list[dict]:
    results = []
    for alert in alerts:
        try:
            result = triage_alert(openai_client, alert)
        except (ValidationError, json.JSONDecodeError) as error:
            result = {"alert_id": alert["alert_id"], "user_id": alert["user_id"], "error": str(error)}
        results.append(result)
        print(_format_line(result))
    return results


def _format_line(result: dict) -> str:
    if "error" in result:
        return f"{result['alert_id']}  ERROR  {result['error'][:80]}"
    approval = "  (approval required)" if result["requires_approval"] else ""
    return (
        f"{result['alert_id']}  {result['alert_type']:<20} explained={result['explained']!s:<5} "
        f"{result['severity']:<8} {result['disposition']}{approval}"
    )


def write_results(results: list[dict]) -> None:
    with open(RESULTS_PATH, "w") as f:
        f.writelines(json.dumps(result) + "\n" for result in results)


def main():
    if not PROJECT_CONNECTION_STRING:
        print("PROJECT_CONNECTION_STRING not set. Run step 0 first.")
        sys.exit(1)

    client, openai_client = connect()
    print("=== Ensuring agents ===")
    ensure_agents_deployed(client, openai_client)

    alerts = load_alerts()
    print(f"\n=== Triaging {len(alerts)} alerts ===")
    results = triage_all(openai_client, alerts)
    write_results(results)

    failed = sum("error" in result for result in results)
    print(f"\nProcessed {len(results)} alerts, {failed} failed. Results written to {RESULTS_PATH.name}")
    client.close()


if __name__ == "__main__":
    main()
