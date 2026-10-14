import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from config.config import Config
from schemas.extracted_record import ExtractedRecord

VALID = {
    "article_number": 1,
    "ar_text": "نص",
    "text_en": "text",
    "is_repealed": False,
    "source_page": 1,
    "citation": "Egyptian Civil Code, Article 1",
}


def test_valid_record_passes():
    assert ExtractedRecord(**VALID).book is None


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        ExtractedRecord(**VALID, surprise="x")


def test_missing_required_field_is_rejected():
    bad = {k: v for k, v in VALID.items() if k != "ar_text"}
    with pytest.raises(ValidationError):
        ExtractedRecord(**bad)


def test_config_requires_env(monkeypatch):
    monkeypatch.delenv("COLLECTION_NAME")
    with pytest.raises(ValidationError):
        Config(_env_file=None)


@pytest.mark.skipif(not Path("data/processed/articles.json").exists(), reason="no data")
def test_committed_articles_json_matches_schema():
    for rec in json.loads(
        Path("data/processed/articles.json").read_text(encoding="utf-8")
    ):
        ExtractedRecord.model_validate(rec)
