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
    folder: Optional[str] = None  # Virtual folder/category for organization
    checksum: Optional[str] = None  # SHA-256 checksum for duplicate detection
    size: Optional[int] = None  # File size in bytes
