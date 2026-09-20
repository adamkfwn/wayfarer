# Wayfarer architecture

## Problem

Aid Nordic's staff travel between headquarters in Denmark and Sweden and programmes in Kenya, Jordan, Bangladesh and Colombia. Entra ID Protection and Defender raise identity alerts on each arrival: impossible travel, unfamiliar location, new device. Most are explained by approved travel. A few are real. Analysts cannot tell which without opening the travel register, the device inventory and the playbook for every alert, so real ones wait behind benign ones.

Wayfarer does that lookup and reasoning for each alert and proposes a response. It does not act. The proposal, the evidence and the policy citation go to a person.

## Components

```
alerts.json ──> alert-triage-agent ──> travel-context-agent ──> response-agent ──> result
                (classify, severity)   (lookup_traveller,        (File Search over
                                        lookup_device)            policies/)
```

| Component | Where | Role |
|---|---|---|
| Foundry project | Azure, Sweden Central | Hosts the agents, the model deployment and the vector store |
| `alert-triage-agent` | Foundry prompt agent | Normalises the alert type and sets initial severity |
| `travel-context-agent` | Foundry prompt agent with two function tools | Explains or fails to explain the alert against the travel register and device state |
| `response-agent` | Foundry prompt agent with File Search | Applies the incident playbook and drafts the user message |
| `wayfarer-policies` | Foundry vector store | The four Aid Nordic policy documents |
| `agents.py` | Python | Definitions, Pydantic contracts, tool-call loop, per-alert pipeline |
| `workflow.py` | Python | Shift-level orchestration and summary |
| `api.py` | FastAPI | HTTP front door with Entra ID bearer validation |
| Application Insights | Azure | Traces with content capture off |
| Evaluation | `azure-ai-evaluation` | Exact match on disposition, severity and explained against `expected.jsonl` |

## Data flow for one alert

1. The caller sends the alert JSON to `alert-triage-agent`. The reply is validated as `Triage`.
2. The alert and triage go to `travel-context-agent`. It calls `lookup_traveller(user_id)` and `lookup_device(device_id)`. The Python loop runs the functions locally against `travellers.json` and returns the outputs. The reply is validated as `TravelContext`.
3. The alert, triage and travel context go to `response-agent`. File Search retrieves the relevant policy passages server side. The reply is validated as `ResponsePlan`.
4. The three validated objects are merged into one result. Code forces `requires_approval` true for `block_and_revoke` and for `leaked_credentials`, whatever the model said.

Each agent gets a fresh conversation per alert and the conversation is deleted afterwards. Agents share nothing between alerts except their instructions.

## Why three agents

One agent could do all of it. Splitting has three benefits that matter here. The travel-context agent is the only one with tools, so the tool surface is small and easy to audit. The response agent is the only one with policy knowledge, so a wrong disposition can be traced to a retrieval or a prompt rather than to a tangle. And each boundary is a typed JSON contract that can be evaluated on its own.

## Trust and safety boundaries

- The agents never see real identities. User ids and device ids are pseudonyms. IPs are masked before they reach the alert feed.
- No agent has a tool that changes anything. There is no Graph call, no session revoke, no password reset. The result is a proposal.
- Approval requirements are enforced in code, not only in prompts.
- Tracing runs with message content capture off. Telemetry has timings, tokens, tool names and status, not alert content.
- The API validates Entra ID tokens against the tenant's keys and checks issuer and audience. It records the caller's object id with the result.
- Policies are the only knowledge source. If the response agent cannot cite a section it must escalate.

## What is synthetic

Aid Nordic, its staff, devices, trips, alerts and policies were written for this lab. The IP prefixes are documentation ranges. No tenant data, alert export or real policy was used.

## Out of scope

Real Graph actions, Logic Apps, a user interface, multi-tenant operation, Container Apps deployment and real programme data. The runbook describes how each would attach if built.
