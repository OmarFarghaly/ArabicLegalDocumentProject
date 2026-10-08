# `civil_code_parser.py` — Simple Cell-by-Cell Explanation

This guide explains the supplied `civil_code_parser.py` file as if it were split into notebook-style **cells**.

The script's overall purpose is:

> **Read a bilingual Egyptian Civil Code PDF, detect English/Arabic article text and legal headings, determine the context of each article, and return structured Python dictionaries.**

The PDF is assumed to have:

- **English text on the left**
- **Arabic text on the right**
- headings such as `FIRST PART`, `BOOK I`, `CHAPTER II`, `SECTION III`
- article labels such as `Article 147` and Arabic labels such as `مادة 147`

---

## Big picture: what flows through the program?

```text
PDF file
   |
   v
PyMuPDF opens the PDF
   |
   +--> extract_word_lines() ---------> normal English/Arabic lines
   |
   +--> extract_bold_english_lines() -> headings only
                                      |
                                      v
                             build_context_timeline()
                                      |
                                      v
                             Part / Book / Chapter /
                             Section / Topic history

normal lines + timeline
   |
   +--> find_articles()
   +--> find_repealed_ranges()
   |
   v
extract_records()
   |
   v
[
  {
    "article_number": 147,
    "book": "Obligations or Personal Rights",
    "chapter": "...",
    "section": "...",
    "topic": "...",
    "ar_text": "...",
    "text_en": "...",
    "is_repealed": false,
    "source_page": 23,
    "citation": "Egyptian Civil Code, Article 147"
  }
]
```

---

# Cell 1 — Imports

## Original code

```python
from __future__ import annotations

import bisect
import copy
import json
import re
from dataclasses import dataclass
from pathlib import Path

import pymupdf as fitz  # PyMuPDF
```

## Line-by-line meaning

```python
from __future__ import annotations
# Tells Python to postpone evaluation of type annotations.
# This makes annotations such as list[Line] safer and more flexible.
```

Simple idea:

```python
def hello(name: str) -> str:
    return "Hello " + name
```

Here `str` is a **type hint**. It helps humans, editors, and type checkers understand expected types.

---

```python
import bisect
# Gives efficient tools for finding where a number belongs
# inside an already sorted list.
```

Example:

```python
import bisect

positions = [100, 200, 300]
index = bisect.bisect_right(positions, 220)
print(index)  # 2
```

Meaning: `220` would be inserted at index `2`, after `200` and before `300`.

This script later uses `bisect` to find:

- the latest heading before an article
- the next heading after an article

---

```python
import copy
# Used to duplicate objects.
# The script specifically uses copy.deepcopy().
```

Why?

```python
original = {"chapter": ["Chapter 1"]}
clone = copy.deepcopy(original)

clone["chapter"].append("Chapter 2")

print(original)
# {'chapter': ['Chapter 1']}
```

A deep copy prevents later changes from accidentally changing an older saved context.

---

```python
import json
# Python's JSON module.
```

Example:

```python
record = {"article_number": 147, "is_repealed": False}
print(json.dumps(record))
```

Possible output:

```json
{"article_number": 147, "is_repealed": false}
```

**Important:** in the supplied file, `json` is imported but is not actually used by the visible code. The script builds Python dictionaries, but this file does not contain the final JSON-writing step.

---

```python
import re
# Regular expressions.
# Used to recognize patterns inside strings.
```

Example:

```python
m = re.match(r"Article\s+(\d+)", "Article 147")
print(m.group(1))  # 147
```

---

```python
from dataclasses import dataclass
# Lets us create small data-holding classes without writing
# a manual __init__ method.
```

Example:

```python
@dataclass
class Person:
    name: str
    age: int

p = Person("Mina", 31)
```

---

```python
from pathlib import Path
# Modern Python way to represent file paths.
```

Example:

```python
pdf_path = Path("civil_code.pdf")
print(pdf_path.name)  # civil_code.pdf
```

---

```python
import pymupdf as fitz
# Imports PyMuPDF and gives it the shorter name `fitz`.
# PyMuPDF is the library that reads the PDF.
```

Example:

```python
doc = fitz.open("civil_code.pdf")
print(len(doc))
```

If the PDF has 250 pages, `len(doc)` is `250`.

---

# Cell 2 — Regular-expression constants

## Original code

```python
ARABIC_RE = re.compile(r"[\u0600-\u06FF]")
LATIN_RE = re.compile(r"[A-Za-z]")
ARABIC_DIGIT_ONLY_RE = re.compile(r"^[\s()\[\]{}٠-٩0-9.\-]+$")
```

These expressions are compiled once and reused many times.

## 2.1 `ARABIC_RE`

```python
ARABIC_RE = re.compile(r"[\u0600-\u06FF]")
```

Meaning:

- look for **at least one Arabic Unicode character**
- `\u0600` to `\u06FF` is a Unicode range containing Arabic characters

Example:

```python
bool(ARABIC_RE.search("Hello"))
# False

bool(ARABIC_RE.search("القانون المدني"))
# True
```

---

## 2.2 `LATIN_RE`

```python
LATIN_RE = re.compile(r"[A-Za-z]")
```

Meaning: find at least one English/Latin letter.

```python
bool(LATIN_RE.search("Article 147"))
# True

bool(LATIN_RE.search("١٤٧"))
# False
```

---

## 2.3 `ARABIC_DIGIT_ONLY_RE`

```python
ARABIC_DIGIT_ONLY_RE = re.compile(r"^[\s()\[\]{}٠-٩0-9.\-]+$")
```

Meaning: the **entire string** may contain only:

- whitespace
- parentheses/brackets/braces
- Arabic digits: `٠١٢٣٤٥٦٧٨٩`
- Western digits: `0123456789`
- period `.`
- hyphen `-`

Example:

```python
bool(ARABIC_DIGIT_ONLY_RE.fullmatch("(١٤٧)"))
# True

bool(ARABIC_DIGIT_ONLY_RE.fullmatch("مادة ١٤٧"))
# False
```

This helps the parser discard labels/numbers that contain no real article text.

---

# Cell 3 — `clean_text()`

## Original code

```python
def clean_text(parts: list[str]) -> str:
    """
    Take multiple pieces of text and turn them
    into one clean string.
    """
    text = " ".join(p.strip() for p in parts if p and p.strip())
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s+([,.;:!?،؛؟])", r"\1", text)
    return text
```

## What this cell does

PDF libraries often return text as many fragments:

```python
[
    "  Article 147 ",
    " The contract ",
    "  is the law   ",
    " of the parties . "
]
```

`clean_text()` joins and cleans those fragments.

## Line-by-line

```python
def clean_text(parts: list[str]) -> str:
```

- defines a function named `clean_text`
- expects a list of strings
- returns one string

---

```python
text = " ".join(p.strip() for p in parts if p and p.strip())
```

Break it down:

```python
if p and p.strip()
```

keeps only non-empty pieces.

```python
p.strip()
```

removes spaces at the beginning and end.

```python
" ".join(...)
```

joins the pieces with one space.

Example:

```python
parts = ["  Hello ", "", " world  "]
```

After this line:

```python
text == "Hello world"
```

---

