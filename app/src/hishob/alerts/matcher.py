"""Find events in saved areas and queue one alert per subscriber per event (SPEC-010/R2, R3, R5, R6).

Reads the ledger index and the geo tables, both in Postgres, so it needs no graph query. Run it after every graph
apply, and the overdue check once a day. Both are safe to run any number of times: an alert's `event_key` is
unique, so a replay queues nothing new.

An event counts for a subscription only if its first fact was loaded after the area was saved: a new subscriber
is not sent the history of their street. The overdue check is the exception, because a work that is overdue
today is news to anyone.
"""

from __future__ import annotations

import json
from datetime import date
from typing import Any

from hishob.ledger import Loader

LOW_CONFIDENCE = 0.7  # below this, the link from work to road was a weak match and the alert says so (R6)

# event kind -> (label of the node that is the event, edge path from it to the tender; empty for the tender itself)
EVENTS = {"tender_published": ("Tender", None), "awarded": ("Award", "OF"), "corrigendum": ("Corrigendum", "AMENDS")}

_EDGES = (
    "SELECT f.name, f.from_id, f.to_id, f.fact_id FROM ledger.current c JOIN ledger.facts f USING (fact_id)"
    " WHERE f.kind = 'edge'"
)
# Subscriptions whose area holds the asset: within the radius of any segment of the road, or the road was named.
_AREA = (
    "SELECT s.id FROM account.subscriptions s WHERE"
    " (s.kind = 'point' AND EXISTS (SELECT 1 FROM geo.road_segments r"
    "    WHERE r.name = (SELECT name FROM geo.road_segments WHERE node_id = %(asset)s)"
    "      AND ST_DWithin(r.geom::geography, s.geom::geography, s.radius_m)))"
    " OR (s.kind = 'roads' AND EXISTS (SELECT 1 FROM geo.road_segments r"
    "    WHERE r.node_id = ANY(s.road_ids)"
    "      AND r.name = (SELECT name FROM geo.road_segments WHERE node_id = %(asset)s)))"
)


def evaluate(conn: Any, loader: Loader) -> int:
    """Queue alerts for tenders, awards and corrigenda linked to assets in saved areas. Returns how many were new."""
    queued = 0
    for kind, (label, to_tender) in EVENTS.items():
        tender = "e.node_id" if to_tender is None else "hop.to_id"
        join = "" if to_tender is None else f"JOIN edges hop ON hop.name = '{to_tender}' AND hop.from_id = e.node_id"
        rows = conn.execute(
            f"WITH edges AS ({_EDGES}),"
            " e AS (SELECT c.node_id, c.fact_id, (SELECT min(loaded_at) FROM ledger.facts f"
            "        WHERE f.node_id = c.node_id AND f.kind = 'node') AS first_seen"
            "      FROM ledger.current c WHERE c.label = %s)"
            f" SELECT e.node_id, e.fact_id, e.first_seen, {tender} AS tender_id, fw.to_id AS work_id,"
            "        im.to_id AS asset_id, im.fact_id AS link_fact"
            f" FROM e {join}"
            f" JOIN edges fw ON fw.name = 'FOR_WORK' AND fw.from_id = {tender}"
            " JOIN edges im ON im.name = 'IMPROVES' AND im.from_id = fw.to_id"
            " ORDER BY e.node_id, im.to_id",
            (label,),
        ).fetchall()
        for node_id, fact_id, first_seen, tender_id, work_id, asset_id, link_fact in rows:
            subscribers = conn.execute(
                f"SELECT id FROM ({_AREA}) AS area JOIN account.subscriptions s USING (id)"
                " WHERE s.created_at <= %(seen)s",
                {"asset": asset_id, "seen": first_seen},
            ).fetchall()
            if not subscribers:
                continue
            payload = _payload(conn, loader, kind, label, node_id, fact_id, tender_id, work_id, asset_id, link_fact)
            payload.setdefault("date", first_seen.date().isoformat())
            # One alert per subscriber per event: the event is the node, so a later fact about it does not repeat.
            queued += _queue(conn, [s[0] for s in subscribers], f"{node_id}:{kind}", payload)
    conn.commit()
    return queued


