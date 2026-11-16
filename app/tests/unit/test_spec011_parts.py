"""SPEC-011 parts that need no services: agent definitions (AC1), layout by verdict (AC3, AC4), word rules (AC5)."""

from __future__ import annotations

from hishob.agentkit.definitions import apply_order, load_agents
from hishob.agentkit.outputs import arrange, banned_words, blocks, canonical, verdict
from hishob.agentkit.redact import honorific_names
from hishob.agentkit.tools import AUDIT_TOOL_DEFINITIONS, AUDIT_TOOLS
from tests.unit.test_spec005_agents import _enabled_tools

# AC1 · R1 -------------------------------------------------------------------------------------------------------


def test_spec011_ac1_the_lead_reads_only_through_the_api_tools() -> None:
    lead = load_agents()["audit-lead"].config
    custom = [t for t in lead["tools"] if t["type"] == "custom"]
    assert {t["name"] for t in custom} == AUDIT_TOOLS  # every one answered by ApiTools with a GET
    from_code = {t["name"]: t["input_schema"] for t in AUDIT_TOOL_DEFINITIONS}
    assert {t["name"]: t["input_schema"] for t in custom} == from_code
    assert not _enabled_tools(lead) & {"web_fetch", "web_search"}
    assert "mcp_servers" not in lead


def test_spec011_ac1_challenger_and_drafter_have_file_tools_only() -> None:
    agents = load_agents()
    for key in ("challenger", "drafter"):
        config = agents[key].config
        assert _enabled_tools(config) <= {"read", "glob", "grep", "write"}, key
        assert [t for t in config["tools"] if t["type"] != "agent_toolset_20260401"] == [], key
        assert "multiagent" not in config and "mcp_servers" not in config, key


def test_spec011_the_lead_is_applied_after_its_roster() -> None:
    order = apply_order(load_agents())
    assert order.index("challenger") < order.index("audit-lead") > order.index("drafter")


# AC3, AC4 · R3, R4 ----------------------------------------------------------------------------------------------


def test_spec011_files_are_placed_by_name_not_by_the_folder_the_agent_chose() -> None:
    assert canonical("/mnt/session/outputs/held/case-02-x.md") == "cases/case-02-x.md"
    assert canonical("rti-01.md") == "drafts/rti-01.md"
    assert canonical("cases/questions.md") == "drafts/questions.md"
    assert canonical("notes.txt") is None


def test_spec011_verdicts_are_read_from_the_last_verdict_line() -> None:
    assert verdict("Sound.\n\n**Verdict:** publish with changes") == "publish with changes"
    assert verdict("Earlier draft said Verdict: publish\n\nVerdict: hold") == "hold"
    assert verdict("No verdict here") is None


def test_spec011_ac3_ac4_only_cases_with_a_passing_review_stay_in_cases() -> None:
    out = arrange(
        {
            "cases/case-01-a.md": b"a",
            "cases/case-01-a.challenge.md": b"Verdict: publish",
            "cases/case-02-b.md": b"b",
            "cases/case-02-b.challenge.md": b"Verdict: hold\n",
            "case-03-c.md": b"c",
            "case-04-d.challenge.md": b"Verdict: publish",
            "scratch.txt": b"x",
        }
    )
    assert sorted(out.files) == [
        "cases/case-01-a.challenge.md",
        "cases/case-01-a.md",
        "held/case-02-b.challenge.md",
        "held/case-02-b.md",
        "held/case-03-c.md",
    ]
    assert out.held == {
        "held/case-02-b.md": "the Challenger held it",
        "held/case-03-c.md": "not reviewed by a Challenger",
    }
    assert out.unexpected == ["scratch.txt"]


# AC5 · R5 -------------------------------------------------------------------------------------------------------


def test_spec011_ac5_banned_words_in_three_languages_with_endings() -> None:
    assert banned_words("Signs of a SCAM and corruption; funds siphoned.") == ["SCAM", "corruption", "siphoned"]
    assert banned_words("हा घोटाळ्याचा प्रकार आहे") == ["घोटाळ्याचा"]
    assert banned_words("यह भ्रष्टाचार और धोखाधड़ी है") == ["भ्रष्टाचार", "धोखाधड़ी"]
    assert banned_words("The tender was cancelled and retendered; scamper is not a finding.") == []


def test_spec011_ac5_people_named_after_an_honorific_are_found_landmarks_are_not() -> None:
    text = "Approved by Shri Ramesh Patil near Shri Ganesh Mandir; श्री सुरेश जाधव यांनी सही केली."
    assert honorific_names(text) == ["Shri Ramesh Patil", "श्री सुरेश जाधव"]
    assert honorific_names(text, keep=["Ramesh Patil"]) == ["श्री सुरेश जाधव"]
    assert honorific_names("M/s Shree Ganesh Infra Pvt. Ltd. was awarded the work.") == []


def test_spec011_references_are_checked_per_paragraph_and_table_row() -> None:
    markdown = "# Case\n\nFirst line\ncontinues.\n\n| Claim | Value |\n|---|---|\n| Cost | Rs. 5 |\n\nLast."
    assert blocks(markdown) == ["First line continues.", "| Cost | Rs. 5 |", "Last."]
