"""Named views over the graph (SPEC-006/R5, R7).

Each view returns its hops in order, every item with its provenance, and lists each missing hop as a gap
naming the record that would fill it and who holds it. Applications and agents call these instead of
writing their own queries.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import date
from typing import Any

ASSET_LABELS = {"Asset", "Road", "Drain", "Bridge", "Building", "Toilet", "Garden", "School", "Hospital"}


@dataclass(frozen=True)
class Gap:
    hop: str
    record_needed: str
    holder: str


@dataclass
class ViewResult:
    rows: list[dict[str, Any]] = field(default_factory=list)
    gaps: list[Gap] = field(default_factory=list)
    query_ms: int = 0


GAPS = {
    "budget_head": Gap(
        "budget_head", "Budget head and allocation this work is charged to", "BMC Chief Accountant (Finance)"
    ),
    "tender": Gap("tender", "Tender notice for this work", "The executing department; Mahatenders"),
    "award": Gap("award", "Award of contract or Standing Committee resolution", "Municipal Secretary, BMC"),
    "contract": Gap("contract", "Contract or work order", "The executing department"),
    "contractor": Gap("contractor", "Name of the contractor awarded the work", "Municipal Secretary, BMC"),
    "defect_liability": Gap("defect_liability", "Defect liability clause of the contract", "The executing department"),
    "payment": Gap("payment", "Bills paid against the contract", "BMC Chief Accountant (Finance)"),
    "owner": Gap("owner", "Which agency owns this asset", "BMC ward office; the agencies that may own it"),
    "ward": Gap("ward", "Which administrative ward the asset is in", "BMC ward office"),
    "department": Gap("department", "Which department handles this kind of issue", "BMC citizen charter"),
    "post": Gap("post", "The post responsible in this ward", "BMC proactive disclosure under RTI Act section 4"),
}


def node_dict(node: Any) -> dict[str, Any]:
    """A graph node as a plain dict: id, label, current properties, and per-property provenance."""
    props = dict(node)
    provenance = {k[len("_prov_") :]: json.loads(v) for k, v in props.items() if k.startswith("_prov_")}
    plain = {k: v for k, v in props.items() if not k.startswith("_prov_")}
    labels = sorted(set(node.labels) - {"Node"})
    return {"label": labels[0] if labels else "Node", **plain, "provenance": provenance}


class Views:
    def __init__(self, driver: Any, database: str | None = None, today: date | None = None) -> None:
        self.driver = driver
        self.database = database
        self.today = today

    def _today(self) -> str:
        return (self.today or date.today()).isoformat()

    def _q(self, query: str, **params: Any) -> list[dict[str, Any]]:
        with self.driver.session(database=self.database) as session:
            return [r.data() if not _has_nodes(r) else _record(r) for r in session.run(query, **params)]

    # ---- trace_money -----------------------------------------------------------------------------------

    def trace_money(self, node_id: str) -> ViewResult:
        """Budget head to payment for every work on an asset, a work, or a tender's work."""
        started = time.monotonic()
        result = ViewResult()
        for work_id in self._works_for(node_id):
            work = self._q("MATCH (w:Work {id: $id}) RETURN w", id=work_id)[0]["w"]
            hops: list[dict[str, Any]] = []
            budget = self._q(
                "MATCH (w:Work {id: $id})-[:FUNDED_BY]->(al:Allocation) "
                "OPTIONAL MATCH (al)-[:UNDER]->(bh:BudgetHead) RETURN al, bh",
                id=work_id,
            )
            for row in budget:
                if row.get("bh"):
                    hops.append({"hop": "budget_head", "node": row["bh"]})
                hops.append({"hop": "allocation", "node": row["al"]})
            if not budget:
                result.gaps.append(_gap("budget_head", work_id))
            hops.append({"hop": "work", "node": work})
            tenders = self._q("MATCH (t:Tender)-[:FOR_WORK]->(:Work {id: $id}) RETURN t ORDER BY t.id", id=work_id)
            hops += [{"hop": "tender", "node": r["t"]} for r in tenders]
            if not tenders:
                result.gaps.append(_gap("tender", work_id))
            awards = self._q(
                "MATCH (a:Award)-[:OF]->(:Tender)-[:FOR_WORK]->(:Work {id: $id}) RETURN DISTINCT a ORDER BY a.id",
                id=work_id,
            )
            hops += [{"hop": "award", "node": r["a"]} for r in awards]
            if tenders and not awards:
                result.gaps.append(_gap("award", work_id))
            contracts = self._q(
                "MATCH (c:Contract)-[:FOR_WORK]->(:Work {id: $id}) RETURN c "
                "UNION MATCH (c:Contract)-[:FROM_AWARD]->(:Award)-[:OF]->(:Tender)-[:FOR_WORK]->(:Work {id: $id}) "
                "RETURN c",
                id=work_id,
            )
            hops += [{"hop": "contract", "node": r["c"]} for r in _unique(contracts, "c")]
            if awards and not contracts:
                result.gaps.append(_gap("contract", work_id))
            contractors = self._q(
                "MATCH (a:Award)-[:OF]->(:Tender)-[:FOR_WORK]->(:Work {id: $id}) MATCH (a)-[:TO]->(k:Contractor) "
                "RETURN k UNION "
                "MATCH (k:Contractor)-[:PARTY_TO]->(:Contract)-[:FOR_WORK]->(:Work {id: $id}) RETURN k",
                id=work_id,
            )
            hops += [{"hop": "contractor", "node": r["k"]} for r in _unique(contractors, "k")]
            if (awards or contracts) and not contractors:
                result.gaps.append(_gap("contractor", work_id))
            dlp = self._q("MATCH (:Work {id: $id})-[:HAS_DLP]->(d:DefectLiabilityPeriod) RETURN d", id=work_id)
            hops += [{"hop": "defect_liability", "node": r["d"]} for r in dlp]
            if contracts and not dlp:
                result.gaps.append(_gap("defect_liability", work_id))
            payments = self._q(
                "MATCH (p:Payment)-[:UNDER_CONTRACT]->(:Contract)-[:FOR_WORK]->(:Work {id: $id}) "
                "RETURN DISTINCT p ORDER BY p.id",
                id=work_id,
            )
            hops += [{"hop": "payment", "node": r["p"]} for r in payments]
            if contracts and not payments:
                result.gaps.append(_gap("payment", work_id))
            result.rows.append({"work_id": work_id, "hops": hops})
        result.query_ms = int((time.monotonic() - started) * 1000)
        return result

    def _works_for(self, node_id: str) -> list[str]:
        rows = self._q(
            "MATCH (n:Node {id: $id}) "
            "OPTIONAL MATCH (w1:Work)-[:IMPROVES]->(n) "
            "OPTIONAL MATCH (n)-[:FOR_WORK]->(w2:Work) "
            "RETURN labels(n) AS labels, collect(DISTINCT w1.id) AS improving, collect(DISTINCT w2.id) AS works",
            id=node_id,
        )
        if not rows:
            return []
        row = rows[0]
        if "Work" in row["labels"]:
            return [node_id]
        return sorted(set(row["improving"]) | set(row["works"]))

    # ---- who_is_responsible ------------------------------------------------------------------------------

    def who_is_responsible(self, asset_id: str, issue: str | None = None) -> ViewResult:
        started = time.monotonic()
        result = ViewResult()
        found = self._q("MATCH (a:Node {id: $id}) RETURN a", id=asset_id)
        if not found:
            return result
        hops: list[dict[str, Any]] = [{"hop": "asset", "node": found[0]["a"]}]
        wards = self._q("MATCH (:Node {id: $id})-[:LOCATED_IN]->(w:AdminWard) RETURN w", id=asset_id)
        hops += [{"hop": "ward", "node": r["w"]} for r in wards]
        if not wards:
            result.gaps.append(_gap("ward", asset_id))
        owners = self._q("MATCH (g:Agency)-[:OWNS]->(:Node {id: $id}) RETURN g", id=asset_id)
        hops += [{"hop": "owner", "node": r["g"]} for r in owners]
        if not owners:
            result.gaps.append(_gap("owner", asset_id))
        departments = (
            self._q(
                "MATCH (it:IssueType {code: $issue})-[:HANDLED_BY]->(d:Department) "
                "OPTIONAL MATCH (d)-[:PART_OF]->(g:Agency) RETURN d, g",
                issue=issue,
            )
            if issue
            else []
        )
        owner_ids = {r["g"]["id"] for r in owners}
        departments = [r for r in departments if not owner_ids or (r.get("g") and r["g"]["id"] in owner_ids)]
        hops += [{"hop": "department", "node": r["d"]} for r in departments]
        if issue and not departments:
            result.gaps.append(_gap("department", asset_id))
        posts = []
        for d in departments:
            for w in wards:
                posts += self._q(
                    "MATCH (p:Post)-[:IN]->(:Department {id: $d}) MATCH (p)-[:COVERS]->(:AdminWard {id: $w}) RETURN p",
                    d=d["d"]["id"],
                    w=w["w"]["id"],
                )
        hops += [{"hop": "post", "node": r["p"]} for r in posts]
        if departments and not posts:
            result.gaps.append(_gap("post", asset_id))
        for post in posts:
            chain = self._q(
                "MATCH path = (:Post {id: $id})-[:REPORTS_TO*1..4]->(up:Post) RETURN up, length(path) AS steps "
                "ORDER BY steps",
                id=post["p"]["id"],
            )
            hops += [{"hop": "escalation", "node": r["up"], "steps": r["steps"]} for r in chain]
        liable = self._q(
            "MATCH (w:Work)-[:IMPROVES]->(:Node {id: $id}) MATCH (w)-[:HAS_DLP]->(d:DefectLiabilityPeriod) "
            "WHERE d.from_date <= $today AND d.to_date >= $today "
            "OPTIONAL MATCH (k:Contractor)-[:PARTY_TO]->(:Contract)-[:FOR_WORK]->(w) RETURN w, d, k",
            id=asset_id,
            today=self._today(),
        )
        hops += [{"hop": "under_liability", "work": r["w"], "period": r["d"], "contractor": r.get("k")} for r in liable]
        result.rows = hops
        result.query_ms = int((time.monotonic() - started) * 1000)
        return result

    # ---- work_status ---------------------------------------------------------------------------------------

    def work_status(self, work_id: str) -> ViewResult:
        started = time.monotonic()
        result = ViewResult()
        found = self._q("MATCH (w:Work {id: $id}) RETURN w", id=work_id)
        if not found:
            return result
        work = found[0]["w"]
        facts = self._q(
            "MATCH (:Work {id: $id})-[:HAS_FACT]->(f:Fact) "
            "OPTIONAL MATCH (f)-[:SUPERSEDES]->(old:Fact) "
            "RETURN f.fact_id AS fact_id, f.props AS props, f.change AS change, f.source AS source, f.page AS page, "
            "f.loaded_at AS loaded_at, collect(old.fact_id) AS supersedes ORDER BY loaded_at, fact_id",
            id=work_id,
        )
        history = []
        for f in facts:
            props = json.loads(f["props"])
            if "due_on" in props:
                history.append(
                    {
                        "due_on": props["due_on"],
                        "fact_id": f["fact_id"],
                        "source": f["source"],
                        "page": f["page"],
                        "loaded_at": f["loaded_at"],
                        "change": f["change"],
                        "supersedes": f["supersedes"],
                    }
                )
        due, done = work.get("due_on"), work.get("completed_on")
        result.rows = [
            {"hop": "work", "node": work},
            {"hop": "due_on_history", "items": history},
            {
                "hop": "state",
                "overdue": bool(due and not done and due < self._today()),
                "due_on": due,
                "completed_on": done,
            },
        ]
        result.query_ms = int((time.monotonic() - started) * 1000)
        return result

    # ---- ward_summary --------------------------------------------------------------------------------------

    def ward_summary(self, ward: str) -> ViewResult:
        """Assets, works and tenders in a ward (by code such as K/W, or node id)."""
        started = time.monotonic()
        result = ViewResult()
        wards = self._q("MATCH (w:AdminWard) WHERE w.code = $ward OR w.id = $ward RETURN w", ward=ward)
        if not wards:
            return result
        ward_id = wards[0]["w"]["id"]
        assets = self._q(
            "MATCH (a:Node)-[:LOCATED_IN]->(:AdminWard {id: $id}) RETURN labels(a) AS labels, count(a) AS n", id=ward_id
        )
        works = self._q(
            "MATCH (w:Work)-[:IMPROVES]->(:Node)-[:LOCATED_IN]->(:AdminWard {id: $id}) "
            "OPTIONAL MATCH (t:Tender)-[:FOR_WORK]->(w) "
            "RETURN w, collect(DISTINCT t) AS tenders",
            id=ward_id,
        )
        today = self._today()
        summary_works = []
        for row in works:
            w = row["w"]
            summary_works.append(
                {
                    "work": w,
                    "tenders": row["tenders"],
                    "estimated_cost": sum(int(t.get("estimated_cost") or 0) for t in row["tenders"]),
                    "overdue": bool(w.get("due_on") and not w.get("completed_on") and w["due_on"] < today),
                }
            )
        counts: dict[str, int] = {}
        for row in assets:
            label = sorted(set(row["labels"]) - {"Node"})[0]
            counts[label] = counts.get(label, 0) + int(row["n"])
        result.rows = [
            {"hop": "ward", "node": wards[0]["w"]},
            {"hop": "assets", "counts": counts},
            {
                "hop": "works",
                "items": summary_works,
                "tendered_value": sum(w["estimated_cost"] for w in summary_works),
                "overdue": sum(1 for w in summary_works if w["overdue"]),
            },
        ]
        result.query_ms = int((time.monotonic() - started) * 1000)
        return result

    # ---- gaps_for ------------------------------------------------------------------------------------------

    def gaps_for(self, node_id: str) -> ViewResult:
        started = time.monotonic()
        labels = self._q("MATCH (n:Node {id: $id}) RETURN labels(n) AS labels", id=node_id)
        result = ViewResult()
        if labels:
            result.gaps = list(self.trace_money(node_id).gaps)
            if set(labels[0]["labels"]) & ASSET_LABELS:
                result.gaps += self.who_is_responsible(node_id).gaps
        result.query_ms = int((time.monotonic() - started) * 1000)
        return result


def _gap(kind: str, node_id: str) -> Gap:
    base = GAPS[kind]
    return Gap(f"{base.hop} ({node_id})", base.record_needed, base.holder)


def _has_nodes(record: Any) -> bool:
    return any(hasattr(v, "labels") or (isinstance(v, list) and v and hasattr(v[0], "labels")) for v in record.values())


def _record(record: Any) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in record.items():
        if hasattr(value, "labels"):
            out[key] = node_dict(value)
        elif isinstance(value, list) and value and hasattr(value[0], "labels"):
            out[key] = [node_dict(v) for v in value]
        else:
            out[key] = value
    return out


def _unique(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    seen, out = set(), []
    for row in rows:
        if row[key]["id"] not in seen:
            seen.add(row[key]["id"])
            out.append(row)
    return sorted(out, key=lambda r: r[key]["id"])
