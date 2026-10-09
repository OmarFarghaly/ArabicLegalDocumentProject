import os

# Config() is built at import time in some modules, so the env must exist first.
os.environ.setdefault("APP_NAME", "TestApp")
os.environ.setdefault("ENGLISH_EMBEDDING", "fake-en-model")
os.environ.setdefault("ARABIC_EMBEDDING", "fake-ar-model")
os.environ.setdefault("COLLECTION_NAME", "test_collection")
os.environ.setdefault("RAW_PDF", "data/raw/civil_code.pdf")
os.environ.setdefault("ARTICLES_JSON", "data/processed/articles.json")
