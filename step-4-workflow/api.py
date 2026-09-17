"""
Step 4: HTTP front door for the triage workflow, protected by Entra ID bearer tokens.

Usage:
    uvicorn api:app --reload
"""

import json
import os
import sys
import urllib.error
import urllib.request
from functools import lru_cache
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "step-1-agents"))

import agents

TENANT_ID = os.getenv("ENTRA_TENANT_ID")
API_AUDIENCE = os.getenv("API_AUDIENCE")
if not TENANT_ID or not API_AUDIENCE:
    sys.exit("ENTRA_TENANT_ID and API_AUDIENCE must be set in .env")

JWKS_URL = f"https://login.microsoftonline.com/{TENANT_ID}/discovery/v2.0/keys"
ISSUER = f"https://login.microsoftonline.com/{TENANT_ID}/v2.0"

bearer = HTTPBearer()
app = FastAPI(title="Wayfarer triage API")
PROJECT_CLIENT, OPENAI_CLIENT = agents.connect()
agents.ensure_agents_deployed(PROJECT_CLIENT, OPENAI_CLIENT)


class Alert(BaseModel):
    alert_id: str
    user_id: str
    device_id: str
    alert_type: agents.AlertType
    timestamp: str
    location: str
    ip_masked: str
    detail: str


@lru_cache
def fetch_jwks() -> dict:
    with urllib.request.urlopen(JWKS_URL) as response:
        return json.load(response)


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(bearer)) -> dict:
    try:
        jwks = fetch_jwks()
    except urllib.error.URLError as error:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, f"Cannot fetch tenant keys: {error}") from error
    try:
        return jwt.decode(credentials.credentials, jwks, algorithms=["RS256"], audience=API_AUDIENCE, issuer=ISSUER)
    except JWTError as error:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"Invalid token: {error}") from error


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/triage")
def triage(alert: Alert, claims: dict = Depends(verify_token)) -> dict:
    result = agents.triage_alert(OPENAI_CLIENT, alert.model_dump())
    result["requested_by"] = claims.get("oid")
    return result
