from pathlib import Path
import json

from parsing.pdf_parser import PDFParser


project_root = Path(__file__).resolve().parent.parent

pdf_path = project_root / "data" / "1576751803.pdf"
output_path = project_root / "data" / "parsedData.json"


parser = PDFParser(pdf_path)

articles = parser.parse()


with open(output_path, "w", encoding="utf-8") as file:
    json.dump(
        articles,
        file,
        ensure_ascii=False,
        indent=2
    )

print(f"Created: {output_path}")