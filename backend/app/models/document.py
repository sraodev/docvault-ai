from pydantic import BaseModel
from typing import Optional

class DocumentMetadata(BaseModel):
    id: str
    filename: str
    upload_date: str
    file_path: str
    summary: Optional[str] = None
    markdown_path: Optional[str] = None
    status: str = "processing" # processing, completed, failed
