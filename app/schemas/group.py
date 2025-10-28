from pydantic import BaseModel
from datetime import datetime

class GroupResponse(BaseModel):
    id: str
    filename: str
    created_at: datetime

class FileUploadResponse(BaseModel):
    group_id: str
    filename: str
    message: str
