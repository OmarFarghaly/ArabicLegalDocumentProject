import importlib
import sys
import types
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel


@pytest.fixture
def build_index_module(monkeypatch):
    """Import build_index with a fake vector_store (no models, no Qdrant)."""
    fake = types.ModuleType("src.vectordb.vector_store")

    class Payload(BaseModel):
        model_config = {"extra": "allow"}

    fake.QdrantVectorStore = MagicMock
    fake.Payload = Payload
    monkeypatch.setitem(sys.modules, "src.vectordb.vector_store", fake)
    monkeypatch.delitem(sys.modules, "src.vectordb.build_index", raising=False)
    return importlib.import_module("src.vectordb.build_index")


def test_short_records_are_skipped(build_index_module, tmp_path):
    import json

    data = [
        {
            "article_number": 1,
            "ar_text": "نص عربي طويل كفاية",
            "text_en": "long enough text",
        },
        {"article_number": 2, "ar_text": "قصير", "text_en": "long enough text"},
        {"article_number": 3, "ar_text": "نص عربي طويل كفاية", "text_en": ""},
    ]
    path = tmp_path / "a.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    store = MagicMock()
    idx = build_index_module.IndexingStore(data_path=str(path), vector_store=store)

    assert idx.build_index(collection_name="c") is True
    store.delete_collection.assert_called_once_with(collection_name="c")
    store.create_collection.assert_called_once_with(collection_name="c")
    assert store.create.call_count == 1
