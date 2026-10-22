import asyncio
from types import SimpleNamespace

from src.retrieval.reterival import Reterival


class StubEmbedding:
    def __init__(self):
        self.last_text = None

    def encode(self, text: str) -> list[float]:
        self.last_text = text
        return [0.1]


class StubClient:
    def __init__(self):
        self.kwargs = None

    async def query_points(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(points=[])


def test_arabic_query_normalizes_bm25_but_not_dense_embedding():
    arabic_embedding = StubEmbedding()
    retriever = Reterival(
        arabic_embedding=arabic_embedding,
        english_embedding=StubEmbedding(),
    )
    client = StubClient()
    retriever.client = client

    original_text = "أَحكامـى"

    asyncio.run(
        retriever.search(
            collection_name="articles",
            text=original_text,
            lang="arabic",
        )
    )

    prefetch = client.kwargs["prefetch"]

    assert arabic_embedding.last_text == original_text
    assert prefetch[1].query.text == "احكامي"