from src.prompt_template import (
    SYSTEM_PROMPT,
    build_llm_request,
    ensure_article_citations,
    format_article,
    format_citation,
    format_context,
)
from src.schemas.llm import LLMRequest
from src.schemas.rag import Payload

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
    text = format_article(PAYLOAD, "english")
    assert 'number="147"' in text
    assert "Book: Obligations or Personal Rights" in text
    assert "Chapter: Effects of Contracts" in text
    assert "Topic: Binding force of contracts" in text
    assert "Source: Egyptian Civil Code, Article 147" in text
    assert "The contract is the law of the parties" in text
    assert "العقد شريعة المتعاقدين" not in text
    assert 'number="147"' in text


def test_article_uses_only_requested_arabic_text():
    text = format_article(PAYLOAD, "arabic")
    assert "العقد شريعة المتعاقدين" in text
    assert "The contract is the law of the parties" not in text
    assert "الكتاب: Obligations or Personal Rights" in text
    assert "Book:" not in text


def test_citation_includes_article_number_and_available_metadata():
    citation = format_citation(PAYLOAD, "english")
    assert citation.startswith("Article 147")
    assert "Book: Obligations or Personal Rights" in citation
    assert "Chapter: Effects of Contracts" in citation
    assert "Section:" not in citation
    assert "Topic: Binding force of contracts" in citation
    assert "Source: Egyptian Civil Code, Article 147" in citation


def test_answer_citations_include_metadata_for_each_cited_article():
    answer = "تسري القاعدة وفق المادة ٤٦، وتوضح المادة ٤٥ الاستثناء."
    result = ensure_article_citations(
        answer, [numbered(46), numbered(45), numbered(44)], "arabic"
    )
    assert "المراجع القانونية:" in result
    assert "- المادة 46،" in result
    assert "- المادة 45،" in result
    assert "المادة 44" not in result


def test_uncited_answer_gets_top_reranked_article_reference():
    result = ensure_article_citations(
        "الإجابة القانونية.", [numbered(46), numbered(45)], "arabic"
    )
    assert "المادة 46" in result
    assert "المادة 45" not in result


def test_empty_optional_fields_are_skipped():
    assert "Section:" not in format_article(PAYLOAD, "english")
    minimal = {k: PAYLOAD[k] for k in ("article_number", "ar_text", "text_en")}
    assert "Book:" not in format_article(minimal, "english")


def test_repealed_article_is_flagged():
    assert 'status="REPEALED"' in format_article(
        {**PAYLOAD, "is_repealed": True}, "english"
    )


def test_context_respects_max_docs_and_keeps_order():
    docs = format_context(
        [numbered(1), numbered(2), numbered(3)], "english", max_docs=2
    )
    assert len(docs) == 2
    assert 'number="1"' in docs[0] and 'number="2"' in docs[1]


def test_context_respects_char_budget_but_keeps_first_article():
    size = len(format_article(PAYLOAD, "english"))
    docs = format_context(
        [numbered(1), numbered(2)], "english", max_chars=size
    )
    assert len(docs) == 1
    assert len(format_context([numbered(1)], "english", max_chars=1)) == 1


def test_build_request_fills_llm_request_fields():
    request = build_llm_request("  ما هو عقد البيع؟  ", [PAYLOAD], "arabic")
    assert isinstance(request, LLMRequest)
    assert request.query == "ما هو عقد البيع؟"
    assert request.system_prompt is not None
    assert request.system_prompt.startswith(SYSTEM_PROMPT)
    prompt = " ".join(request.system_prompt.split())
    assert "Required response language: Arabic." in prompt
    assert (
        "Cite every legal claim with the actual article number"
        in prompt
    )
    assert "Never cite a retrieval label" in prompt
    assert "[Document 1]" in prompt
    assert "include every metadata field available" in prompt
    assert "even when only one" in prompt
    assert "cite each article separately" in prompt
    assert len(request.context_documents) == 1


def test_no_payloads_gives_empty_context():
    assert build_llm_request("question", [], "english").context_documents == []


def test_accepts_pydantic_payload_objects():
    payload = Payload(**{k: PAYLOAD[k] for k in Payload.model_fields})
    request = build_llm_request("question", [payload], "english")
    assert 'number="147"' in request.context_documents[0]