from src.utils.arabic_text import normalize_arabic_for_sparse


def test_normalizes_alef_variants_and_alef_maqsura():
    assert normalize_arabic_for_sparse("أإآٱى") == "ااااي"


def test_removes_diacritics_and_tatweel():
    assert normalize_arabic_for_sparse("مُتَعاقدـون") == "متعاقدون"


def test_collapses_and_trims_whitespace():
    assert normalize_arabic_for_sparse("  العقد \n شريعة\tالمتعاقدين  ") == (
        "العقد شريعة المتعاقدين"
    )


def test_preserves_taa_marbuta_haa_and_hamza_letters():
    assert normalize_arabic_for_sparse("ة ه ؤ ئ") == "ة ه ؤ ئ"


def test_empty_text_stays_empty():
    assert normalize_arabic_for_sparse("") == ""