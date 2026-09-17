"""
Step 2: Enable GenAI tracing with content capture off and run one traced triage.

Usage:
    python monitor.py

Tracing environment variables must be set before azure.ai.projects is imported.
"""

import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv


def _find_repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / ".env").exists():
            return parent
    return Path(__file__).resolve().parents[1]


REPO_ROOT = _find_repo_root()
load_dotenv(REPO_ROOT / ".env")
sys.path.insert(0, str(REPO_ROOT / "step-1-agents"))

PROJECT_CONNECTION_STRING = os.getenv("PROJECT_CONNECTION_STRING")
APPINSIGHTS_CONN_STRING = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")


def check_tracing_settings():
    if os.getenv("AZURE_EXPERIMENTAL_ENABLE_GENAI_TRACING") != "true":
        print("AZURE_EXPERIMENTAL_ENABLE_GENAI_TRACING is not 'true' in .env")
        sys.exit(1)
    if os.getenv("OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT", "false") == "true":
        print("OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT must be 'false'.")
        print("Alert content contains identity data and must not be stored in traces (ai-use-policy.md section 4.4).")
        sys.exit(1)
    print("Tracing on, message content capture off")


def setup_tracing():
    from azure.ai.projects.telemetry import AIProjectInstrumentor
    from azure.monitor.opentelemetry import configure_azure_monitor

    AIProjectInstrumentor().instrument()
    configure_azure_monitor(connection_string=APPINSIGHTS_CONN_STRING, enable_live_metrics=True)
    print("Azure Monitor exporter connected")


def run_traced_triage():
    import agents

    client, openai_client = agents.connect()
    agents.ensure_agents_deployed(client, openai_client)
    alert = agents.load_alerts()[0]
    print(f"\nTriaging {alert['alert_id']} with tracing on...")
    result = agents.triage_alert(openai_client, alert)
    print(f"  {result['disposition']} ({result['severity']}), explained={result['explained']}")
    client.close()


def wait_for_traces():
    print("\nWaiting 30 seconds for traces to propagate...")
    time.sleep(30)
    print("Foundry portal: project -> Agents -> alert-triage-agent -> Traces")
    print("Azure portal: Application Insights -> Investigate -> Search, last 30 minutes")


def main():
    if not PROJECT_CONNECTION_STRING or not APPINSIGHTS_CONN_STRING:
        print("PROJECT_CONNECTION_STRING or APPLICATIONINSIGHTS_CONNECTION_STRING not set. Run step 0 first.")
        sys.exit(1)

    check_tracing_settings()
    setup_tracing()
    run_traced_triage()
    wait_for_traces()


if __name__ == "__main__":
    main()
