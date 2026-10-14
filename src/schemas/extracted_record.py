from pydantic import BaseModel, ConfigDict


class ExtractedRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    article_number: int
    book: str | None = None
    chapter: str | None = None
    section: str | None = None
    topic: str | None = None
    ar_text: str
    text_en: str
    is_repealed: bool
    source_page: int
    citation: str
