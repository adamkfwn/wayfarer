"""
Step 4: Code orchestration of the three agents with a JSON handoff and a shift summary.

Usage:
    python workflow.py
"""

import json
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "step-1-agents"))

import agents

SUMMARY_PATH = Path(__file__).resolve().parent / "shift_summary.json"


def run_shift(openai_client, alerts: list[dict]) -> dict:
    results = agents.triage_all(openai_client, alerts)
    return {"results": results, "summary": summarise(results)}


def summarise(results: list[dict]) -> dict:
    triaged = [r for r in results if "error" not in r]
    return {
        "alerts": len(results),
        "failed": len(results) - len(triaged),
        "explained_by_travel": sum(r["explained"] for r in triaged),
        "by_disposition": dict(Counter(r["disposition"] for r in triaged)),
        "by_severity": dict(Counter(r["severity"] for r in triaged)),
        "awaiting_approval": [
            {"alert_id": r["alert_id"], "user_id": r["user_id"], "disposition": r["disposition"]}
            for r in triaged
            if r["requires_approval"]
        ],
        "escalated": [r["alert_id"] for r in triaged if r["disposition"] == "escalate_human"],
    }


def print_shift_summary(summary: dict) -> None:
    print("\n" + "=" * 60)
    print("AID NORDIC IDENTITY SHIFT SUMMARY")
    print("=" * 60)
    print(f"  Alerts processed       : {summary['alerts']} ({summary['failed']} failed)")
    print(f"  Explained by travel    : {summary['explained_by_travel']}")
    print(f"  By disposition         : {summary['by_disposition']}")
    print(f"  By severity            : {summary['by_severity']}")
    print(f"  Escalated to analyst   : {', '.join(summary['escalated']) or 'none'}")
    print("\n  Awaiting approval:")
    for item in summary["awaiting_approval"] or [{"alert_id": "none", "user_id": "", "disposition": ""}]:
        print(f"    {item['alert_id']}  {item['user_id']}  {item['disposition']}")
    print("=" * 60)


def main():
    if not agents.PROJECT_CONNECTION_STRING:
        print("PROJECT_CONNECTION_STRING not set. Run step 0 first.")
        sys.exit(1)

    client, openai_client = agents.connect()
    print("=== Ensuring agents are deployed ===")
    agents.ensure_agents_deployed(client, openai_client)

    alerts = agents.load_alerts()
    print(f"\n=== Running shift: {len(alerts)} alerts ===")
    shift = run_shift(openai_client, alerts)
    print_shift_summary(shift["summary"])

    SUMMARY_PATH.write_text(json.dumps(shift, indent=2) + "\n")
    print(f"\nWritten to {SUMMARY_PATH.name}")
    client.close()


if __name__ == "__main__":
    main()
