from pydantic import BaseModel
from typing import Optional, List, Dict, Any

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
    modified_date: Optional[str] = None  # Last modified date (defaults to upload_date)
    tags: Optional[List[str]] = None  # Tags extracted from document content
    extracted_fields: Optional[Dict[str, Any]] = None  # Structured fields extracted by AI (e.g., invoice fields, resume fields)
    embedding: Optional[List[float]] = None  # Vector embedding for semantic search
