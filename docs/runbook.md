# Wayfarer runbook

For the analyst on the IT Security duty rota. Wayfarer proposes; you decide.

## Daily run

1. Confirm `.env` is present and `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=false`.
2. Run the shift:

   ```bash
   cd step-4-workflow
   python workflow.py
   ```

3. Read the shift summary. Work the approval queue first, then the escalations, then spot-check dismissals.
4. File `shift_summary.json` with the day's record. It contains pseudonymous ids only.

## Working a proposal

For each result, read in this order: `disposition`, `requires_approval`, `policy_citation`, `evidence`, `rationale`. Open the cited section and check it says what the rationale claims. If it does not, treat the case as an escalation.

| Disposition | What it means | What you do |
|---|---|---|
| `dismiss` | Approved travel on a compliant registered device explains the alert | Nothing. Reviewed weekly in aggregate. |
| `require_mfa` | Not explained, not clearly hostile | Confirm the user's MFA method is app or key, then trigger re-authentication. Send the drafted message. |
| `block_and_revoke` | Credential compromise indicated | Approve or reject. On approval, revoke sessions, reset the password, then send the drafted message. Record your name against the alert id. |
| `escalate_human` | No rule fits or the rule says ask | Contact the traveller through the country office. Decide. Record the outcome and, if a rule was missing, propose a playbook change. |

Never execute a `block_and_revoke` that lacks `requires_approval: true`. It means the code guard failed; stop and raise it.

## Messages to users

The drafted `user_message` states what was observed, what is proposed and what the user should do. Check it contains no IP address or device id and that it says the decision was prepared with AI assistance and reviewed by IT Security. Edit freely. It is a draft.

## When something looks wrong

Wrong disposition on a clear case: rerun the single alert through `agents.triage_alert` and compare. If it repeats, the prompt or the playbook wording is at fault. Change one, rerun step 3, and keep the result with the change.

Agent failed with a JSON error: the result line has an `error` field. The run continues past it. Rerun that alert on its own. If several fail in one shift, check the model deployment in the Foundry portal.

Severity or disposition match dropped in step 3: read the failing rows. A wrong disposition with the right citation is a prompt problem. A wrong citation is a retrieval problem; check the vector store has all four policy files.

Tracing shows no runs: confirm Application Insights is connected under Tracing in the Foundry portal and that `monitor.py` passes its checks.

## Changing the agents

Edit the instructions in `step-1-agents/agents.py`, then run `python agents.py` to create a new version and reprocess all alerts, then `python evaluate.py`. Do not put a changed agent into daily use until the thresholds pass. Keep `evaluation_results.json` with the change.

Edit a policy in `step-1-agents/policies/`, then delete the `wayfarer-policies` vector store in the Foundry portal so the next run re-uploads. Rerun steps 1 and 3.

## Access

Running the scripts needs Foundry User on the Foundry account and a signed-in `az login`. Calling the API needs a token for the API's app registration. Nobody, including the API, has permission to change accounts; that stays with the analyst's own Entra role.

## Retention

`results.jsonl` and `shift_summary.json` hold pseudonymous ids and masked IPs and are kept for 12 months under the incident playbook. Traces in Application Insights hold no message content and follow the workspace retention.
