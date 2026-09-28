from __future__ import annotations

import json
from pathlib import Path

from src.legal_chatbot.config import PROJECT_ROOT, load_params
from src.legal_chatbot.ingestion.civil_code_parser import extract_records
from src.legal_chatbot.schemas.article import ArticleRecord


def main() -> None:
    params = load_params()
    raw_pdf = PROJECT_ROOT / params["paths"]["raw_pdf"]
    output = PROJECT_ROOT / params["paths"]["articles_json"]

    records = extract_records(raw_pdf)

    if params["extraction"].get("validate_schema", True):
        records = [ArticleRecord.model_validate(r).model_dump() for r in records]

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            records,
            ensure_ascii=params["extraction"].get("ensure_ascii", False),
            indent=params["extraction"].get("indent", 2),
        ),
        encoding="utf-8",
    )

    print(f"Wrote {len(records)} articles to {output}")


if __name__ == "__main__":
    main()
