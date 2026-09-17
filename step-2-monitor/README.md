# Step 2: Monitor

Time: about 20 minutes.

## Objective

GenAI tracing switched on for the Wayfarer agents, with message content capture switched off, and a traced triage visible in the Foundry portal and Application Insights.

## Why content capture is off

Tracing records every agent call: timing, token counts, tool calls, status. With `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=true` it also records the full prompt and response. For Wayfarer those contain sign-in locations, device ids and travel dates for named staff. Aid Nordic's AI use policy (section 4.4) says that content must not be stored in monitoring traces, so `deploy.sh` writes the variable as `false` and `monitor.py` refuses to run if it is `true`.

You still get latency, cost, tool-call counts, errors and the outcome of each run. You lose the ability to read what the model saw from the trace alone. That is the trade: the evidence trail lives in `results.jsonl` and the evaluation in step 3, not in the telemetry.

## What to run

Check `.env` has:

```
AZURE_EXPERIMENTAL_ENABLE_GENAI_TRACING=true
OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=false
APPLICATIONINSIGHTS_CONNECTION_STRING=...
```

Then:

```bash
cd step-2-monitor
python monitor.py
```

The script instruments the SDK, connects the Azure Monitor exporter, reuses the agents from step 1 (creating them if missing), triages the first alert and waits 30 seconds for the trace to land.

## What to look for

In the Foundry portal, open the project and select Tracing. If you see a banner asking you to connect an Application Insights resource, select Connect and choose `wayfarer-insights-<suffix>`. Then open Agents, select `alert-triage-agent` and its Traces tab. Open the newest conversation. You should see one span per agent call, the two function calls made by `travel-context-agent`, the file search made by `response-agent`, and token counts. The message bodies are absent.

In the Azure portal, open the Application Insights resource, then Investigate and Search, and set the range to the last 30 minutes. Open the end-to-end transaction for the triage. Under Investigate, Agents (preview) shows runs, tool calls and token consumption per agent.

## Success criteria

- [ ] `monitor.py` runs to completion and refuses to run if content capture is on
- [ ] The triage appears in the Foundry Traces view with spans for all three agents and their tool calls
- [ ] The same run is visible in Application Insights transaction search
- [ ] No prompt or response text appears in any span