```python
text = re.sub(r"\s+", " ", text).strip()
```

- `\s+` = one or more whitespace characters
- replace them with exactly one normal space
- `.strip()` removes outer whitespace

Example:

```python
"Hello     world\nagain"
```

becomes:

```text
Hello world again
```

---

```python
text = re.sub(r"\s+([,.;:!?،؛؟])", r"\1", text)
```

Removes spaces **before punctuation**.

Example:

```text
Before: "Hello , world !"
After:  "Hello, world!"
```

`([,.;:!?،؛؟])` captures the punctuation mark.

`r"\1"` means: put the captured punctuation back.

---

```python
return text
```

returns the cleaned result.

## Complete example

```python
parts = [" Article 147 ", " The contract   ", " is binding . "]
result = clean_text(parts)
print(result)
```

Output:

```text
Article 147 The contract is binding.
```

---

# Cell 4 — `smart_title()`

## Original code

```python
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
```

## Purpose

PDF headings may appear like:

```text
OBLIGATIONS OR PERSONAL RIGHTS
```

The function converts that into a more readable title:

```text
Obligations or Personal Rights
```

## Line-by-line

```python
text = re.sub(r"\s+", " ", text).strip(" :-")
```

- collapse repeated whitespace
- remove spaces, `:`, and `-` from both ends

Example:

```text
"  CONSENT:  "
```

becomes:

```text
"CONSENT"
```

---

```python
if not text:
    return text
```

If nothing remains, return an empty string immediately.

---

```python
if text.isupper():
```

Only transform the title if the whole heading is uppercase.

```python
"FIRST PART".isupper()     # True
"First Part".isupper()     # False
```

---

```python
small = {"of", "or", "and", "the", "a", "an", "in", "on", "to", "for", "by", "with"}
```

These are words that normally remain lowercase in an English title, except when they are the first word.

---

```python
words = text.lower().split()
```

Example:

```text
OBLIGATIONS OR PERSONAL RIGHTS
```

becomes:

```python
["obligations", "or", "personal", "rights"]
```

---

```python
return " ".join(
    w if i > 0 and w in small else w[:1].upper() + w[1:]
    for i, w in enumerate(words)
)
```

For every word:

- if it is a small word **and not first**, keep it lowercase
- otherwise capitalize its first character

Example:

```python
smart_title("OBLIGATIONS OR PERSONAL RIGHTS")
```

returns:

```text
Obligations or Personal Rights
```

---

```python
return text
```

If the heading was not all-uppercase, leave it essentially as it was after whitespace cleanup.

---

# Cell 5 — `scalar_pos()`

## Original code

```python
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
```

## Why is this needed?

Inside a PDF page, a line has a vertical coordinate `y`.

But this is ambiguous across pages:

```text
Page 1, y=500
Page 2, y=100
```

Numerically `100 < 500`, but page 2 obviously comes **after** page 1.

So the function combines page number + vertical position.

## Formula

```python
(page - 1) * 1000.0 + y
```

Examples:

```python
scalar_pos(1, 500)
# 500.0

scalar_pos(2, 100)
# 1100.0

scalar_pos(3, 50)
# 2050.0
```

Now normal numeric comparison works:

```text
500 < 1100 < 2050
```

So the script can sort lines as if the whole PDF were one long vertical page.

---

# Cell 6 — `Context` dataclass

## Original code

```python
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
```

## Meaning

A legal article does not exist alone. It may belong to:

```text
FIRST PART
    BOOK I
        CHAPTER II
            SECTION I
                Consent
                    Article 147
```

`Context` stores this hierarchy.

## Fields

```python
part_title: str | None = None
```

May contain something such as:

```text
Obligations or Personal Rights
```

or `None` if not yet known.

The same applies to:

```python
literal_book_title
chapter
section
topic
```

## Example

```python
ctx = Context(
    part_title="Obligations or Personal Rights",
    literal_book_title="Contracts",
    chapter="Formation of Contracts",
    section="Consent",
    topic="Elements of Contracts",
)
```

Then:

```python
print(ctx.chapter)
# Formation of Contracts
```

### Why both `part_title` and `literal_book_title`?

The source PDF appears to have both a `PART` hierarchy and a literal `BOOK` hierarchy. Later, when building output records, the code deliberately uses:

```python
ctx.part_title or ctx.literal_book_title
```

for the output field called `book`.

---

# Cell 7 — `Line` dataclass

## Original code

```python
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
```

## Coordinate idea

A PDF line is represented by a bounding box:

```text
(x0, y0) ---------------- (x1, y0)
    |                          |
    |          text            |
    |                          |
(x0, y1) ---------------- (x1, y1)
```

Fields:

```python
page
```

physical page number.

```python
x0, x1
```

left and right horizontal coordinates.

```python
y0, y1
```

top and bottom vertical coordinates.

```python
text
```

actual extracted text.

```python
col
```

column/language classification:

```python
"en"
```

or

```python
"ar"
```

## `@property`

```python
@property
def spos(self) -> float:
```

`@property` lets you write:

```python
line.spos
```

instead of:

```python
line.spos()
```

## Example

```python
line = Line(
    page=2,
    x0=50,
    x1=250,
    y0=120,
    y1=140,
    text="Article 147",
    col="en",
)

print(line.spos)
```

Calculation:

```python
(2 - 1) * 1000 + 120
```

Result:

```text
1120.0
```

---

# Cell 8 — `extract_word_lines()`

## Original code

```python
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
```

## Purpose

This is one of the core PDF-reading functions.

It converts PyMuPDF word tuples into cleaner `Line` objects and decides whether each line belongs to the English or Arabic side.

---

## Step 1 — output list

```python
out: list[Line] = []
```

Start with an empty list.

Eventually it may look like:

```python
[
    Line(page=1, ..., text="Article 1", col="en"),
    Line(page=1, ..., text="مادة ١", col="ar"),
    ...
]
```

---

## Step 2 — visit every PDF page

```python
for page_no, page in enumerate(doc, start=1):
```

If `doc` contains three pages:

```text
page_no = 1, page = first page
page_no = 2, page = second page
page_no = 3, page = third page
```

`start=1` is important because human PDF pages here are stored as 1-based physical page numbers.

---

## Step 3 — calculate page middle

```python
mid = page.rect.width / 2
```

Suppose page width is `600` PDF points:

```python
mid = 300
```

The parser expects roughly:

```text
0 ---------------- 300 ---------------- 600
|      ENGLISH      |       ARABIC       |
```

---

## Step 4 — prepare groups

```python
groups: dict[tuple[int, int], list[tuple]] = {}
```

PyMuPDF returns every word separately.

The script groups words using:

```python
(block_no, line_no)
```

so all words belonging to the same detected PDF line can be reconstructed.

---

## Step 5 — get every word

```python
for word in page.get_text("words"):
```

A PyMuPDF word tuple has this structure:

```python
(
    x0,
    y0,
    x1,
    y1,
    text,
    block_no,
    line_no,
    word_no,
)
```

Simplified example:

```python
(50, 100, 90, 115, "Article", 1, 0, 0)
(95, 100, 115, 115, "147",     1, 0, 1)
```

Both belong to:

```python
block_no = 1
line_no = 0
```

---

