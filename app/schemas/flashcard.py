from pydantic import BaseModel
from typing import Optional

class FlashcardCreate(BaseModel):
    question: str
    answer: str

class FlashcardUpdate(BaseModel):
    question: Optional[str] = None
    answer: Optional[str] = None

class FlashcardResponse(BaseModel):
    id: str
    question: str
    answer: str
    user_id: str
    group_id: str
