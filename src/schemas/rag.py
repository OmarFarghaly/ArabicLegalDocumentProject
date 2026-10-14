from pydantic import BaseModel
from typing import List, Optional


class Payload(BaseModel):
    article_number :int
    ar_text : str
    text_en : str
    book: Optional[str | None]
    chapter  : Optional[str | None]
    section : Optional[str | None]
    topic : Optional[str | None]
    is_repealed : bool
    source_page : int
    citation :str


class OutputResponse(BaseModel):
    outputs :List[Payload]