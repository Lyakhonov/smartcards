from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class GroupResponse(BaseModel):
    id: str
    filename: str
    created_at: datetime
    flashcards_count: int
    file_url: Optional[str] = None


class FileUploadResponse(BaseModel):
    group_id: str
    filename: str
    message: str
