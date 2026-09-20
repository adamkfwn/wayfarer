"""
Step 3: Evaluate the step 1 results against expected.jsonl.

Usage:
    python evaluate.py

Runs exact match on disposition, severity and explained, and uploads the run
to the Foundry project.
"""

import json
import os
import sys
from pathlib import Path

from azure.ai.evaluation import evaluate
from dotenv import load_dotenv


def _find_repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / ".env").exists():
            return parent
    return Path(__file__).resolve().parents[1]


REPO_ROOT = _find_repo_root()
load_dotenv(REPO_ROOT / ".env")

PROJECT_CONNECTION_STRING = os.getenv("PROJECT_CONNECTION_STRING")

STEP_DIR = Path(__file__).resolve().parent
STEP1_DIR = REPO_ROOT / "step-1-agents"
RESULTS_PATH = STEP1_DIR / "results.jsonl"
EXPECTED_PATH = STEP_DIR / "expected.jsonl"
EVAL_DATA_PATH = STEP_DIR / "eval_data.jsonl"
OUTPUT_PATH = STEP_DIR / "evaluation_results.json"

MATCH_THRESHOLD = 0.9

TASK = (
    "Triage this Aid Nordic identity alert: classify it, decide whether approved travel explains it, "
    "and propose a disposition with a policy citation. Block and revoke and leaked credentials require approval."
)


def load_jsonl(path: Path) -> list[dict]:
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def load_alerts_by_id() -> dict[str, dict]:
    with open(STEP1_DIR / "alerts.json") as f:
        return {alert["alert_id"]: alert for alert in json.load(f)["alerts"]}


def build_eval_rows() -> list[dict]:
    expected = {row["alert_id"]: row for row in load_jsonl(EXPECTED_PATH)}
    alerts = load_alerts_by_id()
    results = [r for r in load_jsonl(RESULTS_PATH) if "error" not in r]
    return [_eval_row(r, expected[r["alert_id"]], alerts[r["alert_id"]]) for r in results]


def _eval_row(result: dict, expected: dict, alert: dict) -> dict:
    return {
        "alert_id": result["alert_id"],
        "query": f"{TASK}\n\nAlert:\n{json.dumps(alert)}",
        "response": json.dumps(result),
        "ground_truth": json.dumps(
            {
                "disposition": expected["expected_disposition"],
                "severity": expected["expected_severity"],
                "explained": expected["expected_explained"],
            }
        ),
    }


def exact_match(*, response: str, ground_truth: str) -> dict:
    actual, expected = json.loads(response), json.loads(ground_truth)
    return {
        "disposition_match": float(actual.get("disposition") == expected["disposition"]),
        "severity_match": float(actual.get("severity") == expected["severity"]),
        "explained_match": float(actual.get("explained") == expected["explained"]),
    }


def run_evaluation(rows: list[dict]) -> dict:
    with open(EVAL_DATA_PATH, "w") as f:
        f.writelines(json.dumps(row) + "\n" for row in rows)
    return evaluate(
        data=str(EVAL_DATA_PATH),
        evaluation_name="wayfarer-triage",
        evaluators={"exact_match": exact_match},
        azure_ai_project=PROJECT_CONNECTION_STRING,
        output_path=str(OUTPUT_PATH),
    )


def print_report(result: dict) -> bool:
    metrics = result["metrics"]
    print("\n=== Aggregate ===")
    for name, value in sorted(metrics.items()):
        print(f"  {name:<40} {value}")

    print("\n=== Per row ===")
    for row in result["rows"]:
        print(
            f"  {row['inputs.alert_id']}  "
            f"disposition={row.get('outputs.exact_match.disposition_match')}  "
            f"severity={row.get('outputs.exact_match.severity_match')}  "
            f"explained={row.get('outputs.exact_match.explained_match')}"
        )

    disposition = metrics.get("exact_match.disposition_match", 0.0)
    severity = metrics.get("exact_match.severity_match", 0.0)
    passed = disposition >= MATCH_THRESHOLD and severity >= MATCH_THRESHOLD
    print("\n=== Thresholds ===")
    print(f"  disposition match {disposition:.2f} (need >= {MATCH_THRESHOLD})")
    print(f"  severity match    {severity:.2f} (need >= {MATCH_THRESHOLD})")
    print(f"  {'PASS' if passed else 'FAIL'}")
    if result.get("studio_url"):
        print(f"\nPortal: {result['studio_url']}")
    return passed


def main():
    if not PROJECT_CONNECTION_STRING:
        print("PROJECT_CONNECTION_STRING not set. Run step 0 first.")
        sys.exit(1)
    if not RESULTS_PATH.exists():
        print(f"{RESULTS_PATH} not found. Run step 1 first.")
        sys.exit(1)

    rows = build_eval_rows()
    print(f"Evaluating {len(rows)} triage results...")
    passed = print_report(run_evaluation(rows))
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()