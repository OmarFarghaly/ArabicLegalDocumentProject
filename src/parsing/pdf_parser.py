from __future__ import annotations

import bisect
import copy
import json
import re
from dataclasses import dataclass
from pathlib import Path

import pymupdf as fitz  # PyMuPDF

ARABIC_RE = re.compile(r"[\u0600-\u06FF]")
LATIN_RE = re.compile(r"[A-Za-z]")
ARABIC_DIGIT_ONLY_RE = re.compile(r"^[\s()\[\]{}٠-٩0-9.\-]+$")


def clean_text(parts: list[str]) -> str:
    """
    Take multiple pieces of text and turn them
    into one clean string.
    """
    text = " ".join(p.strip() for p in parts if p and p.strip())
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s+([,.;:!?،؛؟])", r"\1", text)
    return text


def smart_title(text: str) -> str:
    """
    Clean up a heading/title.
    """
    text = re.sub(r"\s+", " ", text).strip(" :-")
    if not text:
        return text
    if text.isupper():
        small = {"of", "or", "and", "the", "a", "an", "in", "on", "to", "for", "by", "with"}
        words = text.lower().split()
        return " ".join(
            w if i > 0 and w in small else w[:1].upper() + w[1:]
            for i, w in enumerate(words)
        )
    return text


def scalar_pos(page: int, y: float) -> float:
    """
    Convert page number + vertical position
    into one number representing the position
    in the entire document.

    This makes it easier to compare locations
    between different PDF pages.
    """
    # The PDF pages are < 1000 points high, so this gives a stable document position.
    return (page - 1) * 1000.0 + y


@dataclass
class Context:
    """
    Stores where an article belongs
    in the legal document.
    """
    part_title: str | None = None
    literal_book_title: str | None = None
    chapter: str | None = None
    section: str | None = None
    topic: str | None = None


@dataclass
class Line:
    """
    Represents one line extracted from the PDF.
    """
    page: int
    x0: float
    x1: float
    y0: float
    y1: float
    text: str
    col: str

    @property
    def spos(self) -> float:
        """
        Return this line's position
        in the entire document.
        """
        return scalar_pos(self.page, self.y0)


def extract_word_lines(doc: fitz.Document) -> list[Line]:
    """
    Extract logical lines from the PDF.

    The PDF has English on the left
    and Arabic on the right.
    """
    out: list[Line] = []

    for page_no, page in enumerate(doc, start=1):
        mid = page.rect.width / 2
        groups: dict[tuple[int, int], list[tuple]] = {}

        for word in page.get_text("words"):
            # x0, y0, x1, y1, text, block_no, line_no, word_no
            groups.setdefault((word[5], word[6]), []).append(word)

        for words in groups.values():
            words.sort(key=lambda w: w[7])
            text = clean_text([w[4] for w in words])
            if not text:
                continue

            x0 = min(w[0] for w in words)
            x1 = max(w[2] for w in words)
            y0 = min(w[1] for w in words)
            y1 = max(w[3] for w in words)

            ar_count = sum(1 for c in text if "\u0600" <= c <= "\u06FF")
            en_count = sum(1 for c in text if c.isascii() and c.isalpha())

            if x1 < mid + 8 and en_count >= ar_count:
                col = "en"
            elif x0 > mid - 8 and ar_count > 0:
                col = "ar"
            else:
                col = "ar" if ar_count > en_count else "en"

            out.append(Line(page_no, x0, x1, y0, y1, text, col))

    return out


