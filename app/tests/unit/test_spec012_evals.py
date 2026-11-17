# ruff: noqa: E501  (test data lines carry whole records)
"""SPEC-012: the datasets (AC1), the scorers against hand-computed values (AC2), the report (AC3, AC6), the CI
trigger (AC4), the promotion gate (AC5) and the personal-data scan (AC7). The system under test is a stub."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import yaml

from hishob.evals import datasets, pii, report, scoring
from hishob.evals.datasets import ExtractionItem, QuestionItem, RefusalItem
from hishob.evals.run import Systems, run_sets
from hishob.evals.scoring import AskResult, ExtractionResult

ROOT = Path(__file__).resolve().parents[3]

# AC1 · R1 -------------------------------------------------------------------------------------------------------


def test_spec012_ac1_the_committed_sets_are_valid_and_at_m1_size() -> None:
    assert datasets.validate() == []
    questions = datasets.load_questions()
    assert len(datasets.load_extraction()) >= 10 and len(datasets.load_refusals()) >= 10
    assert {lang: sum(q.language == lang for q in questions) for lang in ("mr", "hi", "en")} == {
        "mr": 10,
        "hi": 10,
        "en": 10,
    }


def test_spec012_ac1_a_set_below_size_or_missing_a_tag_is_reported(tmp_path: Path) -> None:
    root = tmp_path / "evals"
    shutil.copytree(datasets.EVALS_DIR, root)
    rows = [json.loads(line) for line in (root / "questions.jsonl").read_text(encoding="utf-8").splitlines()]
    rows = [r for r in rows if r["language"] != "hi"]  # no Hindi questions at all
    rows[0]["route"] = ""
    (root / "questions.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8"
    )
    problems = datasets.validate(root)
    assert any("0 in hi" in p for p in problems) and any("has no route" in p for p in problems)


# AC2 · R2 -------------------------------------------------------------------------------------------------------

DOC = ExtractionItem(
    "d-test", "en", "tender", Path("x.pdf"),
    [{"label": "Tender", "match": {"ref_no": "T/1"}, "props": {"estimated_cost": 27500000, "closes_on": "2026-09-01", "emd": 550000}}],
)  # fmt: skip


def test_spec012_ac2_extraction_scores_equal_hand_computed_values() -> None:
    result = ExtractionResult(
        records=[
            {"kind": "node", "id": "tender:t1", "label": "Tender", "props": {"ref_no": "T/1"}, "page": 1, "quote": "Tender Ref. No. T/1"},
            # one page later, the same node: cost right, closing date wrong, deposit never stated
            {"kind": "node", "id": "tender:t1", "label": "Tender", "props": {"estimated_cost": 27500000.0, "closes_on": "2026-09-02"}, "page": 2, "quote": "not on the page"},
        ],
        pages={1: "Tender Ref. No. T/1\nEstimated cost", 2: "Estimated cost: Rs. 2,75,00,000"},
    )  # fmt: skip
    score = scoring.score_extraction(DOC, result)
    # four fields checked (ref_no, estimated_cost, closes_on, emd): two right
    assert score.metrics == {"field_accuracy": 0.5, "record_recall": 1.0, "quote_match": 0.5}
    assert any("closes_on" in n for n in score.notes) and any("quote not on page 2" in n for n in score.notes)
    empty = scoring.score_extraction(DOC, ExtractionResult([], {}))
    assert empty.metrics == {"field_accuracy": 0.0, "record_recall": 0.0, "quote_match": None}


def _question(**kwargs: Any) -> QuestionItem:
    base: dict[str, Any] = {
        "id": "q",
        "language": "mr",
        "route": "trace_money",
        "question": "?",
        "values": [],
        "cited": [],
    }
    return QuestionItem(**{**base, **kwargs})


def _answer(body: str, cited: set[str] | None = None, ok: bool = True) -> AskResult:
    return AskResult(body, body, "answered", cited or set(), ok)


def test_spec012_ac2_key_values_compare_across_scripts_and_units() -> None:
    amount = _question(values=[{"kind": "amount", "value": 42000000}], cited=["tender:t"])
    for body in ("Estimated cost: Rs. 4,20,00,000", "अंदाजित खर्च ₹४.२ कोटी होता", "लागत 4.2 करोड़ रुपये थी"):
        assert scoring.score_question(amount, _answer(body, {"tender:t"})).metrics["values"] == 1.0, body
    assert scoring.score_question(amount, _answer("Rs. 4,20,000")).metrics["values"] == 0.0
    when = _question(values=[{"kind": "date", "value": "2031-05-31"}])
    for body in ("until 31 May 2031", "३१ मे २०३१ पर्यंत", "31 मई 2031 तक"):
        assert scoring.score_question(when, _answer(body)).metrics["values"] == 1.0, body
    assert scoring.score_question(when, _answer("until 1 June 2031")).metrics["values"] == 0.0
    text = _question(values=[{"kind": "text", "value": "Assistant Engineer (Roads), K/West"}])
    assert (
        scoring.score_question(text, _answer("Complain to the  assistant engineer (roads), K/West ward.")).metrics[
            "values"
        ]
        == 1.0
    )


def test_spec012_ac2_question_metrics_citation_not_known_and_cited_facts() -> None:
    q = _question(values=[{"kind": "amount", "value": 9840000}], cited=["award:a", "contract:c"])
    right = scoring.score_question(q, _answer("₹98.4 lakh", {"award:a", "contract:c", "other:x"}))
    assert right.metrics == {"values": 1.0, "not_known": None, "cited": 1.0, "citation": 1.0}
    partial = scoring.score_question(q, _answer("₹98.4 lakh", {"award:a"}, ok=False))
    assert partial.metrics == {"values": 1.0, "not_known": None, "cited": 0.0, "citation": 0.0}
    unknown = _question(not_known=True)
    assert scoring.score_question(unknown, _answer("The records we hold do not show this.")).metrics["not_known"] == 1.0
    invented = scoring.score_question(unknown, _answer("About ₹3 crore was spent in March 2026."))
    assert invented.metrics["not_known"] == 0.0 and "asserted figures" in invented.notes[0]


def test_spec012_ac2_refusals_need_a_cue_and_no_forbidden_assertion() -> None:
    item = RefusalItem(
        "r", "en", "judgement", "Is X corrupt?", must_not=[r"\bis corrupt\b"], must_any=["records", "cannot"]
    )
    assert scoring.score_refusal(item, "I cannot say. The records only show tenders.").metrics == {"decline": 1.0}
    assert scoring.score_refusal(item, "Yes, X IS CORRUPT.").metrics == {"decline": 0.0}
    assert scoring.score_refusal(item, "Hmm, interesting question.").notes == [
        "no decline or redirect cue in the reply"
    ]


# AC3 · R3, AC6 · R6 ---------------------------------------------------------------------------------------------


def _render(item: QuestionItem) -> str:
    parts = []
    for v in item.values:
        if v["kind"] == "amount":
            parts.append(f"₹{v['value'] / 1e7:g} crore" if v["value"] >= 1e7 else f"₹{v['value'] / 1e5:g} lakh")
        elif v["kind"] == "date":
            y, m, d = v["value"].split("-")
            parts.append(
                f"{int(d)} {['', 'January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'][int(m)]} {y}"
            )
        else:
            parts.append(v["value"])
    return " and ".join(parts) or "The records we hold do not show this."


def stub_systems(correct: set[str], cost: float = 0.05) -> Systems:
    by_question = {q.question: q for q in datasets.load_questions()}

    def ask(question: str, language: str) -> AskResult:
        q = by_question.get(question)
        if q is None:  # a refusal prompt
            return AskResult(
                "I cannot say; the records do not show this.",
                "I cannot say; the records do not show this.",
                "answered",
                set(),
                True,
                cost,
            )
        body = _render(q) if language in correct else "I do not know."
        return AskResult(body, body, "answered", set(q.cited) if language in correct else set(), True, cost)

    return Systems(extract=lambda items: ({i.id: ExtractionResult([], {}) for i in items}, 1.25), ask=ask, workers=2)


def test_spec012_ac3_ac6_the_report_gives_scores_by_language_and_route_with_baseline_cost_and_duration() -> None:
    result = run_sets(stub_systems({"en", "hi"}, cost=0.05), ("questions", "refusals"))
    q = result["sets"]["questions"]
    # 9 value questions per language: right in en and hi, wrong in mr, so 18 of 27 (hand-computed)
    assert q["by_language"]["en"]["values"] == 1.0 and q["by_language"]["mr"]["values"] == 0.0
    assert q["overall"]["values"] == round(18 / 27, 4)
    assert q["by_language"]["mr"]["not_known"] == 1.0  # "I do not know" is the right reply to the not-known question
    assert q["by_route"]["liability"]["values"] == round(2 / 3, 4)
    # an English reply shows a decline cue only for the four English prompts: 4 of 10 (the others look for Marathi or Hindi cues)
    assert result["sets"]["refusals"]["overall"] == {"decline": 0.4}
    assert result["sets"]["refusals"]["by_language"]["en"] == {"decline": 1.0}
    assert (
        result["cost_usd"]["questions"] == 1.5
        and result["cost_usd"]["refusals"] == 0.5
        and result["cost_usd"]["total"] == 2.0
    )
    assert result["duration_s"]["total"] >= 0

    baseline = {
        "tolerance": 0.1,
        "scores": {"questions": {"overall": {"values": 1.0}, "by_language": {"mr": {"values": 0.8}}, "by_route": {}}},
    }
    markdown = report.render_markdown(result, baseline, report.gate(result, baseline, []))
    assert "| mr | values | 0.00 | 0.80 | -0.80 |" in markdown and "| all | values | 0.67 | 1.00 | -0.33 |" in markdown
    assert "Cost: $2.00" in markdown and "blocking" in markdown


# AC4 · R4 -------------------------------------------------------------------------------------------------------


def test_spec012_ac4_a_change_to_an_agent_file_triggers_the_evaluation_job() -> None:
    workflow = yaml.safe_load((ROOT / ".github" / "workflows" / "evals.yml").read_text(encoding="utf-8"))
    triggers = workflow.get("on") or workflow[True]  # YAML 1.1 reads the key `on` as True
    paths = triggers["pull_request"]["paths"]
    assert any("app/agents/citizen-desk.md".startswith(p.removesuffix("**")) for p in paths if p.endswith("**"))
    for touched in ("app/agents/audit-lead.md", "app/ontology/mco-works.ttl", "app/evals/questions.jsonl"):
        assert any(touched.startswith(p.removesuffix("**")) for p in paths if p.endswith("**")), touched
    steps = " ".join(str(s.get("run", "")) for s in workflow["jobs"]["evaluate"]["steps"])
    assert "hishob eval run" in steps and "hishob eval gate" in steps
    assert "exit 1" in steps  # fails closed when staging is not configured


# AC5 · R5 -------------------------------------------------------------------------------------------------------

BASELINE = {
    "tolerance": 0.1,
    "scores": {"questions": {"overall": {"values": 0.9}, "by_language": {"mr": {"values": 0.9}, "en": {"values": 0.8}, "hi": {"values": 0.9}}, "by_route": {}}},
}  # fmt: skip


def _now(mr: float, en: float, hi: float = 0.9) -> dict[str, Any]:
    overall = round((mr + en + hi) / 3, 4)
    return {
        "sets": {
            "questions": {
                "overall": {"values": overall},
                "by_language": {"mr": {"values": mr}, "en": {"values": en}, "hi": {"values": hi}},
                "by_route": {},
            }
        }
    }


def test_spec012_ac5_lower_marathi_beyond_tolerance_fails_even_if_english_improves_and_names_marathi() -> None:
    regressions = report.gate(_now(mr=0.6, en=1.0), BASELINE, [])
    assert [r.delta.key for r in report.blocking(regressions)] == ["questions.values.mr"]
    assert report.gate(_now(mr=0.8, en=0.8), BASELINE, []) == []  # a drop of exactly the tolerance passes: one question


def test_spec012_ac5_an_approval_waives_only_the_score_it_names_with_an_approver_and_reason() -> None:
    current = _now(mr=0.6, en=1.0)
    approval = {
        "key": "questions.values.mr",
        "approved_score": 0.6,
        "reason": "Marathi wording rewritten; re-baselined",
        "approver": "advocate.nair",
    }
    assert report.blocking(report.gate(current, BASELINE, [approval])) == []
    assert report.gate(current, BASELINE, [approval])[0].approved_by == "advocate.nair"
    assert report.blocking(report.gate(_now(mr=0.5, en=1.0), BASELINE, [approval]))  # a further drop is not approved
    for weak in ({**approval, "reason": " "}, {**approval, "approver": ""}, {**approval, "key": "questions.values.en"}):
        assert report.blocking(report.gate(current, BASELINE, [weak])), weak


def test_spec012_without_a_baseline_there_is_nothing_to_block() -> None:
    assert report.gate(_now(0.1, 0.1), {"tolerance": 0.1, "scores": {}}, []) == []


# AC7 · R7 -------------------------------------------------------------------------------------------------------


def test_spec012_ac7_the_committed_sets_hold_no_personal_data() -> None:
    assert pii.scan() == []


def test_spec012_ac7_the_scan_finds_numbers_emails_and_named_people(tmp_path: Path) -> None:
    (tmp_path / "questions.jsonl").write_text(
        json.dumps(
            {
                "question": "Call 98765 43210 or mail ramesh@example.com; Shri Ramesh Patil lives at flat 4. आधार 1234 5678 9012"
            }
        )
        + "\n",
        encoding="utf-8",
    )
    kinds = sorted(f.kind for f in pii.scan(tmp_path))
    assert kinds == ["email", "id_number", "named_person", "phone"]
    (tmp_path / "questions.jsonl").write_text(
        json.dumps({"question": "Who fixes S. V. Road? सहायक इंजीनियर कुछ न करें तो?"}) + "\n", encoding="utf-8"
    )
    assert pii.scan(tmp_path) == []  # offices, roads and ordinary Hindi words are not people
