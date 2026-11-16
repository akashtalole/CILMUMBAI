"""Regenerate the test fixtures. Not run in CI: the outputs are committed.

    uv run python tests/fixtures/make_fixtures.py /path/to/NotoSansDevanagari-Regular.ttf

The documents are invented test data, marked as such on every page.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pymupdf

HERE = Path(__file__).parent
MARK = "TEST FIXTURE - invented data, not a real tender"


def _text_page(doc: pymupdf.Document, lines: list[tuple[str, str]], font: str | None) -> None:
    page = doc.new_page()
    if font:
        page.insert_font(fontname="deva", fontfile=font)
    y = 72.0
    for kind, text in lines:
        page.insert_text((60, y), text, fontname="deva" if kind == "mr" else "helv", fontsize=12)
        y += 24


def _scanned_page(doc: pymupdf.Document, text: str) -> None:
    """A page that is only an image of text, like a scan: no text layer."""
    source = pymupdf.open()
    page = source.new_page()
    page.insert_text((60, 72), text, fontname="helv", fontsize=12)
    image = page.get_pixmap(dpi=72).tobytes("png")
    target = doc.new_page()
    target.insert_image(target.rect, stream=image)


def main(font: str) -> None:
    english = pymupdf.open()
    _text_page(
        english,
        [
            ("en", MARK),
            ("en", "Brihanmumbai Municipal Corporation"),
            ("en", "Roads and Traffic Department, K/West Ward"),
            ("en", "Tender Ref. No. TEST/KW/ROADS/0001"),
            ("en", "Estimated cost: Rs. 4,20,00,000"),
        ],
        None,
    )
    _text_page(
        english,
        [
            ("en", MARK),
            ("en", "Defect liability period: 5 years from completion"),
            ("en", "Period of work: 18 months including monsoon"),
        ],
        None,
    )
    english.set_metadata({"producer": "fixture", "creationDate": "D:20261116000000", "modDate": "D:20261116000000"})
    english.save(HERE / "tender-en.pdf", garbage=4, deflate=True, no_new_id=True)

    mixed = pymupdf.open()
    _text_page(mixed, [("en", MARK), ("mr", "बृहन्मुंबई महानगरपालिका"), ("en", "Tender Ref. No. TEST/KW/SWD/0002")], font)
    _text_page(
        mixed, [("en", MARK), ("mr", "रस्ते विभाग, के पश्चिम विभाग"), ("en", "Estimated cost: Rs. 1,15,50,000")], font
    )
    _text_page(mixed, [("en", MARK), ("mr", "दोष दायित्व कालावधी: पाच वर्षे")], font)
    _scanned_page(mixed, "Scanned page: work order " + MARK)
    mixed.set_metadata({"producer": "fixture", "creationDate": "D:20261116000000", "modDate": "D:20261116000000"})
    mixed.save(HERE / "tender-mixed.pdf", garbage=4, deflate=True, no_new_id=True)

    picture = pymupdf.open()
    page = picture.new_page(width=200, height=80)
    page.insert_text((10, 40), "Site board photo (fixture)", fontname="helv", fontsize=10)
    (HERE / "site-board.png").write_bytes(page.get_pixmap(dpi=72).tobytes("png"))

    (HERE / "error-page.html").write_text(
        "<!DOCTYPE html><html><head><title>Session expired</title></head>"
        "<body>Please enter the captcha.</body></html>\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main(sys.argv[1])
