#!/bin/bash
set -euo pipefail

# Wayfarer infrastructure. Provisions Foundry (account, project, model), Log Analytics and
# Application Insights, then writes .env at the repo root. Reuses an existing .env if present.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$ROOT_DIR/.env"

if [ -f "$ENV_FILE" ] && grep -q '^PROJECT_CONNECTION_STRING=.\+' "$ENV_FILE"; then
    echo "Found $ENV_FILE with a project connection string. Reusing the existing project."
    grep -E '^(RESOURCE_GROUP|FOUNDRY_RESOURCE_NAME|PROJECT_NAME|MODEL_DEPLOYMENT_NAME)=' "$ENV_FILE"
    echo "Delete .env to provision a new project."
    exit 0
fi

az config set extension.use_dynamic_install=yes_without_prompt --only-show-errors >/dev/null 2>&1 || true
az extension add --name application-insights --only-show-errors >/dev/null 2>&1 || true

SUFFIX="${SUFFIX:-$(openssl rand -hex 4)}"
RESOURCE_GROUP="${RESOURCE_GROUP:-wayfarer-rg-$SUFFIX}"
LOCATION="${LOCATION:-swedencentral}"
FOUNDRY_RESOURCE_NAME="${FOUNDRY_RESOURCE_NAME:-wayfarer-$SUFFIX}"
PROJECT_NAME="${PROJECT_NAME:-wayfarer-project}"
MODEL_DEPLOYMENT_NAME="${MODEL_DEPLOYMENT_NAME:-gpt-5.4}"
MODEL_NAME="${MODEL_NAME:-gpt-5.4}"
MODEL_VERSION="${MODEL_VERSION:-2026-03-05}"
LOG_ANALYTICS_NAME="${LOG_ANALYTICS_NAME:-wayfarer-logs-$SUFFIX}"
APP_INSIGHTS_NAME="${APP_INSIGHTS_NAME:-wayfarer-insights-$SUFFIX}"

