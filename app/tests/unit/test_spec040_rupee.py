"""SPEC-040 Follow the Rupee: the auditor, the linker, the scorecards, the planner, the checked notes, the complaint
trail and the endpoints, on the challenge dataset bundled in datasets/follow-the-rupee."""

from __future__ import annotations

import csv
import dataclasses
from collections import Counter
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from hishob.api.app import ApiConfig, create_app
from hishob.archive.storage import LocalStore
from hishob.rupee import audit, build, link, narrate, score
from hishob.rupee.data import DEFAULT_DIR, Row, load
from hishob.rupee.trail import Trail


@pytest.fixture(scope="module")
def data():  # type: ignore[no-untyped-def]
    return load()


@pytest.fixture(scope="module")
def bundle(data):  # type: ignore[no-untyped-def]
    return build.compute(data, client=None)


def _rows(name: str) -> list[dict[str, str]]:
    with (DEFAULT_DIR / name).open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


# AC1 · R2: the auditor finds the hidden problems, each with a reason, an amount and its rows ---------------------


def test_spec040_ac1_the_auditor_finds_the_three_kinds_of_hidden_problem(data) -> None:  # type: ignore[no-untyped-def]
    flags = audit.run(data)
    counts = Counter(f.rule for f in flags)
    assert counts["overbilled"] == 109 and counts["duplicate"] == 45 and counts["dlp_paid"] == 493
    for f in flags:
        assert f.reason and f.amount_inr > 0
        assert f.evidence[0].startswith("work_orders.csv#L")


def test_spec040_ac1_every_flag_can_be_checked_by_hand_from_the_csv(data) -> None:  # type: ignore[no-untyped-def]
    wos = {r["work_order_id"]: r for r in _rows("work_orders.csv")}
    rate = {r["repair_method"]: r for r in _rows("rate_card.csv")}
    roads = {r["road_id"]: r for r in _rows("roads.csv")}
    lines = {i: r for i, r in enumerate(_rows("work_orders.csv"), start=2)}
    for f in audit.run(data):
        wo = wos[f.work_order_id]
        assert lines[int(f.evidence[0].split("#L")[1])]["work_order_id"] == f.work_order_id  # the cite points at it
        if f.rule == "overbilled":
            r = rate[wo["repair_method"]]
            exp = float(r["standard_rate_inr"]) * (float(wo["area_sqm"]) if r["unit"] == "per sqm" else 1)
            assert float(wo["cost_inr"]) / exp > 1.5
        if f.rule == "duplicate":
            other = wos[f.detail["original"]]
            assert not wo["linked_complaint_ids"] and other["road_id"] == wo["road_id"]
            assert other["work_type"] == wo["work_type"]
        if f.rule == "dlp_paid":
            assert roads[wo["road_id"]]["under_dlp"] == "Y" and float(wo["cost_inr"]) > 0


def test_spec040_ac1_normal_variation_is_not_flagged(data) -> None:  # type: ignore[no-untyped-def]
    over = {f.work_order_id for f in audit.overbilled(data)}
    rate = {r["repair_method"]: r for r in data.rate_card}
    for wo in data.work_orders:
        e = audit.expected_cost(wo, rate[wo["repair_method"]])
        if e and wo.num("cost_inr") / e <= 1.3:  # the 20-30% band in the data dictionary
            assert wo["work_order_id"] not in over


def test_spec040_ac1_money_in_question_counts_each_job_once(data) -> None:  # type: ignore[no-untyped-def]
    flags = audit.run(data)
    by_wo: dict[str, int] = {}
    for f in flags:
        if f.rule in audit.CORE:
            by_wo[f.work_order_id] = max(by_wo.get(f.work_order_id, 0), f.amount_inr)
    assert audit.at_risk(flags) == sum(by_wo.values()) < sum(f.amount_inr for f in flags if f.rule in audit.CORE)


def test_spec040_ac1_rupees_are_written_the_indian_way() -> None:
    assert audit.inr(13432818) == "₹1,34,32,818" and audit.inr(999) == "₹999" and audit.inr(-150000) == "-₹1,50,000"


# AC2 · R1: complaints become issues tied to work orders, across four languages ----------------------------------


def test_spec040_ac2_each_complaint_is_linked_or_its_state_said(data) -> None:  # type: ignore[no-untyped-def]
    rows = link.run(data)
    assert len(rows) == len(data.complaints)
    given = {c for wo in data.work_orders for c in wo["linked_complaint_ids"].split("|") if c}
    assert {r.complaint_id for r in rows if r.work_order_id} == given
    assert all(r.state for r in rows) and all(r.cite.startswith("complaints.csv#L") for r in rows)
    s = link.summary(rows)
    assert s["issues"] < s["complaints"] and s["open_issues"] > 0
    assert s["ward_unknown"] <= 5  # the ~7% with no ward are placed from the gazetteer or GPS


def test_spec040_ac2_open_reports_of_one_problem_are_one_issue(data) -> None:  # type: ignore[no-untyped-def]
    rows = [r for r in link.run(data) if r.state.startswith("open") and r.road_id]
    seen: dict[tuple[str, str, str], str] = {}
    for r in rows:
        key = (r.ward_code, r.road_id, r.category)
        assert seen.setdefault(key, r.issue_id) == r.issue_id


