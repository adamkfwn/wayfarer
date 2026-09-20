# Step 3: Evaluate

Time: about 30 minutes.

## Objective

A scored evaluation of the step 1 results against known correct outcomes, uploaded to the Foundry project, with pass or fail against agreed thresholds.

## The dataset

`expected.jsonl` has one line per alert: `alert_id`, `expected_disposition`, `expected_severity`, `expected_explained` and a `reason` that names the playbook section. The 40 alerts split into 25 explained by approved travel, 10 genuinely suspicious and 5 ambiguous. The ambiguous ones are the interesting rows: a trip that ended yesterday, a personal device during a trip, a VPN egress, an early arrival and a transit hub.

`eval_portal.jsonl` is the same data in the portal's upload format, with the traveller context embedded in each `query` so an agent can answer without calling tools.

## The evaluators

`evaluate.py` runs three evaluators over `step-1-agents/results.jsonl`:

- Exact match. Compares `disposition`, `severity` and `explained` with the expected values. Deterministic.
- Groundedness and task adherence can be run in the portal against `eval_portal.jsonl` (see below). They are not part of the gate.
- Task adherence. An LLM judge checks whether the response did what the task asked: classify, check travel, propose a disposition with a citation, flag approval where required.

Thresholds: disposition match and severity match at least 0.9. The script exits non-zero if either is missed, so it can gate a pipeline.## What to run

Step 1 must have produced `results.jsonl`. Then:

```bash
cd step-3-evaluate
python evaluate.py
```

The script builds `eval_data.jsonl`, runs the evaluators using your `gpt-5.4` deployment as the judge, writes `evaluation_results.json` and prints a portal link.

To run the same dataset in the portal instead, open Build, Evaluations, Create, choose `response-agent` as the target, upload `eval_portal.jsonl` and keep only Groundedness and Task Adherence. Deselect Tool Call Accuracy: the portal cannot run the local tools.

## How to read the results

The aggregate is one number per evaluator across all rows. It is the baseline you track between prompt changes. The per-row table shows which alerts missed. Sort by disposition match first: a wrong disposition on `A-1027` or `A-1032` (leaked credentials) is a safety failure; a wrong one on `A-1038` (VPN egress) is a judgement call worth reading. Then look at rows with groundedness below 4 and compare the rationale with the evidence.

## Success criteria

- [ ] The evaluation runs over all rows without evaluator errors
- [ ] Aggregate and per-row scores are printed and the run appears in the Foundry portal
- [ ] Disposition match is at least 0.9 and groundedness at least 4.0, or you can explain each miss
- [ ] You have found at least one row where a prompt change would help