def extract_bold_english_lines(doc: fitz.Document) -> list[Line]:
    """
    Find bold English lines.

    Bold text is used as a signal for headings
    such as PART, BOOK, CHAPTER, SECTION, etc.
    """
    out: list[Line] = []

    for page_no, page in enumerate(doc, start=1):
        mid = page.rect.width / 2
        data = page.get_text("dict")

        for block in data.get("blocks", []):
            for line in block.get("lines", []):
                spans = line.get("spans", [])
                if not spans:
                    continue

                text = clean_text([s.get("text", "") for s in spans])
                if not text or not LATIN_RE.search(text):
                    continue

                x0 = min(s["bbox"][0] for s in spans)
                y0 = min(s["bbox"][1] for s in spans)
                x1 = max(s["bbox"][2] for s in spans)
                y1 = max(s["bbox"][3] for s in spans)

                # Only the left/English column.
                if x0 >= mid:
                    continue

                total_chars = sum(max(1, len(s.get("text", ""))) for s in spans)
                bold_chars = sum(
                    max(1, len(s.get("text", "")))
                    for s in spans
                    if "Bold" in s.get("font", "") or (s.get("flags", 0) & 16)
                )
                if bold_chars / total_chars < 0.5:
                    continue

                out.append(Line(page_no, x0, x1, y0, y1, text, "en"))

    return out


def build_context_timeline(bold_lines: list[Line]):
    """
    Read headings and keep track of the
    current Part / Book / Chapter / Section / Topic.
    """
    ctx = Context()
    pending: str | None = None
    timeline: list[tuple[float, Context]] = []
    heading_positions: list[float] = []

    def update(pos: float):
        timeline.append((pos, copy.deepcopy(ctx)))
        heading_positions.append(pos)

    for line in sorted(bold_lines, key=lambda x: (x.page, x.y0, x.x0)):
        text = line.text.strip()
        pos = line.spos

        if re.fullmatch(r"(?:FIRST|SECOND|THIRD|FOURTH|FIFTH|SIXTH)\s+PART", text, re.I):
            pending = "part_title"
            update(pos)
            continue
        if re.fullmatch(r"BOOK\s+[IVXLC]+", text, re.I):
            pending = "literal_book_title"
            update(pos)
            continue
        if re.fullmatch(r"CHAPTER\s+[IVXLC]+", text, re.I):
            pending = "chapter"
            update(pos)
            continue
        if re.fullmatch(r"SECTION\s+[IVXLC]+", text, re.I):
            pending = "section"
            update(pos)
            continue

        if pending:
            value = smart_title(text)
            setattr(ctx, pending, value)
            if pending == "part_title":
                ctx.literal_book_title = ctx.chapter = ctx.section = ctx.topic = None
            elif pending == "literal_book_title":
                ctx.chapter = ctx.section = ctx.topic = None
            elif pending == "chapter":
                ctx.section = ctx.topic = None
            elif pending == "section":
                ctx.topic = None
            pending = None
            update(pos)
            continue

        # Remaining bold English lines are local topics/subtopics.
        # Examples in this PDF: "1. Elements of Contracts", "Consent:",
        # "2. The Effects of a Contract", "Nullity:".
        m = re.match(r"^\s*\d+\.\s*(.+)$", text)
        if m:
            ctx.topic = smart_title(m.group(1))
            update(pos)
            continue

        if len(text) <= 100 and not re.match(r"^Article\s+\d+", text, re.I):
            ctx.topic = smart_title(text.rstrip(":"))
            update(pos)

    return timeline, sorted(set(heading_positions))


def context_at(timeline: list[tuple[float, Context]], spos: float) -> Context:
    """
    Find the most recent context before a given
    document position.
    """
    positions = [p for p, _ in timeline]
    i = bisect.bisect_right(positions, spos) - 1
    return copy.deepcopy(timeline[i][1]) if i >= 0 else Context()


def find_articles(lines: list[Line], timeline) -> list[dict]:
    """
    Find Article 1, Article 2, Article 3, etc.
    """
    articles = []
    for line in lines:
        if line.col != "en":
            continue
        m = re.match(r"^Article\s+(\d+)\b", line.text, re.I)
        if not m:
            continue
        n = int(m.group(1))
        articles.append({
            "number": n,
            "page": line.page,
            "start": line.spos,
            "context": context_at(timeline, line.spos),
        })
    articles.sort(key=lambda a: a["start"])
    return articles