@pytest.mark.parametrize(
    ("text", "category"),
    [
        ("Poisar मध्ये पाणी साचले आहे, गाड्या अडकल्या आहेत", "Waterlogging"),
        ("kitni baar complaint karein? wahi gadda phir se khul gaya", "Pothole"),
        ("post office ke paas gutter ka dhakkan khula hai", "Open or broken manhole"),
        ("Ganpatrao Kadam Marg — road dhas gaya hai", "Road cave-in"),
        ("My bike tyre burst because of pothole at petrol pump", "Pothole"),
        ("Thank you BMC for the quick work", None),
    ],
)
def test_spec040_ac2_categories_are_read_in_four_languages(text: str, category: str | None) -> None:
    assert link.infer_category(text) == category


# AC3 · R3: fair scorecards -------------------------------------------------------------------------------------


def test_spec040_ac3_fifty_means_as_expected_and_the_scale_is_bounded() -> None:
    assert score.fair(0.25, 0.25) == 50 and score.fair(0.0, 0.25) == 100 and score.fair(0.5, 0.25) == 0
    assert score.fair(0.9, 0.25) == 0 and 50 < score.fair(0.2, 0.25) < 100


def test_spec040_ac3_doing_more_of_the_same_work_is_not_punished(data, bundle) -> None:  # type: ignore[no-untyped-def]
    flags, linked = audit.run(data), link.run(data)
    s = score.Scorer(data, flags, linked)
    c = data.contractors[0]
    jobs = [j for j in data.work_orders if j["contractor_id"] == c["contractor_id"]]
    mine = [f for f in flags if f.contractor_id == c["contractor_id"]]
    once = s._common(jobs, mine, score.CONTRACTOR_RULES)["scores"]
    copies = []
    for j in jobs:  # the same jobs again, as new work orders
        r = Row({**j, "work_order_id": j["work_order_id"] + "-B"})
        r.file, r.line = j.file, j.line
        copies.append(r)
    more = [dataclasses.replace(f, work_order_id=f.work_order_id + "-B") for f in mine]
    twice = s._common(jobs + copies, mine + more, score.CONTRACTOR_RULES)["scores"]
    assert once == twice


def test_spec040_ac3_scorecards_cover_everyone_and_explain_themselves(bundle) -> None:  # type: ignore[no-untyped-def]
    assert len(bundle["contractors"]) == 8 and len(bundle["wards"]) == 24
    for c in bundle["contractors"]:
        assert set(c["scores"]) == {"durability", "speed", "billing"} and c["grade"] in "ABCDE"
        assert c["billing_basis"] == ["overbilled", "duplicate"]  # DLP payments count against the ward
        assert c["note"]["text"]
    for w in bundle["wards"]:
        assert set(w["scores"]) == {"durability", "speed", "billing", "backlog"} and w["budget_inr"] > 0
    worst = bundle["contractors"][-1]
    assert worst["flags"]["overbilled"]["count"] >= 30  # the contractor that over-bills most ranks last


# AC4 · R4: the next-rupee plan --------------------------------------------------------------------------------


def test_spec040_ac4_the_plan_ranks_by_risk_and_stays_in_budget(bundle) -> None:  # type: ignore[no-untyped-def]
    p = bundle["plan"]
    assert abs(sum(p["weights"].values()) - 1) < 1e-9
    for ward in p["wards"].values():
        risks = [i["risk"] for i in ward["items"]]
        assert risks == sorted(risks, reverse=True)
        assert ward["funded_cost_inr"] <= max(0, ward["remaining_inr"])
        for i in ward["items"]:
            assert i["why"] and i["evidence"]
            if i["under_dlp"]:
                assert i["cost_inr"] == 0 and i["funded"] and i["method"].startswith("Call the original contractor")


def test_spec040_ac4_the_method_is_the_one_that_lasts(bundle) -> None:  # type: ignore[no-untyped-def]
    methods = bundle["plan"]["methods"]
    for i in bundle["plan"]["city_top"]:
        options = methods[i["category"]]
        assert i["method_reopen_rate"] == min(m["reopen_rate"] for m in options)
    assert methods["Pothole"][0]["method"] != "Cold mix patch"  # the cheapest patch fails most


# AC5 · R5: Claude's notes are checked in code -----------------------------------------------------------------


class FakeClient:
    def __init__(self, text: str, stop: str = "end_turn") -> None:
        self.messages = SimpleNamespace(
            create=lambda **_: SimpleNamespace(content=[SimpleNamespace(text=text)], stop_reason=stop)
        )


