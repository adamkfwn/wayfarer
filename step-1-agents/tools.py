"""Function tools for the travel-context-agent. Both read travellers.json."""

import json
from pathlib import Path

from azure.ai.projects.models import FunctionTool

TRAVELLERS_PATH = Path(__file__).resolve().parent / "travellers.json"


def _load_travellers() -> list[dict]:
    with open(TRAVELLERS_PATH) as f:
        return json.load(f)["travellers"]


def lookup_traveller(user_id: str) -> str:
    traveller = next((t for t in _load_travellers() if t["user_id"] == user_id), None)
    if not traveller:
        return json.dumps({"error": f"Traveller '{user_id}' not found"})
    return json.dumps(traveller, indent=2)


def lookup_device(device_id: str) -> str:
    owner = next((t for t in _load_travellers() if t["device_id"] == device_id), None)
    if not owner:
        return json.dumps({"device_id": device_id, "registered": False})
    return json.dumps(
        {
            "device_id": device_id,
            "registered": True,
            "owner_user_id": owner["user_id"],
            "device_compliant": owner["device_compliant"],
        },
        indent=2,
    )


TOOL_FUNCTIONS = {"lookup_traveller": lookup_traveller, "lookup_device": lookup_device}


def call_tool(name: str, arguments: dict) -> str:
    function = TOOL_FUNCTIONS.get(name)
    if not function:
        return json.dumps({"error": f"Unknown tool '{name}'"})
    return function(**arguments)


def _string_param_tool(name: str, description: str, param: str, param_description: str) -> FunctionTool:
    return FunctionTool(
        name=name,
        description=description,
        parameters={
            "type": "object",
            "properties": {param: {"type": "string", "description": param_description}},
            "required": [param],
            "additionalProperties": False,
        },
        strict=False,
    )


LOOKUP_TRAVELLER_TOOL = _string_param_tool(
    "lookup_traveller",
    "Look up a staff member by pseudonymous user id. Returns role, home country, registered "
    "device, device compliance, MFA method and approved trips with dates and approver.",
    "user_id",
    "Pseudonymous user id, for example 'u-0417'",
)

LOOKUP_DEVICE_TOOL = _string_param_tool(
    "lookup_device",
    "Look up a device by id. Returns whether it is registered, who owns it and whether it is compliant.",
    "device_id",
    "Device id, for example 'd-1417'",
)

LOOKUP_TOOLS = [LOOKUP_TRAVELLER_TOOL, LOOKUP_DEVICE_TOOL]
