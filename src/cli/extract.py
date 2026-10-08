from __future__ import annotations

import json
from pathlib import Path

from config.config import Config
from parsing.pdf_parser import extract_records
from schemas.extracted_record import ExtractedRecord


def main() -> None:
    settings = Config()

    raw_pdf = Path(settings.RAW_PDF)
    output = Path(settings.ARTICLES_JSON)

    records = extract_records(raw_pdf)

    if settings.VALIDATE_SCHEMA:
        records = [
            ExtractedRecord.model_validate(record).model_dump()
            for record in records
        ]

    output.parent.mkdir(parents=True, exist_ok=True)

    output.write_text(
        json.dumps(
            records,
            ensure_ascii=settings.ENSURE_ASCII,
            indent=settings.INDENT,
        ),
        encoding="utf-8",
    )

    print(f"Wrote {len(records)} articles to {output}")


if __name__ == "__main__":
    main()
    