def test_spec040_ac5_a_note_with_an_invented_number_or_an_accusation_is_replaced(bundle) -> None:  # type: ignore[no-untyped-def]
    facts = narrate.contractor_facts(bundle["contractors"][0])
    good = f"{facts['name']} met the SLA on {facts['sla_met_pct']}% of {facts['jobs']} jobs."
    assert narrate.write(FakeClient(good), "contractor", facts)["by"] == narrate.MODEL
    for bad in (good + " This looks like a scam.", good + " It billed 777 jobs.", good):
        stop = "max_tokens" if bad == good else "end_turn"
        got = narrate.write(FakeClient(bad, stop), "contractor", facts)
        assert got["by"] == "template" and got["problems"] and got["rejected"] == bad
    assert narrate.write(None, "contractor", facts)["by"] == "template"


def test_spec040_ac5_the_templates_pass_their_own_checks(bundle) -> None:  # type: ignore[no-untyped-def]
    for c in bundle["contractors"]:
        f = narrate.contractor_facts(c)
        assert narrate.check(narrate.template_contractor(f), f, 120) == []
    for w in bundle["wards"]:
        f = narrate.ward_facts(w, bundle["plan"]["wards"][w["ward_code"]])
        assert not [p for p in narrate.check(narrate.template_ward(f), f, 170) if not p.startswith("too long")]


# AC6 · R7: what happened to my complaint -----------------------------------------------------------------------


def test_spec040_ac6_a_fixed_complaint_names_the_work_the_cost_and_whether_it_held(bundle) -> None:  # type: ignore[no-untyped-def]
    wos = {r["work_order_id"]: r for r in _rows("work_orders.csv")}
    trail = Trail(bundle, wos)
    got = trail("bmc25-000013")
    assert got is not None and got["work_order"]["work_order_id"] == "WO25-00004"
    assert "WO25-00004" in got["answer"] and "Western Coast Asphalt" in got["answer"] and "₹" in got["answer"]
    mr = trail("BMC25-000013", "mr")
    assert mr is not None and "काम आदेश" in mr["answer"]
    assert trail("BMC25-999999") is None
    open_one = next(c for c in bundle["complaints"] if c["state"] == "open, overdue")
    o = trail(open_one["complaint_id"])
    assert o is not None and o["work_order"] is None and "still open" in o["answer"]


# AC7 · R6, R8: outputs and endpoints ---------------------------------------------------------------------------


def test_spec040_ac7_the_build_writes_files_a_judge_can_open(tmp_path: Path, bundle) -> None:  # type: ignore[no-untyped-def]
    paths = build.write(bundle, tmp_path)
    assert {p.name for p in paths} == {
        "bundle.json",
        "flags.csv",
        "complaints_linked.csv",
        "next_rupee.csv",
        "scorecards.csv",
    }
    with (tmp_path / "flags.csv").open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == len(bundle["flags"]) and rows[0]["evidence"].startswith("work_orders.csv#L")


@pytest.fixture
def web(tmp_path: Path, bundle) -> TestClient:  # type: ignore[no-untyped-def]
    build.write(bundle, tmp_path)

    @contextmanager
    def nothing():  # type: ignore[no-untyped-def]
        yield None

    store = LocalStore(tmp_path / "none")
    return TestClient(
        create_app(ApiConfig(connect=nothing, sources=store, data=store, graph_driver=None, rupee_dir=tmp_path))
    )


def test_spec040_ac7_the_endpoints_serve_the_bundle(web: TestClient) -> None:
    s = web.get("/rupee/summary").json()
    assert s["flags"]["overbilled"]["count"] == 109 and len(s["wards"]) == 24 and len(s["contractors"]) == 8
    w = web.get("/rupee/ward", params={"code": "f/s"}).json()
    assert w["ward_code"] == "F/S" and w["plan"]["items"] and all(f["ward_code"] == "F/S" for f in w["flag_list"])
    assert web.get("/rupee/ward", params={"code": "Z"}).status_code == 404
    c = web.get("/rupee/contractor", params={"id": "CT03"}).json()
    assert c["contractor_id"] == "CT03" and c["note"]["text"]
    f = web.get("/rupee/flags", params={"rule": "duplicate"}).json()
    assert f["total"] == 45 and all(x["rule"] == "duplicate" for x in f["items"])
    wo = web.get("/rupee/workorder", params={"id": "WO25-00004"}).json()
    assert {x["complaint_id"] for x in wo["complaints"]} == {"BMC25-000012", "BMC25-000013"}
    t = web.get("/rupee/complaint", params={"id": "BMC25-000013", "lang": "hi"}).json()
    assert "कार्य आदेश" in t["answer"]
    shapes = web.get("/rupee/wards.geojson").json()
    assert all("grade" in f["properties"] for f in shapes["features"])
    assert web.get("/rupee/plan").json()["city_top"]


def test_spec040_ac7_without_a_bundle_the_endpoints_say_so(tmp_path: Path) -> None:
    @contextmanager
    def nothing():  # type: ignore[no-untyped-def]
        yield None

    store = LocalStore(tmp_path / "none")
    app = create_app(ApiConfig(connect=nothing, sources=store, data=store, graph_driver=None, rupee_dir=tmp_path))
    assert TestClient(app).get("/rupee/summary").status_code == 503
    off = create_app(ApiConfig(connect=nothing, sources=store, data=store, graph_driver=None))
    assert TestClient(off).get("/rupee/summary").status_code == 404