## Step 6 — group words by PDF line

```python
groups.setdefault((word[5], word[6]), []).append(word)
```

`word[5]` is `block_no`.

`word[6]` is `line_no`.

`setdefault()` means roughly:

```python
key = (word[5], word[6])

if key not in groups:
    groups[key] = []

groups[key].append(word)
```

After grouping:

```python
groups[(1, 0)]
```

might contain:

```python
[
    (..., "Article", ..., word_no=0),
    (..., "147",     ..., word_no=1),
]
```

---

## Step 7 — process each line group

```python
for words in groups.values():
```

Now `words` is a list containing the words of one logical PDF line.

---

## Step 8 — restore word order

```python
words.sort(key=lambda w: w[7])
```

`w[7]` is `word_no`.

Example:

```python
[(..., "147", ..., 1), (..., "Article", ..., 0)]
```

becomes:

```python
[(..., "Article", ..., 0), (..., "147", ..., 1)]
```

---

## Step 9 — combine word text

```python
text = clean_text([w[4] for w in words])
```

`w[4]` is the actual text.

Example:

```python
[w[4] for w in words]
```

returns:

```python
["Article", "147"]
```

Then:

```python
clean_text(["Article", "147"])
```

returns:

```text
Article 147
```

---

## Step 10 — skip empty lines

```python
if not text:
    continue
```

`continue` means:

> stop processing this current group and move to the next group.

---

## Step 11 — calculate the line bounding box

```python
x0 = min(w[0] for w in words)
x1 = max(w[2] for w in words)
y0 = min(w[1] for w in words)
y1 = max(w[3] for w in words)
```

If two words have boxes:

```text
Article: x=50 to 90
147:     x=95 to 115
```

then the complete line is approximately:

```text
x0 = 50
x1 = 115
```

The same idea applies vertically to `y0` and `y1`.

---

## Step 12 — count Arabic characters

```python
ar_count = sum(1 for c in text if "\u0600" <= c <= "\u06FF")
```

Example:

```python
text = "مادة 147"
```

The Arabic letters contribute to `ar_count`.

---

## Step 13 — count English letters

```python
en_count = sum(1 for c in text if c.isascii() and c.isalpha())
```

A character must be:

- ASCII
- alphabetic

Example:

```python
text = "Article 147"
```

`Article` contributes seven English letters.

---

## Step 14 — classify left-side English

```python
if x1 < mid + 8 and en_count >= ar_count:
    col = "en"
```

Meaning:

- the line ends around the left half of the page
- English characters are at least as common as Arabic characters

Then classify it as English.

Why `mid + 8` instead of exactly `mid`?

Because PDF coordinates are not always perfectly aligned. The extra `8` points provide a small tolerance around the page center.

---

## Step 15 — classify right-side Arabic

```python
elif x0 > mid - 8 and ar_count > 0:
    col = "ar"
```

Meaning:

- the line begins around the right half
- it has at least one Arabic character

Then classify it as Arabic.

---

## Step 16 — fallback based on character count

```python
else:
    col = "ar" if ar_count > en_count else "en"
```

If geometry is ambiguous:

```text
more Arabic letters -> "ar"
otherwise           -> "en"
```

---

## Step 17 — create a `Line`

```python
out.append(Line(page_no, x0, x1, y0, y1, text, col))
```

Example object:

```python
Line(
    page=7,
    x0=42.5,
    x1=210.3,
    y0=180.2,
    y1=194.8,
    text="Article 147",
    col="en",
)
```

---

## Step 18 — return all lines

```python
return out
```

The rest of the parser works with these `Line` objects instead of raw PyMuPDF tuples.

---

# Cell 9 — `extract_bold_english_lines()`

## Original code

```python
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
```

## Purpose

`extract_word_lines()` collects normal text.

This function has a different job:

> identify **bold English headings** because headings define the hierarchy/context of articles.

Examples of headings:

```text
FIRST PART
BOOK I
CHAPTER II
SECTION I
1. Elements of Contracts
Consent:
```

---

## Why use `page.get_text("dict")`?

```python
data = page.get_text("dict")
```

`"words"` gives convenient word positions.

`"dict"` gives richer formatting information including:

- blocks
- lines
- spans
- font names
- font flags
- bounding boxes

The script needs formatting because it wants to detect **bold text**.

---

## Nested PDF structure

```python
for block in data.get("blocks", []):
    for line in block.get("lines", []):
        spans = line.get("spans", [])
```

Conceptually:

```text
page
 └── block
      └── line
           ├── span 1
           └── span 2
```

A span is a run of characters with similar formatting.

Example:

```python
span = {
    "text": "CHAPTER I",
    "font": "Times-Bold",
    "bbox": [50, 100, 130, 118],
    "flags": 16,
}
```

---

## Skip lines with no spans

```python
if not spans:
    continue
```

No spans means nothing useful to inspect.

---

## Reconstruct the text

```python
text = clean_text([s.get("text", "") for s in spans])
```

Example spans:

```python
[
    {"text": "CHAPTER"},
    {"text": " I"},
]
```

become:

```text
CHAPTER I
```

---

## Require Latin text

```python
if not text or not LATIN_RE.search(text):
    continue
```

This ignores:

- blank lines
- Arabic-only bold headings

because this context builder intentionally uses the English side.

---

## Compute complete bounding box

```python
x0 = min(s["bbox"][0] for s in spans)
y0 = min(s["bbox"][1] for s in spans)
x1 = max(s["bbox"][2] for s in spans)
y1 = max(s["bbox"][3] for s in spans)
```

Same concept as in the previous function: combine all span boxes into one line box.

---

## Ignore the right half

```python
if x0 >= mid:
    continue
```

If the line begins at or after the page midpoint, it is not treated as an English-column heading.

---

## Count all characters

```python
total_chars = sum(max(1, len(s.get("text", ""))) for s in spans)
```

Why `max(1, ...)`?

Even an empty span is counted as at least `1`, which prevents a zero-sized span from creating odd weighting/division behavior.

Example:

```python
spans = [
    {"text": "CHAPTER"},  # 7 chars
    {"text": " I"},      # 2 chars
]
```

`total_chars` is approximately `9`.

---

## Count bold characters

```python
bold_chars = sum(
    max(1, len(s.get("text", "")))
    for s in spans
    if "Bold" in s.get("font", "") or (s.get("flags", 0) & 16)
)
```

A span counts as bold if either:

```python
"Bold" in s.get("font", "")
```

For example:

```text
TimesNewRoman-Bold
```

or:

```python
s.get("flags", 0) & 16
```

The bitwise `&` checks whether the bold-related flag bit is present.

Simple bitwise example:

```python
flags = 20       # binary contains several bits
bool(flags & 16) # True if the 16 bit is present
```

---

## Require at least 50% bold text

```python
if bold_chars / total_chars < 0.5:
    continue
```

Example:

```text
total_chars = 20
bold_chars  = 16
16 / 20 = 0.8
```

Keep it.

But:

```text
total_chars = 20
bold_chars  = 4
4 / 20 = 0.2
```

Skip it.

---

## Store heading as a `Line`

```python
out.append(Line(page_no, x0, x1, y0, y1, text, "en"))
```

