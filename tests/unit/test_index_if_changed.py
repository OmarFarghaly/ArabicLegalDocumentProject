import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture
def index_if_changed_module():
    module_path = Path(__file__).parents[2] / "docker" / "index_if_changed.py"
    spec = importlib.util.spec_from_file_location("index_if_changed", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_index_is_current_requires_nonempty_qdrant_collection(
    index_if_changed_module, monkeypatch, tmp_path
):
    state_path = tmp_path / "articles.sha256"
    state_path.write_text("current-hash", encoding="ascii")
    client = SimpleNamespace(
        collection_exists=lambda collection_name: True,
        count=lambda **kwargs: SimpleNamespace(count=5),
        close=lambda: None,
    )
    monkeypatch.setattr(index_if_changed_module, "INDEX_STATE_PATH", state_path)
    monkeypatch.setattr(
        index_if_changed_module,
        "QdrantClient",
        lambda **kwargs: client,
    )

    assert index_if_changed_module.index_is_current("current-hash") is True


def test_empty_collection_triggers_reindex(
    index_if_changed_module, monkeypatch, tmp_path
):
    state_path = tmp_path / "articles.sha256"
    state_path.write_text("current-hash", encoding="ascii")
    client = SimpleNamespace(
        collection_exists=lambda collection_name: True,
        count=lambda **kwargs: SimpleNamespace(count=0),
        close=lambda: None,
    )
    monkeypatch.setattr(index_if_changed_module, "INDEX_STATE_PATH", state_path)
    monkeypatch.setattr(
        index_if_changed_module,
        "QdrantClient",
        lambda **kwargs: client,
    )

    assert index_if_changed_module.index_is_current("current-hash") is False


def test_changed_data_triggers_reindex_without_qdrant_check(
    index_if_changed_module, monkeypatch, tmp_path
):
    state_path = tmp_path / "articles.sha256"
    state_path.write_text("old-hash", encoding="ascii")
    monkeypatch.setattr(index_if_changed_module, "INDEX_STATE_PATH", state_path)

    def unexpected_qdrant_connection(**kwargs):
        pytest.fail("Qdrant should not be checked when the data hash changed")

    monkeypatch.setattr(
        index_if_changed_module,
        "QdrantClient",
        unexpected_qdrant_connection,
    )

    assert index_if_changed_module.index_is_current("new-hash") is False
