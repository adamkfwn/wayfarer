"""
Step 3: Evaluate the step 1 results against expected.jsonl.

Usage:
    python evaluate.py

Runs exact match on disposition, severity and explained, plus groundedness and
task adherence, and uploads the run to the Foundry project.
"""

import json
import os
import sys
from pathlib import Path

from azure.ai.evaluation import (
    AzureOpenAIModelConfiguration,
    GroundednessEvaluator,
    TaskAdherenceEvaluator,
    evaluate,
)
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv


def _find_repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / ".env").exists():
            return parent
    return Path(__file__).resolve().parents[1]


REPO_ROOT = _find_repo_root()
load_dotenv(REPO_ROOT / ".env")

PROJECT_CONNECTION_STRING = os.getenv("PROJECT_CONNECTION_STRING")
FOUNDRY_ENDPOINT = os.getenv("FOUNDRY_ENDPOINT")
MODEL_DEPLOYMENT_NAME = os.getenv("MODEL_DEPLOYMENT_NAME", "gpt-5.4")

STEP_DIR = Path(__file__).resolve().parent
STEP1_DIR = REPO_ROOT / "step-1-agents"
RESULTS_PATH = STEP1_DIR / "results.jsonl"
EXPECTED_PATH = STEP_DIR / "expected.jsonl"
PLAYBOOK_PATH = STEP1_DIR / "policies" / "incident-playbook.md"
EVAL_DATA_PATH = STEP_DIR / "eval_data.jsonl"
OUTPUT_PATH = STEP_DIR / "evaluation_results.json"

DISPOSITION_MATCH_THRESHOLD = 0.9
GROUNDEDNESS_THRESHOLD = 4.0

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


def load_travellers_by_id() -> dict[str, dict]:
    with open(STEP1_DIR / "travellers.json") as f:
        return {t["user_id"]: t for t in json.load(f)["travellers"]}


def build_eval_rows() -> list[dict]:
    expected = {row["alert_id"]: row for row in load_jsonl(EXPECTED_PATH)}
    alerts = load_alerts_by_id()
    travellers = load_travellers_by_id()
    playbook = PLAYBOOK_PATH.read_text()
    results = [r for r in load_jsonl(RESULTS_PATH) if "error" not in r]
    return [
        _eval_row(r, expected[r["alert_id"]], alerts[r["alert_id"]], travellers[r["user_id"]], playbook)
        for r in results
    ]


def _eval_row(result: dict, expected: dict, alert: dict, traveller: dict, playbook: str) -> dict:
    return {
        "alert_id": result["alert_id"],
        "query": f"{TASK}\n\nAlert:\n{json.dumps(alert)}",
        "response": json.dumps(result),
        "context": f"Alert:\n{json.dumps(alert)}\n\nTraveller:\n{json.dumps(traveller)}\n\nPlaybook:\n{playbook}",
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


def model_config() -> AzureOpenAIModelConfiguration:
    return AzureOpenAIModelConfiguration(
        azure_endpoint=FOUNDRY_ENDPOINT,
        azure_deployment=MODEL_DEPLOYMENT_NAME,
        credential=DefaultAzureCredential(),
    )


def run_evaluation(rows: list[dict]) -> dict:
    with open(EVAL_DATA_PATH, "w") as f:
        f.writelines(json.dumps(row) + "\n" for row in rows)
    config = model_config()
    return evaluate(
        data=str(EVAL_DATA_PATH),
        evaluation_name="wayfarer-triage",
        evaluators={
            "exact_match": exact_match,
            "groundedness": GroundednessEvaluator(config),
            "task_adherence": TaskAdherenceEvaluator(config),
        },
        azure_ai_project=PROJECT_CONNECTION_STRING,
        output_path=str(OUTPUT_PATH),
    )


def print_report(result: dict) -> bool:
    metrics = result["metrics"]
    print("\n=== Aggregate ===")
    for name, value in sorted(metrics.items()):
        print(f"  {name:<45} {value}")

    print("\n=== Per row ===")
    for row in result["rows"]:
        print(
            f"  {row['inputs.alert_id']}  disposition_match={row.get('outputs.exact_match.disposition_match')}  "
            f"groundedness={row.get('outputs.groundedness.groundedness')}  "
            f"task_adherence={row.get('outputs.task_adherence.task_adherence')}"
        )

    disposition_match = metrics.get("exact_match.disposition_match", 0.0)
    groundedness = metrics.get("groundedness.groundedness", 0.0)
    passed = disposition_match >= DISPOSITION_MATCH_THRESHOLD and groundedness >= GROUNDEDNESS_THRESHOLD
    print("\n=== Thresholds ===")
    print(f"  disposition match {disposition_match:.2f} (need >= {DISPOSITION_MATCH_THRESHOLD})")
    print(f"  groundedness      {groundedness:.2f} (need >= {GROUNDEDNESS_THRESHOLD})")
    print(f"  {'PASS' if passed else 'FAIL'}")
    if result.get("studio_url"):
        print(f"\nPortal: {result['studio_url']}")
    return passed


def main():
    if not PROJECT_CONNECTION_STRING or not FOUNDRY_ENDPOINT:
        print("PROJECT_CONNECTION_STRING or FOUNDRY_ENDPOINT not set. Run step 0 first.")
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
