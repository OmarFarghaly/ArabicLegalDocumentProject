from parsing.pdf_parser import (
    Line,
    clean_text,
    find_articles,
    find_repealed_ranges,
    is_repealed,
    scalar_pos,
    smart_title,
    strip_arabic_article_label,
    strip_english_article_label,
)


def make_line(text, page=1, y=10.0, col="en"):
    return Line(page=page, x0=0, x1=1, y0=y, y1=y + 1, text=text, col=col)


def test_clean_text_joins_and_fixes_spacing():
    assert clean_text(["  hello ", "", "world ,"]) == "hello world,"


def test_smart_title_only_changes_uppercase_titles():
    assert smart_title("OBLIGATION OF THE SELLER") == "Obligation of the Seller"
    assert smart_title(" Sale : ") == "Sale"


def test_scalar_pos_orders_across_pages():
    assert scalar_pos(3, 50.0) == 2050.0
    assert scalar_pos(2, 0.0) > scalar_pos(1, 999.0)


def test_strip_english_label():
    assert (
        strip_english_article_label("Article 147 The contract is law", 147)
        == "The contract is law"
    )


def test_strip_arabic_label_and_number_only_lines():
    assert (
        strip_arabic_article_label("مادة ١٤٧ العقد شريعة المتعاقدين")
        == "العقد شريعة المتعاقدين"
    )
    assert strip_arabic_article_label("(١٤٧)") == ""


def test_find_articles_accepts_headings_and_rejects_references():
    lines = [
        make_line("Article 451", y=10),
        make_line("rticle 452", y=20),  # OCR drops the 'A'
        make_line("Article 444.", y=30),  # a reference, not a heading
        make_line("Article 9", y=40, col="ar"),  # wrong column
    ]
    assert [a["number"] for a in find_articles(lines, [])] == [451, 452]


def test_repealed_ranges():
    lines = [
        make_line("Articles 50-55 have been repealed"),
        make_line("Articles 50–55 repealed"),
    ]  # duplicate, different dash
    ranges = find_repealed_ranges(lines)
    assert len(ranges) == 1
    assert is_repealed(52, ranges) and not is_repealed(56, ranges)