def evaluate_overdue(conn: Any, loader: Loader, today: date | None = None) -> int:
    """Queue one overdue alert per work whose current due date has passed with no completion fact (R3)."""
    today = today or date.today()
    queued = 0
    rows = conn.execute(
        f"WITH edges AS ({_EDGES})"
        " SELECT c.node_id, c.fact_id, im.to_id, im.fact_id,"
        "   (SELECT fw.from_id FROM edges fw JOIN ledger.current t ON t.node_id = fw.from_id AND t.label = 'Tender'"
        "     WHERE fw.name = 'FOR_WORK' AND fw.to_id = c.node_id ORDER BY fw.from_id LIMIT 1)"
        " FROM ledger.current c JOIN edges im ON im.name = 'IMPROVES' AND im.from_id = c.node_id"
        " WHERE c.label = 'Work' ORDER BY c.node_id, im.to_id"
    ).fetchall()
    for work_id, fact_id, asset_id, link_fact, tender_id in rows:
        props = loader.current_properties(f"node|Work|{work_id}")
        due = props.get("due_on")
        if not due or props.get("completed_on") or str(due) >= today.isoformat():
            continue
        subscribers = conn.execute(_AREA, {"asset": asset_id}).fetchall()
        if not subscribers:
            continue
        payload = _payload(conn, loader, "overdue", "Work", work_id, fact_id, tender_id, work_id, asset_id, link_fact)
        payload["date"] = str(due)
        # The due date is part of the key: if the date is extended and passes again, that is a new event.
        queued += _queue(conn, [s[0] for s in subscribers], f"{work_id}:overdue:{due}", payload)
    conn.commit()
    return queued


def _payload(
    conn: Any,
    loader: Loader,
    kind: str,
    label: str,
    node_id: str,
    fact_id: str,
    tender_id: str | None,
    work_id: str,
    asset_id: str,
    link_fact: str,
) -> dict[str, Any]:
    entry = loader.fact(fact_id) or {}
    own = loader.current_properties(f"node|{label}|{node_id}")
    tender = loader.current_properties(f"node|Tender|{tender_id}") if tender_id else {}
    work = loader.current_properties(f"node|Work|{work_id}")
    road = conn.execute("SELECT name, name_mr FROM geo.road_segments WHERE node_id = %s", (asset_id,)).fetchone()
    link = loader.fact(link_fact) or {}
    payload: dict[str, Any] = {
        "kind": kind,
        "node_id": node_id,
        "fact_id": fact_id,
        "tender_ref": tender.get("ref_no") or own.get("ref_no"),
        "work_title": work.get("title") or tender.get("title"),
        "asset_id": asset_id,
        "road_name": road[0] if road else None,
        "road_name_mr": road[1] if road else None,
        "source": entry.get("source"),
        "page": entry.get("page"),
        "low_confidence": float(link.get("confidence", 1.0)) < LOW_CONFIDENCE,
    }
    when = own.get("published_on") or own.get("awarded_on")
    if when:
        payload["date"] = str(when)
    if own.get("changed_field"):
        payload["changed_field"] = own["changed_field"]
    return payload


def _queue(conn: Any, subscription_ids: list[int], event: str, payload: dict[str, Any]) -> int:
    new = 0
    for subscription_id in subscription_ids:
        new += conn.execute(
            "INSERT INTO alerts.outbox (subscription_id, event_key, payload) VALUES (%s, %s, %s)"
            " ON CONFLICT (event_key) DO NOTHING",
            (subscription_id, f"{subscription_id}:{event}", json.dumps(payload, ensure_ascii=False)),
        ).rowcount
    return new
