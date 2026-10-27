from pydantic import BaseModel, Field, field_validator
from .llm import ChatMessage
import re 
class InputRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    chat_history: list[ChatMessage] = Field(
        default_factory=list,
        max_length=10,
    )

    @field_validator("question")
    @classmethod
    def question_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Question must not be blank")
        return value