All retained heading lines are explicitly marked `"en"`.

---

# Cell 10 — `build_context_timeline()`

## Original code

```python
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
```

## Core idea

Imagine the parser sees these headings in this order:

```text
FIRST PART
OBLIGATIONS OR PERSONAL RIGHTS
BOOK I
CONTRACTS
CHAPTER I
FORMATION OF CONTRACTS
SECTION I
CONSENT
Article 147
```

`FIRST PART` itself does **not** contain the real title.

The **next bold line** contains the value:

```text
OBLIGATIONS OR PERSONAL RIGHTS
```

That is why this function uses a variable named `pending`.

---

## Initial state

```python
ctx = Context()
```

Equivalent to:

```python
Context(
    part_title=None,
    literal_book_title=None,
    chapter=None,
    section=None,
    topic=None,
)
```

---

```python
pending: str | None = None
```

`pending` means:

> “I have just seen a structural label, and I am waiting for the next heading to tell me its title.”

Example:

```text
Read "CHAPTER II"
pending = "chapter"

Read "Effects of Contracts"
ctx.chapter = "Effects of Contracts"
pending = None
```

---

```python
timeline: list[tuple[float, Context]] = []
```

Stores snapshots such as:

```python
[
    (1200.5, Context(part_title="Obligations or Personal Rights", ...)),
    (1500.2, Context(chapter="Formation of Contracts", ...)),
]
```

Each tuple means:

```text
At document position X, the active legal context became Y.
```

---

```python
heading_positions: list[float] = []
```

Stores only heading positions.

This will later help determine where article text should stop.

---

## Nested `update()` function

```python
def update(pos: float):
    timeline.append((pos, copy.deepcopy(ctx)))
    heading_positions.append(pos)
```

Whenever context changes, save:

1. position
2. a **deep copy** of current context
3. heading position

Why deep copy?

Without it, every timeline entry could point to the same mutable `ctx` object.

Then changing `ctx.chapter` later could accidentally make old entries look as if they had the new chapter too.

---

## Sort headings into reading order

```python
for line in sorted(bold_lines, key=lambda x: (x.page, x.y0, x.x0)):
```

Sort priority:

1. page
2. vertical location
3. horizontal location

Example:

```python
key=lambda x: (x.page, x.y0, x.x0)
```

may generate keys such as:

```python
(5, 100.0, 50.0)
(5, 180.0, 50.0)
(6,  70.0, 50.0)
```

---

## Clean heading text and get global position

```python
text = line.text.strip()
pos = line.spos
```

Example:

```text
text = "CHAPTER II"
pos  = 8175.4
```

---

## Recognize `FIRST PART`, etc.

```python
if re.fullmatch(r"(?:FIRST|SECOND|THIRD|FOURTH|FIFTH|SIXTH)\s+PART", text, re.I):
```

This matches:

```text
FIRST PART
SECOND PART
THIRD PART
...
SIXTH PART
```

`re.I` means case-insensitive.

`(?:...)` is a non-capturing group.

`\s+` means one or more whitespace characters.

`fullmatch()` means the **whole string** must match.

Then:

```python
pending = "part_title"
```

means the next appropriate bold line will become `ctx.part_title`.

---

## Recognize `BOOK I`, `BOOK II`, ...

```python
if re.fullmatch(r"BOOK\s+[IVXLC]+", text, re.I):
```

`[IVXLC]+` matches Roman-numeral characters.

Examples:

```text
BOOK I
BOOK IV
BOOK XII
```

Then:

```python
pending = "literal_book_title"
```

---

## Recognize chapter

```python
if re.fullmatch(r"CHAPTER\s+[IVXLC]+", text, re.I):
    pending = "chapter"
```

Example:

```text
CHAPTER III
```

---

## Recognize section

```python
if re.fullmatch(r"SECTION\s+[IVXLC]+", text, re.I):
    pending = "section"
```

Example:

```text
SECTION II
```

---

## Why `update(pos)` even after structural marker?

Example:

```python
pending = "chapter"
update(pos)
continue
```

The marker itself is a heading position, so it matters as a boundary even before its title is assigned.

---

## Handle the title after a marker

```python
if pending:
```

Suppose previous line was:

```text
CHAPTER I
```

Then:

```python
pending == "chapter"
```

Now current line might be:

```text
FORMATION OF CONTRACTS
```

---

```python
value = smart_title(text)
```

Converts:

```text
FORMATION OF CONTRACTS
```

into:

```text
Formation of Contracts
```

---

```python
setattr(ctx, pending, value)
```

This is dynamic attribute assignment.

If:

```python
pending = "chapter"
value = "Formation of Contracts"
```

then:

```python
setattr(ctx, "chapter", "Formation of Contracts")
```

is equivalent to:

```python
ctx.chapter = "Formation of Contracts"
```

---

## Reset child context when parent changes

### New Part

```python
if pending == "part_title":
    ctx.literal_book_title = ctx.chapter = ctx.section = ctx.topic = None
```

Why?

A new part should not inherit the previous part's book/chapter/section/topic.

---

### New Book

```python
elif pending == "literal_book_title":
    ctx.chapter = ctx.section = ctx.topic = None
```

A new book resets everything below book level.

---

### New Chapter

```python
elif pending == "chapter":
    ctx.section = ctx.topic = None
```

A new chapter resets its old section/topic.

---

### New Section

```python
elif pending == "section":
    ctx.topic = None
```

A new section resets only the local topic.

This is a hierarchy:

```text
Part
 └── Book
      └── Chapter
           └── Section
                └── Topic
```

---

## Clear pending state

```python
pending = None
update(pos)
continue
```

Now the title has been consumed.

---

## Recognize numbered topic headings

```python
m = re.match(r"^\s*\d+\.\s*(.+)$", text)
```

Matches:

```text
1. Elements of Contracts
2. The Effects of a Contract
```

Parts:

```text
^       start
\s*     optional spaces
\d+     one or more digits
\.      literal period
\s*     optional spaces
(.+)    capture the remaining title
$       end
```

For:

```text
1. Elements of Contracts
```

`m.group(1)` is:

```text
Elements of Contracts
```

Then:

```python
ctx.topic = smart_title(m.group(1))
```

---

## Treat other short bold lines as topics

```python
if len(text) <= 100 and not re.match(r"^Article\s+\d+", text, re.I):
```

If a bold line:

- is at most 100 characters
- is **not** an `Article 123` line

then the script considers it a local topic/subtopic.

Example:

```text
Consent:
```

Then:

```python
ctx.topic = smart_title(text.rstrip(":"))
```

`rstrip(":")` changes:

```text
Consent:
```

to:

```text
Consent
```

---

## Return values

```python
return timeline, sorted(set(heading_positions))
```

`set(...)` removes duplicate positions.

`sorted(...)` restores numeric order.

So the function returns **two things**:

```python
timeline
```

and

```python
heading_positions
```

Usage:

```python
timeline, heading_positions = build_context_timeline(bold_lines)
```

---

# Cell 11 — `context_at()`

## Original code

```python
def context_at(timeline: list[tuple[float, Context]], spos: float) -> Context:
    """
    Find the most recent context before a given
    document position.
    """
    positions = [p for p, _ in timeline]
    i = bisect.bisect_right(positions, spos) - 1
    return copy.deepcopy(timeline[i][1]) if i >= 0 else Context()
```

