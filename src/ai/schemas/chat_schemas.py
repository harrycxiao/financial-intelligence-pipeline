from pydantic import BaseModel
from typing import Literal

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    answer: str