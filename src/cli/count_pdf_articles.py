import re

import pymupdf as fitz

from config.config import Config


def main() -> None:
    settings = Config()
    doc = fitz.open(settings.RAW_PDF)
    articles = []

    for page_number, page in enumerate(doc, start=1):
        text = page.get_text("text")

        for line in text.splitlines():
            line = line.strip()

            if re.fullmatch(r"A?rticle\s+\d+", line, re.I):
                number = int(re.search(r"\d+", line).group())
                articles.append((number, page_number, line))

    numbers = [number for number, _, _ in articles]

    print(f"PDF pages: {len(doc)}")
    print(f"Article headings found: {len(articles)}")
    print(f"Unique article numbers: {len(set(numbers))}")

    duplicates = {}

    for number, page, line in articles:
        duplicates.setdefault(number, []).append(page)

    duplicates = {
        number: pages
        for number, pages in duplicates.items()
        if len(pages) > 1
    }

    print(f"Duplicate article numbers: {duplicates}")


if __name__ == "__main__":
    main()