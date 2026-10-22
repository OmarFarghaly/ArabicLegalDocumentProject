from pydantic import BaseModel, Field, field_validator
import re 
class InputRequest(BaseModel):
    question :str = Field()
        
    