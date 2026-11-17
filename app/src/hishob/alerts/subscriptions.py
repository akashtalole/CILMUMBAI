"""Saved areas (SPEC-010/R1). A subscription holds an account id and an area; no contact details (C7)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from hishob.alerts.render import render

MIN_RADIUS_M, MAX_RADIUS_M, MAX_ROADS, MAX_PER_ACCOUNT = 100, 1000, 20, 10
LANGUAGES = ("mr", "hi", "en")


@dataclass(frozen=True)
class Subscription:
    id: int
    account_id: str
    kind: str
    lat: float | None
    lon: float | None
    radius_m: int | None
    road_ids: list[str]
    language: str
    created_at: datetime


def _check(conn: Any, account_id: str, language: str) -> None:
    if language not in LANGUAGES:
        raise ValueError("language must be mr, hi or en")
    count = conn.execute("SELECT count(*) FROM account.subscriptions WHERE account_id = %s", (account_id,)).fetchone()
    if count[0] >= MAX_PER_ACCOUNT:
        raise ValueError(f"at most {MAX_PER_ACCOUNT} saved areas per account")


def save_point(
    conn: Any, account_id: str, lat: float, lon: float, radius_m: int, language: str, *, now: datetime | None = None
) -> Subscription:
    if not MIN_RADIUS_M <= radius_m <= MAX_RADIUS_M:
        raise ValueError(f"radius must be between {MIN_RADIUS_M} and {MAX_RADIUS_M} metres")
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError("not a valid point")
    _check(conn, account_id, language)
    row = conn.execute(
        "INSERT INTO account.subscriptions (account_id, kind, geom, radius_m, language, created_at)"
        " VALUES (%s, 'point', ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s, %s, COALESCE(%s, now())) RETURNING id",
        (account_id, lon, lat, radius_m, language, now),
    ).fetchone()
    conn.commit()
    return _get(conn, int(row[0]))


def save_roads(
    conn: Any, account_id: str, road_ids: list[str], language: str, *, now: datetime | None = None
) -> Subscription:
    wanted = sorted(set(road_ids))
    if not 1 <= len(wanted) <= MAX_ROADS:
        raise ValueError(f"name between 1 and {MAX_ROADS} roads")
    known = {
        r[0]
        for r in conn.execute("SELECT node_id FROM geo.road_segments WHERE node_id = ANY(%s)", (wanted,)).fetchall()
    }
    unknown = [r for r in wanted if r not in known]
    if unknown:
        conn.commit()
        raise ValueError("not a road we know: " + ", ".join(unknown))
    _check(conn, account_id, language)
    row = conn.execute(
        "INSERT INTO account.subscriptions (account_id, kind, road_ids, language, created_at)"
        " VALUES (%s, 'roads', %s, %s, COALESCE(%s, now())) RETURNING id",
        (account_id, wanted, language, now),
    ).fetchone()
    conn.commit()
    return _get(conn, int(row[0]))


_COLUMNS = "id, account_id, kind, ST_Y(geom), ST_X(geom), radius_m, road_ids, language, created_at"


def _get(conn: Any, subscription_id: int) -> Subscription:
    row = conn.execute(f"SELECT {_COLUMNS} FROM account.subscriptions WHERE id = %s", (subscription_id,)).fetchone()
    conn.commit()
    return Subscription(*row)


def list_subscriptions(conn: Any, account_id: str) -> list[Subscription]:
    rows = conn.execute(
        f"SELECT {_COLUMNS} FROM account.subscriptions WHERE account_id = %s ORDER BY id", (account_id,)
    ).fetchall()
    conn.commit()
    return [Subscription(*row) for row in rows]


def unsubscribe(conn: Any, account_id: str, subscription_id: int) -> bool:
    """Delete a saved area and its alerts. Only its owner can."""
    done = conn.execute(
        "DELETE FROM account.subscriptions WHERE id = %s AND account_id = %s", (subscription_id, account_id)
    ).rowcount
    conn.commit()
    return bool(done)


def list_alerts(conn: Any, account_id: str, base_url: str = "", limit: int = 50) -> list[dict[str, Any]]:
    """A subscriber's alerts, newest first, rendered in each subscription's language (R4)."""
    rows = conn.execute(
        "SELECT o.id, o.subscription_id, o.payload, o.created_at, s.language FROM alerts.outbox o"
        " JOIN account.subscriptions s ON s.id = o.subscription_id WHERE s.account_id = %s"
        " ORDER BY o.created_at DESC, o.id DESC LIMIT %s",
        (account_id, limit),
    ).fetchall()
    conn.commit()
    return [
        {
            "id": alert_id,
            "subscription_id": subscription_id,
            "created_at": created_at.isoformat(),
            "kind": payload["kind"],
            "text": render(payload, language, base_url),
            "payload": payload,
        }
        for alert_id, subscription_id, payload, created_at, language in rows
    ]