## Goal

Question:

> At Article 147's position, what Part/Book/Chapter/Section/Topic is currently active?

Imagine:

```python
positions = [100, 250, 500, 900]
```

and Article 147 is at:

```python
spos = 620
```

The latest heading before `620` is at `500`.

---

## Extract timeline positions

```python
positions = [p for p, _ in timeline]
```

If:

```python
timeline = [
    (100, ctx1),
    (250, ctx2),
    (500, ctx3),
]
```

then:

```python
positions == [100, 250, 500]
```

The underscore `_` means:

> I intentionally do not need the second tuple item here.

---

## Binary-search for latest context

```python
i = bisect.bisect_right(positions, spos) - 1
```

Example:

```python
positions = [100, 250, 500, 900]
spos = 620
```

`bisect_right(...)` returns `3` because `620` would go before `900`.

Then:

```python
i = 3 - 1
# 2
```

Index `2` is position `500`, the latest heading before Article 147.

---

## Return copied context or empty context

```python
return copy.deepcopy(timeline[i][1]) if i >= 0 else Context()
```

This is a conditional expression.

Expanded version:

```python
if i >= 0:
    return copy.deepcopy(timeline[i][1])
else:
    return Context()
```

If the article appears before any known heading, it gets a blank `Context()`.

---

# Cell 12 — `find_articles()`

## Original code

```python
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
```

## Purpose

Search through all extracted lines and identify lines beginning with:

```text
Article 1
Article 2
Article 147
...
```

---

## Start list

```python
articles = []
```

---

## Visit every extracted line

```python
for line in lines:
```

---

## Only inspect English lines

```python
if line.col != "en":
    continue
```

The canonical article number is extracted from the English label.

---

## Match article label

```python
m = re.match(r"^Article\s+(\d+)\b", line.text, re.I)
```

Matches:

```text
Article 147
ARTICLE 147
Article     147 The contract ...
```

Pattern explanation:

```text
^          beginning of string
Article    literal word
\s+        one or more spaces
(\d+)      capture one or more digits
\b         word boundary
```

For:

```text
Article 147 The contract...
```

`m.group(1)` is:

```text
147
```

---

## Skip non-articles

```python
if not m:
    continue
```

---

## Convert number to integer

```python
n = int(m.group(1))
```

Converts:

```python
"147"
```

into:

```python
147
```

---

## Store article metadata

```python
articles.append({
    "number": n,
    "page": line.page,
    "start": line.spos,
    "context": context_at(timeline, line.spos),
})
```

Example:

```python
{
    "number": 147,
    "page": 25,
    "start": 24320.4,
    "context": Context(
        part_title="Obligations or Personal Rights",
        chapter="Contracts",
        section="Consent",
        topic="Elements of Contracts",
    ),
}
```

---

## Sort by document order

```python
articles.sort(key=lambda a: a["start"])
```

This guarantees Article records follow their actual PDF position, regardless of the order in which extraction happened.

---

# Cell 13 — `find_repealed_ranges()`

## Original code

```python
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
```

## Purpose

Some PDFs may not print every repealed article separately. Instead they may say:

```text
Articles 50-55 have been repealed
```

The parser captures the range:

```python
50, 55
```

---

## Declared return type

```python
list[tuple[int, int, int, float]]
```

Each tuple contains:

```python
(
    start_article,   # int
    end_article,     # int
    page,            # int
    document_pos,    # float
)
```

Example:

```python
(50, 55, 18, 17420.5)
```

---

## First regex

```python
re.compile(
    r"Articles?\s+(\d+)\s*[-–—]\s*(\d+)\s+have\s+been\s+repealed",
    re.I,
)
```

Matches both singular/plural prefix because:

```text
Articles?
```

means:

```text
Article
Articles
```

`[-–—]` accepts three kinds of dash:

```text
-   hyphen
–   en dash
—   em dash
```

Matches examples such as:

```text
Articles 50-55 have been repealed
Articles 50–55 have been repealed
```

---

## Second regex

```python
re.compile(r"Articles?\s+(\d+)\s*[-–—]\s*(\d+)\s+repealed", re.I)
```

Also accepts shorter wording:

```text
Articles 50-55 repealed
```

---

## Test every line against every pattern

```python
for line in lines:
    for pat in patterns:
        m = pat.search(line.text)
```

Unlike `re.match()`, `search()` allows the phrase to appear **anywhere** inside the line.

Example:

```text
Note: Articles 50-55 have been repealed by law...
```

can still match.

---

## Store match

```python
ranges.append((int(m.group(1)), int(m.group(2)), line.page, line.spos))
```

For:

```text
Articles 50-55 have been repealed
```

this adds approximately:

```python
(50, 55, 20, 19123.8)
```

---

## De-duplicate

```python
dedup = {}
```

Use a dictionary keyed by:

```python
(start, end)
```

Then:

```python
for start, end, page, pos in ranges:
    dedup[(start, end)] = (start, end, page, pos)
```

If `(50, 55)` was detected twice, only one final dictionary entry exists for that key.

---

```python
return list(dedup.values())
```

Convert dictionary values back into a list.

---

# Cell 14 — Repealed check + label cleaners

This logical cell contains three small helper functions.

---

## 14.1 `is_repealed()`

```python
def is_repealed(article_number: int, ranges) -> bool:
    return any(start <= article_number <= end for start, end, _, _ in ranges)
```

### Meaning

Check whether an article number falls inside **any** repealed range.

Example:

```python
ranges = [
    (50, 55, 10, 9000.0),
    (100, 105, 20, 19000.0),
]
```

Then:

```python
is_repealed(52, ranges)
# True

is_repealed(99, ranges)
# False
```

### Tuple unpacking

```python
for start, end, _, _ in ranges
```

The two `_` values mean page and position are intentionally ignored here.

### `any()`

```python
any(...)
```

returns `True` as soon as one condition is true.

---

## 14.2 `strip_english_article_label()`

```python
def strip_english_article_label(text: str, number: int) -> str:
    return re.sub(rf"^\s*Article\s+{number}\b\s*", "", text, flags=re.I).strip()
```

### Goal

Remove only the article label, keeping article content.

Example:

```python
text = "Article 147 The contract makes the law of the parties."
```

Result:

```text
The contract makes the law of the parties.
```

### Why `rf"..."`?

It is both:

- raw string `r`
- f-string `f`

So this:

```python
number = 147
rf"Article\s+{number}"
```

becomes regex text equivalent to:

```text
Article\s+147
```

---

## 14.3 `strip_arabic_article_label()`

```python
def strip_arabic_article_label(text: str) -> str:
    text = text.strip()
    if ARABIC_DIGIT_ONLY_RE.fullmatch(text):
        return ""
    text = re.sub(r"^[()\s]*مادة[()\s٠-٩0-9]*", "", text).strip()
    if not text or ARABIC_DIGIT_ONLY_RE.fullmatch(text):
        return ""
    return text
```

### Step 1

```python
text = text.strip()
```

Remove outer spaces.

---

### Step 2

