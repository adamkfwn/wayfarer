# Step 1: Build the agents

Time: about 30 minutes.

## Objective

Three agents in your Foundry project, and all 40 synthetic alerts in `alerts.json` triaged end to end with a validated JSON handoff between each agent.

## The agents

| Agent | Job | Tools and knowledge | Output |
|---|---|---|---|
| `alert-triage-agent` | Classify the alert type and set an initial severity | none | `alert_id`, `alert_type`, `severity`, `summary` |
| `travel-context-agent` | Decide whether an approved trip on a compliant, registered device explains the activity | `lookup_traveller`, `lookup_device` over `travellers.json` | `explained`, `confidence`, `evidence[]` |
| `response-agent` | Propose a disposition, draft the message to the user and cite the policy section | File Search over `policies/` | `disposition`, `requires_approval`, `policy_citation`, `user_message`, `rationale` |

Each agent returns strict JSON. `agents.py` validates every response with a Pydantic model before handing it to the next agent, so a malformed answer fails loudly instead of propagating. Two rules are enforced in code as well as in the prompts: `block_and_revoke` always requires approval, and so does any `leaked_credentials` alert.

The tools return pseudonymous ids only. Alerts carry IP addresses with the last octet masked. Nothing here is real.

## What to run

```bash
cd step-1-agents
python agents.py
```

The script uploads the four policy documents to a vector store called `wayfarer-policies` (reused on later runs), creates a new version of each agent, then triages the alerts one at a time. Each line shows the alert id, type, whether travel explained it, severity and disposition. Results are written to `results.jsonl`, which step 3 reads.

A run takes several minutes. Expect roughly 25 dismissals, a handful of MFA challenges, seven block proposals and three escalations, but the exact numbers vary between runs.

## What to look for

- In the Foundry portal, open Agents. All three agents are listed; select one to read its instructions and tools.
- Open `results.jsonl`. Pick an explained alert such as `A-1001` and read the evidence the travel-context agent recorded. Pick `A-1027` and check `requires_approval` is true and the citation is the leaked credentials section of the playbook.
- Pick an ambiguous alert such as `A-1038` (VPN egress) and see whether the response agent escalated rather than guessed.

## Success criteria

- [ ] Three agents are visible in the Foundry portal
- [ ] All 40 alerts are processed and `results.jsonl` has 40 lines with no `error` entries
- [ ] Every `block_and_revoke` and every `leaked_credentials` result has `requires_approval: true`
- [ ] Every non-dismiss result cites a policy file and section
