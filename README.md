# Wayfarer

Traveller-aware identity protection for a humanitarian NGO, built on Microsoft Foundry.

Aid Nordic staff travel constantly between headquarters and country programmes. Every arrival raises Entra ID and Defender identity alerts that look like account compromise. Wayfarer triages those alerts with three agents: one classifies the alert, one checks it against approved travel and device compliance, and one proposes a response grounded in Aid Nordic's own policies. Blocking actions are proposed, not taken. A person approves them.

Everything here is synthetic. Aid Nordic is fictional, the staff are fictional, and the alerts were written for this lab.

## Steps

| Step | Folder | What you do |
|---|---|---|
| 0 | `step-0-setup/` | Provision a Foundry project, model and Application Insights, or reuse one |
| 1 | `step-1-agents/` | Create the three agents and run 40 alerts through them |
| 2 | `step-2-monitor/` | Turn on tracing with content capture off and read the traces |
| 3 | `step-3-evaluate/` | Score the results against ground truth: disposition, severity and travel explanation |
| 4 | `step-4-workflow/` | Orchestrate the agents from code and expose them behind an Entra-protected API |

Each step has a README with what to run, what to look for and how to know it worked. Work through them in order.

## Getting started

Open the repository in a GitHub Codespace. The dev container installs the Azure CLI and the Python requirements. Then:

```bash
az login
bash step-0-setup/deploy.sh
```

Continue with `step-1-agents/README.md`.

## Layout

```
step-1-agents/    agents.py, tools.py, alerts.json, travellers.json, policies/
step-2-monitor/   monitor.py
step-3-evaluate/  evaluate.py, expected.jsonl, eval_portal.jsonl
step-4-workflow/  workflow.py, api.py
docs/             architecture.md, runbook.md
```

## Licence

MIT. See `LICENSE`.