```python
if ARABIC_DIGIT_ONLY_RE.fullmatch(text):
    return ""
```

If the line is only a number/label-like string, discard it.

Example:

```text
(١٤٧)
```

returns:

```python
""
```

---

### Step 3

```python
text = re.sub(r"^[()\s]*مادة[()\s٠-٩0-9]*", "", text).strip()
```

Removes an Arabic article prefix from the beginning.

Examples it is designed to remove include structures like:

```text
مادة 147
مادة (147)
( مادة ١٤٧ )
```

Simplified result:

```text
Before: مادة ١٤٧ العقد شريعة المتعاقدين
After:  العقد شريعة المتعاقدين
```

---

### Step 4

```python
if not text or ARABIC_DIGIT_ONLY_RE.fullmatch(text):
    return ""
```

After removing `مادة ...`, discard the line if nothing meaningful remains.

---

### Step 5

```python
return text
```

Otherwise return the real Arabic article text.

---

# Cell 15 — `extract_records()`

## Original code

```python
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
```

This is the **main orchestration function**. It connects all earlier helper functions.

---

## Step 1 — open the PDF

```python
doc = fitz.open(pdf_path)
```

If called like:

```python
records = extract_records(Path("civil_code.pdf"))
```

then PyMuPDF opens `civil_code.pdf`.

---

## Step 2 — extract normal lines

```python
lines = extract_word_lines(doc)
```

Result conceptually:

```python
[
    Line(..., text="FIRST PART", col="en"),
    Line(..., text="Article 1", col="en"),
    Line(..., text="مادة ١", col="ar"),
    ...
]
```

---

## Step 3 — extract bold English headings

```python
bold_lines = extract_bold_english_lines(doc)
```

Example:

```python
[
    Line(..., text="FIRST PART", col="en"),
    Line(..., text="OBLIGATIONS OR PERSONAL RIGHTS", col="en"),
    Line(..., text="CHAPTER I", col="en"),
    ...
]
```

---

## Step 4 — build legal hierarchy timeline

```python
timeline, heading_positions = build_context_timeline(bold_lines)
```

Now the parser knows:

> At document position 20,000, the current part/chapter/section/topic is X.

---

## Step 5 — find article starts

```python
articles = find_articles(lines, timeline)
```

Possible simplified result:

```python
[
    {
        "number": 147,
        "page": 35,
        "start": 34210.5,
        "context": Context(...),
    },
    {
        "number": 148,
        "page": 35,
        "start": 34510.2,
        "context": Context(...),
    },
]
```

---

## Step 6 — find repealed ranges

```python
repealed_ranges = find_repealed_ranges(lines)
```

Example:

```python
[(50, 55, 12, 11100.3)]
```

---

## Step 7 — guarantee sorted headings

```python
heading_positions = sorted(heading_positions)
```

`bisect` requires sorted data.

---

## Step 8 — create final record list

```python
records = []
```

Eventually this becomes:

```python
[
    {... Article 1 ...},
    {... Article 2 ...},
    ...
]
```

---

## Step 9 — loop through articles with index

```python
for i, article in enumerate(articles):
```

`enumerate()` gives both:

```python
i
```

and:

```python
article
```

Example:

```text
i=0 -> Article 147
i=1 -> Article 148
```

The index is needed to look at the **next** article.

---

## Step 10 — article start

```python
start = article["start"]
```

Example:

```python
start = 34210.5
```

---

## Step 11 — find next article boundary

```python
next_article = articles[i + 1]["start"] if i + 1 < len(articles) else float("inf")
```

Expanded:

```python
if i + 1 < len(articles):
    next_article = articles[i + 1]["start"]
else:
    next_article = float("inf")
```

For a normal article:

```text
Article 147 starts at 34210
Article 148 starts at 34510
```

So Article 147 should normally stop before `34510`.

For the final article, there is no next article, so the code uses:

```python
float("inf")
```

which represents positive infinity.

---

## Step 12 — find next heading after article start

```python
h_idx = bisect.bisect_right(heading_positions, start + 1e-6)
```

This finds the first heading position strictly after the article start.

### Why `1e-6`?

```python
1e-6 == 0.000001
```

It is a tiny positive offset used to avoid edge cases where a heading and article share effectively the same coordinate.

---

```python
next_heading = heading_positions[h_idx] if h_idx < len(heading_positions) else float("inf")
```

If a next heading exists, use it.

Otherwise, use infinity.

---

## Step 13 — article ends at whichever comes first

```python
end = min(next_article, next_heading)
```

Example A:

```text
Article 147 start = 1000
next article      = 1300
next heading      = 1500
```

Then:

```python
end = 1300
```

Example B:

```text
Article 147 start = 1000
next article      = 1600
next heading      = 1300
```

Then:

```python
end = 1300
```

This prevents a new section/topic heading from being accidentally included in the previous article body.

---

## Step 14 — select lines inside the article region

```python
selected = [line for line in lines if start - 4 <= line.spos < end - 0.5]
```

Normally we might expect:

```python
start <= line.spos < end
```

But the code deliberately uses tolerances.

### `start - 4`

Comment from the source:

```text
Arabic article labels are sometimes a couple of points above the English label.
```

So the parser starts four coordinate points earlier to catch Arabic text that visually belongs to the article.

### `end - 0.5`

Stops slightly before the boundary to reduce accidental inclusion of the next heading/article.

---

## Step 15 — select English article lines

```python
english_lines = sorted(
    [l for l in selected if l.col == "en" and LATIN_RE.search(l.text)],
    key=lambda l: (l.page, round(l.y0, 1), l.x0),
)
```

### Filter

```python
l.col == "en"
```

must be classified as English.

```python
LATIN_RE.search(l.text)
```

must actually contain a Latin letter.

This helps reject number-only fragments.

### Sort order

```python
(l.page, round(l.y0, 1), l.x0)
```

Sort by:

1. page
2. visual row
3. left-to-right horizontal location

`round(l.y0, 1)` groups nearly identical vertical coordinates such as:

```text
100.01
100.04
```

into roughly the same visual row.

---

## Step 16 — select Arabic article lines

```python
arabic_lines = sorted(
    [
        l
        for l in selected
        if l.col == "ar"
        and (ARABIC_RE.search(l.text) or re.search(r"[٠-٩]", l.text))
    ],
    key=lambda l: (l.page, round(l.y0, 1), -l.x0),
)
```

### Filter

Must:

```python
l.col == "ar"
```

and contain either:

```python
ARABIC_RE.search(l.text)
```

Arabic characters,

or:

```python
re.search(r"[٠-٩]", l.text)
```

Arabic-Indic digits.

### Why `-l.x0`?

Arabic is read right-to-left.

Suppose fragments on the same visual row have:

```text
right fragment x0 = 500
left fragment  x0 = 350
```

Normal ascending `x0` would produce:

```text
350 then 500
```

But right-to-left order needs:

```text
500 then 350
```

Negating gives:

```text
-500 < -350
```

so normal ascending sort now produces the rightmost fragment first.

---

## Step 17 — build English text pieces

```python
en_parts = []
```

---

```python
for line in english_lines:
```

process each English line in reading order.

---

```python
text = strip_english_article_label(line.text, article["number"])
```

Example:

