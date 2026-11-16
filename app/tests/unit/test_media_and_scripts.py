from pathlib import Path

from hishob.archive import media
from hishob.archive.scripts import detect_scripts

FIXTURES = Path(__file__).parent.parent / "fixtures"


def test_recognises_pdf_png_and_refuses_html() -> None:
    assert media.sniff((FIXTURES / "tender-en.pdf").read_bytes()) == media.PDF
    assert media.sniff((FIXTURES / "site-board.png").read_bytes()) == media.PNG
    assert media.sniff((FIXTURES / "error-page.html").read_bytes()) is None


def test_refuses_empty_and_html_by_content_type() -> None:
    assert media.sniff(b"") is None
    assert media.sniff(b"Please log in", content_type="text/html; charset=utf-8") is None


def test_csv_json_geojson_and_office_files() -> None:
    assert media.sniff(b"ward,amount\nK/W,10\n", filename="budget.csv") == media.CSV
    assert media.sniff(b'{"a": 1}') == media.JSON
    assert media.sniff(b'{"type": "FeatureCollection", "features": []}') == media.GEOJSON
    assert media.sniff(b"PK\x03\x04rest", filename="Rates.XLSX") == media.XLSX
    assert media.sniff(b"PK\x03\x04rest", filename="archive.zip") is None


def test_detects_devanagari_and_latin() -> None:
    assert detect_scripts(["बृहन्मुंबई महानगरपालिका"]) == ["Deva"]
    assert detect_scripts(["Roads Department"]) == ["Latn"]
    assert detect_scripts(["रस्ते विभाग", "Roads"]) == ["Deva", "Latn"]
    assert detect_scripts(["12345 ..."]) == []
