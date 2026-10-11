from llm.prompt_templates import (
    SYSTEM_PROMPT,
    build_llm_request,
    format_article,
    format_context,
)
from src.schemas.llm import LLMRequest

PAYLOAD = {
    "article_number": 147,
    "ar_text": "العقد شريعة المتعاقدين",
    "text_en": "The contract is the law of the parties",
    "book": "Obligations or Personal Rights",
    "chapter": "Effects of Contracts",
    "section": None,
    "topic": "Binding force of contracts",
    "is_repealed": False,
    "source_page": 52,
    "citation": "Egyptian Civil Code, Article 147",
}


def numbered(n):
    return {**PAYLOAD, "article_number": n}


def test_article_contains_every_citation_field():
    text = format_article(PAYLOAD)
    assert 'number="147"' in text
    assert "Book: Obligations or Personal Rights" in text
    assert "Chapter: Effects of Contracts" in text
    assert "Topic: Binding force of contracts" in text
    assert "Source: Egyptian Civil Code, Article 147" in text
    assert "العقد شريعة المتعاقدين" in text
    assert "The contract is the law of the parties" in text


def test_empty_optional_fields_are_skipped():
    assert "Section:" not in format_article(PAYLOAD)
    minimal = {k: PAYLOAD[k] for k in ("article_number", "ar_text", "text_en")}
    assert "Book:" not in format_article(minimal)


def test_repealed_article_is_flagged():
    assert 'status="REPEALED"' in format_article({**PAYLOAD, "is_repealed": True})


def test_context_respects_max_docs_and_keeps_order():
    docs = format_context([numbered(1), numbered(2), numbered(3)], max_docs=2)
    assert len(docs) == 2
    assert 'number="1"' in docs[0] and 'number="2"' in docs[1]


def test_context_respects_char_budget_but_keeps_first_article():
    size = len(format_article(PAYLOAD))
    assert len(format_context([numbered(1), numbered(2)], max_chars=size)) == 1
    assert len(format_context([numbered(1)], max_chars=1)) == 1


def test_build_request_fills_llm_request_fields():
    request = build_llm_request("  ما هو عقد البيع؟  ", [PAYLOAD])
    assert isinstance(request, LLMRequest)
    assert request.query == "ما هو عقد البيع؟"
    assert request.system_prompt == SYSTEM_PROMPT
    assert len(request.context_documents) == 1


def test_no_payloads_gives_empty_context():
    assert build_llm_request("question", []).context_documents == []
