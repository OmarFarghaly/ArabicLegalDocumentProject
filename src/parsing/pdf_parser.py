import re
import pymupdf

from parsing.arabic_utils import fix_arabic


class PDFParser:

    def __init__(self, pdf_path):
        self.pdf_path = pdf_path

    def parse(self):
        doc = pymupdf.open(self.pdf_path)

        articles = []

        for page_number, page in enumerate(doc, start=1):

            tables = page.find_tables()

            for table in tables.tables:

                rows = table.extract()

                for row in rows:

                    if not row:
                        continue

                    # Arabic-only content
                    if len(row) == 1:
                        arabic = fix_arabic(row[0] or "")

                        articles.append({
                            "page": page_number,
                            "english": "",
                            "arabic": arabic
                        })

                    # English + Arabic
                    elif len(row) >= 2:

                        english = (row[0] or "").strip()
                        arabic = fix_arabic(row[1] or "")

                        article_number = self._get_article_number(english)

                        if article_number is not None:

                            articles.append({
                                "article_number": article_number,
                                "page": page_number,
                                "english": english,
                                "arabic": arabic
                            })

        doc.close()

        return articles

    def _get_article_number(self, text):
        match = re.search(
            r"Article\s+(\d+)",
            text,
            re.IGNORECASE
        )

        if match:
            return int(match.group(1))

        return None