```text
Article 147 The contract is binding...
```

becomes:

```text
The contract is binding...
```

---

```python
if text and not re.match(r"^Article\s+\d+\b", text, re.I):
    en_parts.append(text)
```

Only append if:

- text is non-empty
- it is not another `Article N` label

This helps avoid leaking the next article label into the current article body.

---

## Step 18 — build Arabic text pieces

```python
ar_parts = []
```

---

```python
for line in arabic_lines:
    text = strip_arabic_article_label(line.text)
    if text:
        ar_parts.append(text)
```

Remove labels such as `مادة ١٤٧`, then retain only meaningful Arabic text.

---

## Step 19 — recover article context

```python
ctx: Context = article["context"]
```

This is a type annotation plus assignment.

The `ctx` object contains the hierarchy active at the article's start.

---

## Step 20 — create the final record

```python
records.append({
```

A Python dictionary is created for each article.

Let's explain every field.

### `article_number`

```python
"article_number": article["number"],
```

Example:

```json
"article_number": 147
```

---

### `book`

```python
"book": ctx.part_title or ctx.literal_book_title,
```

Python's `or` returns the first truthy value.

Example 1:

```python
ctx.part_title = "Obligations or Personal Rights"
ctx.literal_book_title = "Contracts"
```

Result:

```text
Obligations or Personal Rights
```

Example 2:

```python
ctx.part_title = None
ctx.literal_book_title = "Contracts"
```

Result:

```text
Contracts
```

The source comment explicitly explains that this mapping is intentional so `FIRST PART`'s title can populate the requested output `book` field.

---

### `chapter`

```python
"chapter": ctx.chapter,
```

The current chapter title, or `None`.

---

### `section`

```python
"section": ctx.section,
```

The current section title, or `None`.

---

### `topic`

```python
"topic": ctx.topic,
```

The most recent local topic/subtopic.

---

### `ar_text`

```python
"ar_text": clean_text(ar_parts),
```

All Arabic article fragments are joined and cleaned.

Example:

```python
ar_parts = [
    "العقد شريعة المتعاقدين،",
    "فلا يجوز نقضه...",
]
```

becomes one string.

---

### `text_en`

```python
"text_en": clean_text(en_parts),
```

All English fragments become one clean article body.

---

### `is_repealed`

```python
"is_repealed": is_repealed(article["number"], repealed_ranges),
```

Example:

```python
article["number"] = 52
repealed_ranges = [(50, 55, 10, 9000.0)]
```

Result:

```json
"is_repealed": true
```

---

### `source_page`

```python
"source_page": article["page"],
```

Stores the **physical PDF page**, using 1-based numbering.

---

### `citation`

```python
"citation": f"Egyptian Civil Code, Article {article['number']}",
```

For Article 147:

```text
Egyptian Civil Code, Article 147
```

---

## Step 21 — return all final records

```python
return records
```

Possible simplified return value:

```python
[
    {
        "article_number": 147,
        "book": "Obligations or Personal Rights",
        "chapter": "Formation of Contracts",
        "section": "Consent",
        "topic": "Elements of Contracts",
        "ar_text": "العقد شريعة المتعاقدين...",
        "text_en": "The contract makes the law of the parties...",
        "is_repealed": False,
        "source_page": 25,
        "citation": "Egyptian Civil Code, Article 147",
    }
]
```

---

# Full simple example: how one article travels through the code

Assume the PDF visually contains:

```text
LEFT / ENGLISH                         RIGHT / ARABIC
---------------------------------------------------------------
CHAPTER I
FORMATION OF CONTRACTS
SECTION I
CONSENT

Article 147                            مادة ١٤٧
The contract makes the law            العقد شريعة المتعاقدين
of the parties.                        ...

Article 148                            مادة ١٤٨
...
```

## Stage A — normal line extraction

`extract_word_lines()` may produce something like:

```python
[
    Line(page=10, y0=100, text="CHAPTER I", col="en", ...),
    Line(page=10, y0=120, text="FORMATION OF CONTRACTS", col="en", ...),
    Line(page=10, y0=150, text="SECTION I", col="en", ...),
    Line(page=10, y0=170, text="CONSENT", col="en", ...),
    Line(page=10, y0=220, text="Article 147", col="en", ...),
    Line(page=10, y0=220, text="مادة ١٤٧", col="ar", ...),
    Line(page=10, y0=240, text="The contract makes the law", col="en", ...),
    Line(page=10, y0=240, text="العقد شريعة المتعاقدين", col="ar", ...),
    Line(page=10, y0=300, text="Article 148", col="en", ...),
]
```

---

## Stage B — heading extraction

`extract_bold_english_lines()` keeps headings such as:

```python
[
    "CHAPTER I",
    "FORMATION OF CONTRACTS",
    "SECTION I",
    "CONSENT",
]
```

---

## Stage C — context timeline

`build_context_timeline()` interprets:

```text
CHAPTER I
```

as:

```python
pending = "chapter"
```

Then:

```text
FORMATION OF CONTRACTS
```

becomes:

```python
ctx.chapter = "Formation of Contracts"
```

Likewise:

```text
SECTION I
CONSENT
```

becomes:

```python
ctx.section = "Consent"
```

Depending on the exact source structure, later bold lines may also update `topic`.

---

## Stage D — find Article 147

`find_articles()` sees:

```text
Article 147
```

and creates:

```python
{
    "number": 147,
    "page": 10,
    "start": scalar_pos(10, 220),
    "context": context_at(...),
}
```

The scalar position is:

```python
(10 - 1) * 1000 + 220
# 9220
```

---

## Stage E — determine Article 147 boundaries

Suppose:

```python
Article 147 start = 9220
Article 148 start = 9300
next heading      = 9500
```

Then:

```python
end = min(9300, 9500)
# 9300
```

So the parser collects text between Article 147 and Article 148.

---

## Stage F — clean labels

English:

```python
strip_english_article_label("Article 147 The contract makes the law", 147)
```

returns:

```text
The contract makes the law
```

Arabic:

```python
strip_arabic_article_label("مادة ١٤٧ العقد شريعة المتعاقدين")
```

returns approximately:

```text
العقد شريعة المتعاقدين
```

---

## Stage G — final record

```python
{
    "article_number": 147,
    "book": "Obligations or Personal Rights",
    "chapter": "Formation of Contracts",
    "section": "Consent",
    "topic": "...",
    "ar_text": "العقد شريعة المتعاقدين ...",
    "text_en": "The contract makes the law of the parties ...",
    "is_repealed": False,
    "source_page": 10,
    "citation": "Egyptian Civil Code, Article 147",
}
```

---

# Important Python concepts used in this file

## 1. List comprehension

Example from the source:

```python
[w[4] for w in words]
```

Longer equivalent:

```python
result = []
for w in words:
    result.append(w[4])
```

---

## 2. Generator expression

```python
sum(1 for c in text if c.isascii() and c.isalpha())
```

Means:

> for every English letter, produce `1`, then add all the `1`s.

---

## 3. Lambda

```python
words.sort(key=lambda w: w[7])
```

Equivalent idea:

```python
def get_word_number(w):
    return w[7]

words.sort(key=get_word_number)
```

---

## 4. Conditional expression

