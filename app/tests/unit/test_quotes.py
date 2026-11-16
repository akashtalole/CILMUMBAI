from hishob.ledger.quotes import check, looks_garbled, normalise


def test_whitespace_and_line_breaks_do_not_matter() -> None:
    page = "Brihanmumbai Municipal Corporation\nRoads and Traffic   Department"
    assert check("Municipal Corporation Roads and Traffic Department", page) == "matched"


def test_case_punctuation_and_digits_must_match_exactly() -> None:
    page = "Estimated cost: Rs. 4,20,00,000"
    assert check("Rs. 4,20,00,000", page) == "matched"
    assert check("Rs. 4,20,00,001", page) == "quote_not_found"
    assert check("rs. 4,20,00,000", page) == "quote_not_found"


def test_nukta_forms_and_zero_width_characters_are_unified() -> None:
    precomposed, decomposed = "क़", "क़"  # क़ written two ways
    assert normalise(precomposed) == normalise(decomposed)
    assert check("स्त्री", "स्‍त्री") == "matched"


def test_pages_without_text_or_with_garbled_devanagari_are_unchecked() -> None:
    assert check("anything", None) == "scan_unchecked"
    garbled = "बृहõमुंबइǺ महानगरपाल का"  # what a shaped PDF can extract as
    assert looks_garbled(garbled)
    assert check("बृहन्मुंबई", garbled) == "scan_unchecked"
    assert not looks_garbled("बृहन्मुंबई महानगरपालिका, Café")