TAGS=("environment=hack" "project=wayfarer")
while [[ $# -gt 0 ]]; do
    case "$1" in
        --tags)
            shift
            while [[ $# -gt 0 && "$1" != --* ]]; do
                TAGS+=("$1")
                shift
            done
            ;;
        *)
            echo "Unknown argument: $1" >&2
            echo "Usage: deploy.sh [--tags 'Key=Value' ...]" >&2
            exit 1
            ;;
    esac
done

echo "Wayfarer infrastructure deploy"
echo "  Resource group:   $RESOURCE_GROUP"
echo "  Location:         $LOCATION"
echo "  Foundry resource: $FOUNDRY_RESOURCE_NAME"
echo "  Project:          $PROJECT_NAME"
echo "  Model:            $MODEL_NAME $MODEL_VERSION as $MODEL_DEPLOYMENT_NAME"
echo "  Tags:             ${TAGS[*]}"
echo ""

echo ">>> Creating resource group..."
az group create --name "$RESOURCE_GROUP" --location "$LOCATION" --output none --tags "${TAGS[@]}"

echo ">>> Creating Foundry account (AIServices)..."
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
TENANT_ID=$(az account show --query tenantId -o tsv)
az rest \
    --method PUT \
    --url "https://management.azure.com/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.CognitiveServices/accounts/$FOUNDRY_RESOURCE_NAME?api-version=2026-03-01" \
    --body "{\"kind\": \"AIServices\", \"sku\": {\"name\": \"S0\"}, \"location\": \"$LOCATION\", \"identity\": {\"type\": \"SystemAssigned\"}, \"properties\": {\"customSubDomainName\": \"$FOUNDRY_RESOURCE_NAME\", \"publicNetworkAccess\": \"Enabled\", \"allowProjectManagement\": true}}" \
    --output none || true

echo ">>> Waiting for the account to reach Succeeded..."
for i in $(seq 1 36); do
    PROV_STATE=$(az cognitiveservices account show \
        --name "$FOUNDRY_RESOURCE_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --query "properties.provisioningState" -o tsv 2>/dev/null || echo "Pending")
    if [ "$PROV_STATE" = "Succeeded" ]; then
        echo "    Provisioning complete."
        break
    elif [ "$PROV_STATE" = "Failed" ]; then
        echo "Account provisioning failed. Check the Azure portal." >&2
        exit 1
    fi
    echo "    State: $PROV_STATE, retrying in 10s ($i/36)"
    sleep 10
done

FOUNDRY_RESOURCE_ID=$(az cognitiveservices account show \
    --name "$FOUNDRY_RESOURCE_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query id -o tsv)

az resource update --ids "$FOUNDRY_RESOURCE_ID" --set properties.disableLocalAuth=false --output none || true
az resource update --ids "$FOUNDRY_RESOURCE_ID" --set properties.allowProjectManagement=true --output none

DISABLE_LOCAL_AUTH=$(az cognitiveservices account show \
    --name "$FOUNDRY_RESOURCE_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query properties.disableLocalAuth -o tsv)
if [ "$DISABLE_LOCAL_AUTH" = "true" ]; then
    echo "    Key authentication is disabled by policy on this tenant. The scripts use Entra ID, so this is fine."
fi

echo ">>> Creating Foundry project..."
az cognitiveservices account project create \
    --name "$FOUNDRY_RESOURCE_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --project-name "$PROJECT_NAME" \
    --location "$LOCATION" \
    --output none

echo ">>> Deploying model $MODEL_NAME ($MODEL_VERSION)..."
az cognitiveservices account deployment create \
    --name "$FOUNDRY_RESOURCE_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --deployment-name "$MODEL_DEPLOYMENT_NAME" \
    --model-name "$MODEL_NAME" \
    --model-version "$MODEL_VERSION" \
    --model-format OpenAI \
    --sku-capacity 10 \
    --sku-name GlobalStandard \
    --output none

echo ">>> Creating Log Analytics workspace..."
az monitor log-analytics workspace create \
    --resource-group "$RESOURCE_GROUP" \
    --workspace-name "$LOG_ANALYTICS_NAME" \
    --location "$LOCATION" \
    --output none

LOG_ANALYTICS_ID=$(az monitor log-analytics workspace show \
    --resource-group "$RESOURCE_GROUP" \
    --workspace-name "$LOG_ANALYTICS_NAME" \
    --query id -o tsv)

echo ">>> Creating Application Insights..."
az monitor app-insights component create \
    --app "$APP_INSIGHTS_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --location "$LOCATION" \
    --workspace "$LOG_ANALYTICS_ID" \
    --output none

APP_INSIGHTS_CONN_STRING=$(az monitor app-insights component show \
    --app "$APP_INSIGHTS_NAME" --resource-group "$RESOURCE_GROUP" --query connectionString -o tsv)
APP_INSIGHTS_INSTRUMENTATION_KEY=$(az monitor app-insights component show \
    --app "$APP_INSIGHTS_NAME" --resource-group "$RESOURCE_GROUP" --query instrumentationKey -o tsv)
APP_INSIGHTS_RESOURCE_ID=$(az monitor app-insights component show \
    --app "$APP_INSIGHTS_NAME" --resource-group "$RESOURCE_GROUP" --query id -o tsv)

echo ">>> Connecting Application Insights to the Foundry account..."
if ! az rest \
    --method PUT \
    --url "https://management.azure.com/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.CognitiveServices/accounts/$FOUNDRY_RESOURCE_NAME/connections/appinsights-conn?api-version=2025-06-01" \
    --body "{\"properties\": {\"category\": \"AppInsights\", \"target\": \"$APP_INSIGHTS_RESOURCE_ID\", \"authType\": \"ApiKey\", \"credentials\": {\"key\": \"$APP_INSIGHTS_CONN_STRING\"}, \"isSharedToAll\": true, \"metadata\": {\"ApiType\": \"Azure\", \"ResourceId\": \"$APP_INSIGHTS_RESOURCE_ID\"}}}" \
    --output none; then
    echo "    Could not link Application Insights automatically. Connect it from the Foundry portal in step 2."
fi

echo ">>> Retrieving endpoints..."
FOUNDRY_ENDPOINT=$(az cognitiveservices account show \
    --name "$FOUNDRY_RESOURCE_NAME" --resource-group "$RESOURCE_GROUP" --query "properties.endpoint" -o tsv)
PROJECT_CONNECTION_STRING=$(az cognitiveservices account project show \
    --name "$FOUNDRY_RESOURCE_NAME" --resource-group "$RESOURCE_GROUP" --project-name "$PROJECT_NAME" \
    --query "properties.endpoints.\"AI Foundry API\"" -o tsv)

echo ">>> Writing $ENV_FILE"
cat > "$ENV_FILE" << EOF_ENV
# Wayfarer environment variables. Generated by deploy.sh on $(date). Do not commit.

# Azure subscription
AZURE_SUBSCRIPTION_ID=$SUBSCRIPTION_ID
RESOURCE_GROUP=$RESOURCE_GROUP

# Microsoft Foundry
FOUNDRY_RESOURCE_NAME=$FOUNDRY_RESOURCE_NAME
PROJECT_NAME=$PROJECT_NAME
FOUNDRY_ENDPOINT=$FOUNDRY_ENDPOINT
PROJECT_CONNECTION_STRING=$PROJECT_CONNECTION_STRING
MODEL_DEPLOYMENT_NAME=$MODEL_DEPLOYMENT_NAME

# Application Insights
APPLICATIONINSIGHTS_CONNECTION_STRING=$APP_INSIGHTS_CONN_STRING
APPINSIGHTS_INSTRUMENTATION_KEY=$APP_INSIGHTS_INSTRUMENTATION_KEY

# Tracing. Content capture stays off: alert content is identity data.
AZURE_EXPERIMENTAL_ENABLE_GENAI_TRACING=true
OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=false

# Step 4 API. Set API_AUDIENCE to the app registration's client id or application id URI.
ENTRA_TENANT_ID=$TENANT_ID
API_AUDIENCE=
EOF_ENV

echo ""
echo "Deployment complete. .env written to $ENV_FILE"
