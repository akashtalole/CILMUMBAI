"""Regenerate the extraction evaluation set (SPEC-012). Not run in CI: the outputs are committed.

    uv run python evals/make_extraction_set.py /path/to/NotoSansDevanagari-Regular.ttf

Ten invented documents, each marked as such on every page, with the records an extractor should produce.
Nothing here is a real tender, and no private person appears (constitution C7).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pymupdf

HERE = Path(__file__).parent / "extraction"
MARK = "TEST FIXTURE - invented data, not a real tender"


def node(label: str, match: dict, **props: object) -> dict:
    """One expected node: found by its label and the `match` properties, then checked on `props`."""
    return {"label": label, "match": match, "props": props}


BMC = ("mr", "बृहन्मुंबई महानगरपालिका")
DOCS = [
    {
        "id": "d01-tender-roads", "language": "en", "route": "tender",
        "pages": [
            [("en", "Brihanmumbai Municipal Corporation"), ("en", "Roads and Traffic Department, G/North Ward"),
             ("en", "Tender Ref. No. TEST/GN/ROADS/0101"), ("en", "Estimated cost: Rs. 2,75,00,000")],
            [("en", "Bid closing date: 1 September 2026"), ("en", "Earnest money deposit: Rs. 5,50,000")],
        ],
        "expected": [node("Tender", {"ref_no": "TEST/GN/ROADS/0101"}, estimated_cost=27500000,
                          closes_on="2026-09-01", emd=550000)],
    },
    {
        "id": "d02-tender-drains-mr", "language": "mr", "route": "tender",
        "pages": [
            [BMC, ("mr", "पर्जन्य जलवाहिनी विभाग"), ("en", "Tender Ref. No. TEST/KE/SWD/0102"),
             ("en", "Estimated cost: Rs. 80,00,000")],
        ],
        "expected": [node("Tender", {"ref_no": "TEST/KE/SWD/0102"}, estimated_cost=8000000)],
    },
    {
        "id": "d03-award-en", "language": "en", "route": "award",
        "pages": [
            [("en", "Brihanmumbai Municipal Corporation"), ("en", "Standing Committee resolution TEST/SC/0103"),
             ("en", "The work under Tender Ref. No. TEST/GN/ROADS/0101 is awarded to"),
             ("en", "M/s Anand Constructions Pvt. Ltd. at Rs. 2,41,50,000."),
             ("en", "Date of award: 14 October 2026")],
        ],
        "expected": [node("Award", {}, value=24150000, awarded_on="2026-10-14"),
                     node("Contractor", {"name": "M/s Anand Constructions Pvt. Ltd."})],
    },
    {
        "id": "d04-corrigendum-en", "language": "en", "route": "corrigendum",
        "pages": [
            [("en", "Corrigendum No. 1 to Tender Ref. No. TEST/GN/ROADS/0101"),
             ("en", "The bid closing date is changed from 1 September 2026 to 8 September 2026."),
             ("en", "Published on 25 August 2026")],
        ],
        "expected": [node("Corrigendum", {}, published_on="2026-08-25", changed_field="closing date")],
    },
    {
        "id": "d05-work-order-en", "language": "en", "route": "work_order",
        "pages": [
            [("en", "Work Order No. TEST/WO/0105"), ("en", "Work: Resurfacing of Link Road, P/South Ward"),
             ("en", "Contract value: Rs. 1,12,00,000"), ("en", "Completion due on 31 March 2027"),
             ("en", "Contract period: 180 days")],
        ],
        "expected": [node("Work", {"title": "Resurfacing of Link Road"}, due_on="2027-03-31"),
                     node("Contract", {}, value=11200000, duration_days=180)],
    },
    {
        "id": "d06-completion-mr", "language": "mr", "route": "completion",
        "pages": [
            [BMC, ("mr", "पूर्णत्व प्रमाणपत्र"), ("en", "Work: Footpath reconstruction, M/West Ward"),
             ("mr", "काम पूर्ण झाल्याची तारीख: १२ जुलै २०२६")],
        ],
        "expected": [node("Work", {"title": "Footpath reconstruction"}, completed_on="2026-07-12")],
    },
    {
        "id": "d07-penalty-en", "language": "en", "route": "penalty",
        "pages": [
            [("en", "Penalty notice"),
             ("en", "A penalty of Rs. 20,00,000 is imposed on M/s Bhoomi Infra Ltd."),
             ("en", "on 3 September 2026 for substandard concrete work.")],
        ],
        "expected": [node("Penalty", {}, amount=2000000, imposed_on="2026-09-03", reason="substandard concrete"),
                     node("Contractor", {"name": "M/s Bhoomi Infra Ltd."})],
    },
    {
        "id": "d08-tender-hi", "language": "hi", "route": "tender",
        "pages": [
            [("hi", "बृहन्मुंबई महानगरपालिका"), ("hi", "सड़क विभाग"),
             ("en", "Tender Ref. No. TEST/HW/ROADS/0108"), ("en", "Estimated cost: Rs. 3,60,00,000"),
             ("en", "Bid closing date: 20 November 2026")],
        ],
        "expected": [node("Tender", {"ref_no": "TEST/HW/ROADS/0108"}, estimated_cost=36000000,
                          closes_on="2026-11-20")],
    },
    {
        "id": "d09-dlp-en", "language": "en", "route": "dlp",
        "pages": [
            [("en", "Defect liability period for the work"), ("en", "Concretisation of Station Road, R/Central Ward:"),
             ("en", "from 1 August 2026 to 31 July 2031.")],
        ],
        "expected": [node("DefectLiabilityPeriod", {}, from_date="2026-08-01", to_date="2031-07-31"),
                     node("Work", {"title": "Concretisation of Station Road"})],
    },
    {
        "id": "d10-payment-hi", "language": "hi", "route": "payment",
        "pages": [
            [("hi", "भुगतान सूचना"),
             ("en", "Payment advice: Rs. 48,00,000 paid on 5 October 2026"),
             ("en", "to M/s Anand Constructions Pvt. Ltd. as running bill 1 under Contract TEST/CT/0110.")],
        ],
        "expected": [node("Payment", {}, amount=4800000, paid_on="2026-10-05"),
                     node("Contractor", {"name": "M/s Anand Constructions Pvt. Ltd."})],
    },
]


def main(font: str) -> None:
    for doc in DOCS:
        folder = HERE / doc["id"]
        folder.mkdir(parents=True, exist_ok=True)
        pdf = pymupdf.open()
        for lines in doc["pages"]:
            page = pdf.new_page()
            page.insert_font(fontname="deva", fontfile=font)
            y = 72.0
            for kind, text in [("en", MARK), *lines]:
                page.insert_text((60, y), text, fontname="helv" if kind == "en" else "deva", fontsize=12)
                y += 24
        pdf.set_metadata({"producer": "fixture", "creationDate": "D:20261116000000", "modDate": "D:20261116000000"})
        pdf.save(folder / "document.pdf", garbage=4, deflate=True, no_new_id=True)
        (folder / "expected.jsonl").write_text(
            "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in doc["expected"]), encoding="utf-8"
        )
        (folder / "meta.json").write_text(
            json.dumps({"id": doc["id"], "language": doc["language"], "route": doc["route"]}, indent=2) + "\n"
        )
    print(f"wrote {len(DOCS)} documents to {HERE}")


if __name__ == "__main__":
    main(sys.argv[1])
