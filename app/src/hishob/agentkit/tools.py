"""The citizen desk's tools, answered through the query API under the resident's tier (SPEC-008; C8).

Every tool is a read. Results are trimmed of geometry and per-property provenance to save tokens, but keep
each item's fact id, source, page and quote so the agent can cite them.
"""

from __future__ import annotations

import json
from typing import Any

DROP = {"geometry_wkt", "provenance"}

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "custom",
        "name": "find_place",
        "description": "Find roads and wards by name, in English, Marathi or Hindi. Returns node ids.",
        "input_schema": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]},
    },
    {
        "type": "custom",
        "name": "locate",
        "description": "Given a latitude and longitude, return the nearest road within 50 m and the ward.",
        "input_schema": {
            "type": "object",
            "properties": {"lat": {"type": "number"}, "lon": {"type": "number"}},
            "required": ["lat", "lon"],
        },
    },
    {
        "type": "custom",
        "name": "trace_money",
        "description": "For a road, work or tender id: budget, work, tender, award, contract, contractor, defect "
        "liability period and payments, each with fact id and source; and the records that are missing.",
        "input_schema": {"type": "object", "properties": {"node_id": {"type": "string"}}, "required": ["node_id"]},
    },
    {
        "type": "custom",
        "name": "who_is_responsible",
        "description": "For a road or other asset and an issue (pothole, open_manhole, waterlogging, incomplete_work): "
        "owning agency, department, responsible post, escalation chain, and any contractor still "
        "under defect liability, each with fact id and source.",
        "input_schema": {
            "type": "object",
            "properties": {"asset_id": {"type": "string"}, "issue": {"type": "string"}},
            "required": ["asset_id"],
        },
    },
    {
        "type": "custom",
        "name": "work_status",
        "description": "For a work id: due date, whether overdue, and the history of due-date changes.",
        "input_schema": {"type": "object", "properties": {"work_id": {"type": "string"}}, "required": ["work_id"]},
    },
    {
        "type": "custom",
        "name": "gaps_for",
        "description": "Records we do not hold about a road or work, and which office holds them.",
        "input_schema": {"type": "object", "properties": {"node_id": {"type": "string"}}, "required": ["node_id"]},
    },
    {
        "type": "custom",
        "name": "get_fact",
        "description": "The full record behind a fact id: document, page and exact quote.",
        "input_schema": {"type": "object", "properties": {"fact_id": {"type": "string"}}, "required": ["fact_id"]},
    },
]
WARD_SUMMARY: dict[str, Any] = {
    "type": "custom",
    "name": "ward_summary",
    "description": "For a ward code such as K/W: assets, works, tenders, estimated cost and what is overdue.",
    "input_schema": {"type": "object", "properties": {"ward": {"type": "string"}}, "required": ["ward"]},
}
# The audit lead (SPEC-011) reads the same views, plus the ward summary; it has no use for a point lookup.
AUDIT_TOOL_DEFINITIONS = [WARD_SUMMARY] + [t for t in TOOL_DEFINITIONS if t["name"] != "locate"]
READ_ONLY_TOOLS = {t["name"] for t in TOOL_DEFINITIONS}
AUDIT_TOOLS = {t["name"] for t in AUDIT_TOOL_DEFINITIONS}


def _trim(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _trim(v) for k, v in value.items() if k not in DROP}
    if isinstance(value, list):
        return [_trim(v) for v in value]
    return value


class ApiTools:
    """Maps tool calls to API requests. `http` is any httpx-style client pointed at the API."""

    def __init__(self, http: Any, token: str | None = None) -> None:
        self.http = http
        self.headers = {"Authorization": f"Bearer {token}"} if token else {}
        self.seen: list[Any] = []  # every result returned to the agent, for the fallback reply

    def __call__(self, name: str, args: dict[str, Any]) -> str:
        if name == "find_place":
            response = self.http.get("/places", params={"q": args["text"]}, headers=self.headers)
        elif name == "locate":
            response = self.http.get("/point", params={"lat": args["lat"], "lon": args["lon"]}, headers=self.headers)
        elif name == "get_fact":
            response = self.http.get(f"/facts/{args['fact_id']}", headers=self.headers)
        elif name == "ward_summary":
            response = self.http.get("/views/ward_summary", params={"id": args["ward"]}, headers=self.headers)
        elif name in {"trace_money", "work_status", "gaps_for"}:
            node = args.get("node_id") or args.get("work_id")
            response = self.http.get(f"/views/{name}", params={"id": node}, headers=self.headers)
        elif name == "who_is_responsible":
            params = {"id": args["asset_id"], **({"issue": args["issue"]} if args.get("issue") else {})}
            response = self.http.get("/views/who_is_responsible", params=params, headers=self.headers)
        else:
            return json.dumps({"error": f"unknown tool {name}"})
        if response.status_code != 200:
            return json.dumps({"error": f"not found ({response.status_code})"})
        result = _trim(response.json())
        self.seen.append(result)
        return json.dumps(result, ensure_ascii=False)
