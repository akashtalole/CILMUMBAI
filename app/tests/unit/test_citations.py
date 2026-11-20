"""SPEC-007 citation check (AC4, AC5, AC6) and its parsers."""

from hishob.api.citations import check, parse_amounts, parse_dates

TENDER = {
    "fact_id": "f1",
    "quote": "Estimated cost: Rs. 4,20,00,000",
    "props": {"estimated_cost": 42000000, "ref_no": "TEST/KW/ROADS/0001"},
}
WORK = {
    "fact_id": "f2",
    "quote": "Period of work: 18 months",
    "props": {"due_on": "2026-05-31", "title": "Concretisation of S. V. Road"},
}
AWARD = {"fact_id": "f3", "quote": "M/s Shree Ganesh Infra Pvt. Ltd. at Rs. 98,40,000.", "props": {"value": 9840000}}


def test_amounts_in_rupees_lakh_and_crore() -> None:
    values = [a.value for _, a, _ in parse_amounts("₹4.2 crore, Rs. 98,40,000 and 98.4 lakh, रु. ४२,००,००,०००")]
    assert values == [42000000, 9840000, 9840000, 420000000]


def test_dates_in_many_forms_and_languages() -> None:
    found = [d for _, d, _ in parse_dates("31 May 2026, 31/05/2026, May 31, 2026, ३१ मे २०२६, 31 मई 2026, May 2026")]
    assert found == [(2026, 5, 31)] * 5 + [(2026, 5, None)]


# AC4 · R5 -------------------------------------------------------------------------------------------------------


def test_spec007_ac4_an_answer_that_states_only_cited_values_passes() -> None:
    answer = "Contract value ₹4.2 crore, due 31 May 2026 [f1, f2]. Tender TEST/KW/ROADS/0001."
    result = check(answer, [TENDER, WORK])
    assert result.ok, result.unmatched
    assert {c.kind for c in result.matched} == {"amount", "date", "identifier"}


def test_spec007_ac4_names_must_appear_in_cited_facts() -> None:
    assert check("Awarded to Shree Ganesh Infra [f3].", [AWARD]).ok
    bad = check("Awarded to Lakshmi Constructions [f3].", [AWARD])
    assert not bad.ok and bad.unmatched[0].kind == "name"


# AC5 · R5, R6 ---------------------------------------------------------------------------------------------------


def test_spec007_ac5_a_changed_amount_fails_and_is_listed() -> None:
    result = check("Contract value ₹5 crore, due 31 May 2026 [f1, f2].", [TENDER, WORK])
    assert not result.ok
    assert [(c.kind, c.text) for c in result.unmatched] == [("amount", "₹5 crore")]


def test_spec007_ac5_dates_and_identifiers_are_checked_too() -> None:
    result = check("Due 30 June 2026 under tender TEST/KW/ROADS/0009.", [TENDER, WORK])
    assert sorted(c.kind for c in result.unmatched) == ["date", "identifier"]


def test_spec007_ac5_citing_a_fact_that_does_not_exist_fails() -> None:
    result = check("Nothing specific.", [], missing_ids=["f_missing"])
    assert not result.ok and result.unmatched[0].kind == "fact_id"


# AC6 · R5 -------------------------------------------------------------------------------------------------------


def test_spec007_ac6_marathi_answer_with_devanagari_numerals_matches() -> None:
    answer = "अंदाजित खर्च ₹४.२ कोटी आहे आणि काम ३१ मे २०२६ पर्यंत पूर्ण व्हायचे आहे."
    assert check(answer, [TENDER, WORK]).ok


def test_spec007_ac6_hindi_answer_with_wrong_amount_fails() -> None:
    result = check("अनुमानित लागत ₹५ करोड़ है।", [TENDER])
    assert not result.ok and result.unmatched[0].text == "₹5 करोड़"


def test_rounding_follows_what_the_answer_states() -> None:
    assert check("About ₹98 lakh.", [AWARD]).ok
    assert not check("About ₹9 lakh.", [AWARD]).ok


def test_a_name_does_not_run_across_a_line_break() -> None:
    # Found by the photo report: a letter's address block ended "Executive Engineer (Roads), Western Suburbs", then a
    # blank line, then "Subject: ...". The words were joined into the name "Western Suburbs Subject", which no fact
    # holds, so the desk's English letters were rejected and replaced by the fallback.
    facts = [
        {
            "quote": "Executive Engineer (Roads), Western Suburbs",
            "props": {"title": "Executive Engineer (Roads), Western Suburbs"},
        }
    ]
    letter = (
        "To,\nThe Executive Engineer (Roads), Western Suburbs\n\nSubject: A pothole on the road\n\nAbout the pothole."
    )
    assert check(letter, facts).ok
    names = [c.text for c in check(letter, facts).matched + check(letter, facts).unmatched if c.kind == "name"]
    assert not any("Subject" in n or "About" in n for n in names)
    # a real name that is not in the facts is still caught, on one line
    assert [c.text for c in check("Complain to Ramesh Patil today.", facts).unmatched if c.kind == "name"] == [
        "Ramesh Patil"
    ]


def test_a_leading_article_is_not_part_of_a_name() -> None:
    facts = [{"quote": "Assistant Engineer (Roads), K/West", "props": {"title": "Assistant Engineer (Roads), K/West"}}]
    assert check("Respectfully, to The Assistant Engineer (Roads), K/West about the road.", facts).ok
    assert check("Dear Assistant Engineer, please act.", facts).ok  # "Dear" and a single word left: no name at all