def find_repealed_ranges(lines: list[Line]) -> list[tuple[int, int, int, float]]:
    """
    Find statements such as:

    Articles 50-55 have been repealed

    Return:
        start article
        end article
        page
        document position
    """
    ranges = []
    patterns = [
        re.compile(r"Articles?\s+(\d+)\s*[-–—]\s*(\d+)\s+have\s+been\s+repealed", re.I),
        re.compile(r"Articles?\s+(\d+)\s*[-–—]\s*(\d+)\s+repealed", re.I),
    ]

    for line in lines:
        for pat in patterns:
            m = pat.search(line.text)
            if m:
                ranges.append((int(m.group(1)), int(m.group(2)), line.page, line.spos))

    # De-duplicate ranges.
    dedup = {}
    for start, end, page, pos in ranges:
        dedup[(start, end)] = (start, end, page, pos)
    return list(dedup.values())


def is_repealed(article_number: int, ranges) -> bool:
    return any(start <= article_number <= end for start, end, _, _ in ranges)


def strip_english_article_label(text: str, number: int) -> str:
    return re.sub(rf"^\s*Article\s+{number}\b\s*", "", text, flags=re.I).strip()


def strip_arabic_article_label(text: str) -> str:
    text = text.strip()
    if ARABIC_DIGIT_ONLY_RE.fullmatch(text):
        return ""
    text = re.sub(r"^[()\s]*مادة[()\s٠-٩0-9]*", "", text).strip()
    if not text or ARABIC_DIGIT_ONLY_RE.fullmatch(text):
        return ""
    return text


def extract_records(pdf_path: Path) -> list[dict]:
    doc = fitz.open(pdf_path)
    lines = extract_word_lines(doc)
    bold_lines = extract_bold_english_lines(doc)
    timeline, heading_positions = build_context_timeline(bold_lines)
    articles = find_articles(lines, timeline)
    repealed_ranges = find_repealed_ranges(lines)

    heading_positions = sorted(heading_positions)
    records = []

    for i, article in enumerate(articles):
        start = article["start"]
        next_article = articles[i + 1]["start"] if i + 1 < len(articles) else float("inf")

        h_idx = bisect.bisect_right(heading_positions, start + 1e-6)
        next_heading = heading_positions[h_idx] if h_idx < len(heading_positions) else float("inf")
        end = min(next_article, next_heading)

        # Arabic article labels are sometimes a couple of points above the English label.
        selected = [line for line in lines if start - 4 <= line.spos < end - 0.5]

        english_lines = sorted(
            [l for l in selected if l.col == "en" and LATIN_RE.search(l.text)],
            key=lambda l: (l.page, round(l.y0, 1), l.x0),
        )
        # On the right-hand Arabic column, fragments on the same visual line must be read right-to-left.
        arabic_lines = sorted(
            [l for l in selected if l.col == "ar" and (ARABIC_RE.search(l.text) or re.search(r"[٠-٩]", l.text))],
            key=lambda l: (l.page, round(l.y0, 1), -l.x0),
        )

        en_parts = []
        for line in english_lines:
            text = strip_english_article_label(line.text, article["number"])
            if text and not re.match(r"^Article\s+\d+\b", text, re.I):
                en_parts.append(text)

        ar_parts = []
        for line in arabic_lines:
            text = strip_arabic_article_label(line.text)
            if text:
                ar_parts.append(text)

        ctx: Context = article["context"]
        records.append({
            "article_number": article["number"],
            # This maps FIRST PART to your requested `book` field so Article 147
            # becomes "Obligations or Personal Rights", matching your schema.
            "book": ctx.part_title or ctx.literal_book_title,
            "chapter": ctx.chapter,
            "section": ctx.section,
            "topic": ctx.topic,
            "ar_text": clean_text(ar_parts),
            "text_en": clean_text(en_parts),
            "is_repealed": is_repealed(article["number"], repealed_ranges),
            "source_page": article["page"],  # physical PDF page, 1-based
            "citation": f"Egyptian Civil Code, Article {article['number']}",
        })

    return records
