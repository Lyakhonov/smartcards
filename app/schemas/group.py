from datetime import datetime

from pydantic import BaseModel


class GroupResponse(BaseModel):
    id: str
    filename: str
    created_at: datetime
    flashcards_count: int

class FileUploadResponse(BaseModel):
    group_id: str
    filename: str
    message: str
