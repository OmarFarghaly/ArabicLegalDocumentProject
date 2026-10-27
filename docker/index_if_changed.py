import hashlib
import os
import subprocess
import sys
from pathlib import Path

from qdrant_client import QdrantClient

ARTICLES_PATH = Path("/app/data/processed/articles.json")
INDEX_STATE_PATH = Path("/var/lib/index-state/articles.v2.sha256")
COLLECTION_NAME = os.environ.get("COLLECTION_NAME", "legel_document")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def index_is_current(current_hash: str) -> bool:
    try:
        previous_hash = INDEX_STATE_PATH.read_text(encoding="ascii").strip()
    except FileNotFoundError:
        return False

    if previous_hash != current_hash:
        return False

    client = QdrantClient(
        host=os.environ.get("QDRANT_HOST", "qdrant"),
        port=int(os.environ.get("QDRANT_PORT", "6333")),
    )
    try:
        if not client.collection_exists(collection_name=COLLECTION_NAME):
            return False
        return client.count(
            collection_name=COLLECTION_NAME,
            exact=False,
        ).count > 0
    finally:
        client.close()


def main() -> None:
    current_hash = file_sha256(ARTICLES_PATH)
    INDEX_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)

    if index_is_current(current_hash):
        print("Articles are unchanged; skipping index build.")
        return

    subprocess.run(
        [sys.executable, "-m", "src.vectordb.build_index"],
        check=True,
        cwd="/app",
    )
    INDEX_STATE_PATH.write_text(current_hash, encoding="ascii")


if __name__ == "__main__":
    main()
