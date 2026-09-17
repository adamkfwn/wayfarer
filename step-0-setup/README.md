# Step 0: Setup

Time: about 20 minutes.

## Objective

A Microsoft Foundry project with a deployed model and Application Insights, and a `.env` file at the repository root that every later step reads.

## Prerequisites

- An Azure subscription where you hold Contributor on the subscription or resource group and Foundry User on the Foundry account. Contributor alone cannot run agents; ask an admin to assign Foundry User after deployment if you cannot self-assign it.
- The repository open in a GitHub Codespace. The dev container installs the Azure CLI and the Python requirements.

## What to run

```bash
az login
bash step-0-setup/deploy.sh
```

The script provisions a resource group in Sweden Central with a Foundry account, a project called `wayfarer-project`, a `gpt-5.4` deployment, a Log Analytics workspace and Application Insights. It writes `.env` at the repository root.

If `.env` already exists with a project connection string, the script prints the project it found and exits without touching Azure. Delete `.env` to provision a new project.

Override names by exporting `RESOURCE_GROUP`, `LOCATION` or `MODEL_DEPLOYMENT_NAME` before running. Add resource tags with `--tags Owner=you`.

## What to look for

- In the Azure portal, the resource group contains the Foundry account, project, Log Analytics workspace and Application Insights.
- In the Foundry portal, open the project, select Build then Models, and check `gpt-5.4` shows Succeeded. Send a test message in the playground.
- `.env` contains `PROJECT_CONNECTION_STRING`, `FOUNDRY_ENDPOINT` and `APPLICATIONINSIGHTS_CONNECTION_STRING`. `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT` is `false`; step 2 explains why.

`.env` is ignored by git. Never commit it.

## Success criteria

- [ ] The resource group and its resources are visible in the Azure portal
- [ ] The model deployment shows Succeeded and answers in the playground
- [ ] `.env` exists at the repository root with the values above
