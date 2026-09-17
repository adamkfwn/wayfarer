# Step 4: Workflow

Time: about 30 minutes.

## Objective

The three agents orchestrated from code as one triage workflow with a shift summary, and the same workflow exposed as an HTTP API that accepts Entra ID bearer tokens. Then the same flow built visually in the Foundry portal.

## Code or portal orchestration

The portal designer wires agents into a sequence and passes each agent's text output to the next. It is quick to build and easy to show. It cannot run the local `lookup_traveller` and `lookup_device` functions, and it cannot validate the JSON between steps.

`workflow.py` orchestrates from Python instead. It reuses the agents from step 1 (creating them only if missing), runs each alert through triage, travel context and response, validates each handoff with the Pydantic models from `agents.py`, and prints a shift summary: counts by disposition and severity, the alerts awaiting approval and the alerts escalated to an analyst. The summary is written to `shift_summary.json`.

## The JSON contract

| From | To | Fields |
|---|---|---|
| alert | triage | `alert_id`, `user_id`, `device_id`, `alert_type`, `timestamp`, `location`, `ip_masked`, `detail` |
| triage | travel context | `alert_id`, `alert_type`, `severity`, `summary` |
| travel context | response | `alert_id`, `explained`, `confidence`, `evidence[]` |
| response | caller | `alert_id`, `disposition`, `requires_approval`, `policy_citation`, `user_message`, `rationale` |

Each agent receives the alert plus everything produced so far, as one JSON object. Each output is validated before it is passed on.

## What to run

```bash
cd step-4-workflow
python workflow.py
```

## The API

`api.py` wraps the workflow in FastAPI with two routes. `GET /health` returns `{"status": "ok"}`. `POST /triage` takes one alert as JSON and returns the triage result.

`POST /triage` requires a bearer token issued by your Entra tenant for the API's app registration. The token's signature is checked against the tenant's published keys, and the issuer and audience must match. Set these in `.env`:

- `ENTRA_TENANT_ID`: written by `deploy.sh` from your signed-in account.
- `API_AUDIENCE`: the client id or application id URI of an app registration you create for the API. Set its accepted token version to 2 so the issuer matches.

Run it:

```bash
cd step-4-workflow
uvicorn api:app --reload
```

Get a token for the API with `az account get-access-token --resource <API_AUDIENCE>` and call `POST /triage` with `Authorization: Bearer <token>` and an alert from `alerts.json` as the body. Without a token, or with one for a different audience, the call returns 401.

The API does not execute any disposition. It returns the proposal and the approver's object id from the token, so a caller can record who asked.

## Build the same workflow in the portal

1. In the Foundry portal open Build, Agents, Workflows, then Create and Blank workflow.
2. Add an Agent node and select `alert-triage-agent`. Set the next node to Agent.
3. Select `travel-context-agent`. Set the next node to Agent.
4. Select `response-agent`. Set the next node to End. Save as `wayfarer-triage-portal`.
5. Open Preview and paste one line from `../step-3-evaluate/eval_portal.jsonl`. The traveller context is embedded in the query because the portal cannot call the lookup tools.
6. Watch the three steps run and compare the output with the same alert in `shift_summary.json`. Open Traces for the run.

## Success criteria

- [ ] `workflow.py` runs all 40 alerts and prints a shift summary with the approval queue
- [ ] `GET /health` answers without a token and `POST /triage` returns 401 without one
- [ ] `POST /triage` with a valid token returns a triage result for an alert
- [ ] The portal workflow runs the three agents in sequence on a pasted alert
