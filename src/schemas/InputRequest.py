from pydantic import BaseModel, Field

class InputRequest(BaseModel):
    question :str = Field()
    