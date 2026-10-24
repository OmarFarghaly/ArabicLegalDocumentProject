import re


_ARABIC_DIACRITICS_RE = re.compile(r"[\u064B-\u065F\u0670]")
_WHITESPACE_RE = re.compile(r"\s+")

_ARABIC_SPARSE_TRANSLATION = str.maketrans({
    "أ": "ا",
    "إ": "ا",
    "آ": "ا",
    "ٱ": "ا",
    "ى": "ي",
})


def normalize_arabic_for_sparse(text: str) -> str:
    """Normalize Arabic text for sparse retrieval without changing its meaning."""
    text = text.replace("ـ", "")
    text = _ARABIC_DIACRITICS_RE.sub("", text)
    text = text.translate(_ARABIC_SPARSE_TRANSLATION)
    return _WHITESPACE_RE.sub(" ", text).strip()