```python
col = "ar" if ar_count > en_count else "en"
```

Equivalent:

```python
if ar_count > en_count:
    col = "ar"
else:
    col = "en"
```

---

## 5. Tuple unpacking

```python
for start, end, page, pos in ranges:
```

If one tuple is:

```python
(50, 55, 10, 9000.0)
```

Python automatically assigns:

```python
start = 50
end = 55
page = 10
pos = 9000.0
```

---

## 6. Type hints

```python
def clean_text(parts: list[str]) -> str:
```

Means:

- `parts` should be a list of strings
- the function should return a string

Python normally does **not** enforce this automatically at runtime. It is primarily documentation/tooling information.

---

## 7. `None`

```python
chapter: str | None = None
```

Means the value may be:

```python
"Formation of Contracts"
```

or:

```python
None
```

`None` means “no value / not known.”

---

## 8. `continue`

```python
if not text:
    continue
```

Means:

> skip the rest of this loop iteration and move to the next item.

---

## 9. `setattr()`

```python
setattr(ctx, pending, value)
```

Dynamic form of attribute assignment.

If:

```python
pending = "chapter"
value = "Contracts"
```

then:

```python
setattr(ctx, pending, value)
```

acts like:

```python
ctx.chapter = "Contracts"
```

---

## 10. `deepcopy()`

```python
copy.deepcopy(ctx)
```

Creates an independent snapshot of the current context.

This is important because the `ctx` object keeps changing as new headings are read.

---

## 11. `bisect_right()`

```python
bisect.bisect_right(sorted_values, target)
```

Efficiently finds where `target` would be inserted on the **right side of equal values**.

Example:

```python
values = [10, 20, 20, 40]
bisect.bisect_right(values, 20)
# 3
```

---

# Important regular expressions in plain English

| Regex | Plain meaning | Example match |
|---|---|---|
| `r"[\u0600-\u06FF]"` | contains an Arabic Unicode character | `القانون` |
| `r"[A-Za-z]"` | contains an English/Latin letter | `Article` |
| `r"^Article\s+(\d+)\b"` | begins with `Article` + number | `Article 147` |
| `r"BOOK\s+[IVXLC]+"` | `BOOK` + Roman numeral | `BOOK IV` |
| `r"CHAPTER\s+[IVXLC]+"` | `CHAPTER` + Roman numeral | `CHAPTER II` |
| `r"SECTION\s+[IVXLC]+"` | `SECTION` + Roman numeral | `SECTION III` |
| `r"^\s*\d+\.\s*(.+)$"` | numbered heading | `1. Elements of Contracts` |
| `r"[٠-٩]"` | contains an Arabic-Indic digit | `١٤٧` |

---

# What the script returns vs. what it does not do

## It **does**

- open a PDF
- extract PDF text and geometry
- classify English vs Arabic lines
- identify bold English headings
- build legal hierarchy context
- find article labels
- detect repealed ranges
- reconstruct English article text
- reconstruct Arabic article text
- return a list of dictionaries

## It **does not**, in the supplied file

There is no visible code such as:

```python
if __name__ == "__main__":
    ...
```

There is also no visible call such as:

```python
records = extract_records(Path("civil_code.pdf"))
```

and no visible JSON output such as:

```python
Path("output.json").write_text(json.dumps(records, ...))
```

So this file currently **defines the parser**, but another caller/script would need to invoke it to process a real PDF and persist results.

---

# Example of how the existing function could be called

The following is an **example usage**, not code that exists in the supplied file:

```python
from pathlib import Path

pdf_path = Path("egyptian_civil_code.pdf")
records = extract_records(pdf_path)

print(records[0])
```

Possible output shape:

```python
{
    "article_number": 1,
    "book": "...",
    "chapter": "...",
    "section": "...",
    "topic": "...",
    "ar_text": "...",
    "text_en": "...",
    "is_repealed": False,
    "source_page": 1,
    "citation": "Egyptian Civil Code, Article 1",
}
```

---

# Optional example: saving returned records as JSON

Again, this is **illustrative code**, not part of the supplied file:

```python
import json
from pathlib import Path

pdf_path = Path("egyptian_civil_code.pdf")
records = extract_records(pdf_path)

output_path = Path("civil_code.json")
output_path.write_text(
    json.dumps(records, ensure_ascii=False, indent=2),
    encoding="utf-8",
)
```

Why:

```python
ensure_ascii=False
```

keeps Arabic readable instead of converting it to Unicode escape sequences.

Why:

```python
indent=2
```

formats JSON nicely for humans.

---

# Short mental model for remembering the entire script

Think of the parser as five stages:

```text
1. READ
   PyMuPDF reads words, coordinates, fonts.

2. CLASSIFY
   Decide English vs Arabic and normal text vs bold heading.

3. UNDERSTAND STRUCTURE
   Track Part -> Book -> Chapter -> Section -> Topic.

4. CUT ARTICLES
   Article start -> next article or next heading.

5. BUILD RECORDS
   article number + hierarchy + Arabic + English + metadata.
```

A compact pseudocode version is:

```python
open PDF

normal_lines = extract all normal lines
heading_lines = extract bold English headings

context_history = build hierarchy from headings
article_starts = find all "Article N" lines
repealed_ranges = find all repealed article ranges

for each article:
    determine where it starts
    determine where it ends
    collect English text
    collect Arabic text
    remove labels
    attach hierarchy
    attach repeal status
    save dictionary

return all dictionaries
```

---

# Final summary of every logical cell

| Cell | Code | Main job |
|---:|---|---|
| 1 | Imports | Load Python/PDF utilities |
| 2 | Regex constants | Recognize Arabic, Latin, number-only labels |
| 3 | `clean_text()` | Join and normalize extracted fragments |
| 4 | `smart_title()` | Convert uppercase headings into readable titles |
| 5 | `scalar_pos()` | Convert page + Y coordinate into one global position |
| 6 | `Context` | Store Part/Book/Chapter/Section/Topic |
| 7 | `Line` | Store PDF line geometry, text, and language column |
| 8 | `extract_word_lines()` | Reconstruct lines and classify EN/AR |
| 9 | `extract_bold_english_lines()` | Detect bold English headings |
| 10 | `build_context_timeline()` | Build hierarchy history through the PDF |
| 11 | `context_at()` | Find active hierarchy at an article position |
| 12 | `find_articles()` | Find each `Article N` start |
| 13 | `find_repealed_ranges()` | Detect ranges marked repealed |
| 14 | Small helpers | Check repeal and remove article labels |
| 15 | `extract_records()` | Combine everything into final article dictionaries |

---

# Best order to study this code

If you are learning it rather than only using it, read the cells in this order:

```text
1. Context + Line
2. clean_text + smart_title
3. scalar_pos
4. extract_word_lines
5. extract_bold_english_lines
6. build_context_timeline
7. context_at
8. find_articles
9. find_repealed_ranges
10. label cleaners
11. extract_records
```

The hardest concepts are usually:

- PDF coordinates
- `bisect`
- regular expressions
- why `pending` is needed
- why context snapshots use `deepcopy`
- Arabic right-to-left ordering with `-l.x0`

Once those are clear, `extract_records()` becomes much easier to understand.
