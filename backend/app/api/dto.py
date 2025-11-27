"""
Data Transfer Objects (DTOs) for API layer.
Separates API contracts from domain entities.
"""
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime

class DocumentDTO(BaseModel):
    """Document DTO for API responses."""
    id: str
    filename: str
    upload_date: str
    modified_date: Optional[str]
    file_path: str
    folder: Optional[str]
    checksum: Optional[str]
    size: Optional[int]
    status: str
    summary: Optional[str]
    markdown_path: Optional[str]
    upload_progress: int = 0
    
    class Config:
        from_attributes = True

class FolderDTO(BaseModel):
    """Folder DTO for API responses."""
    folder_path: str
    name: str
    parent_folder: Optional[str]
    created_date: str
    
    class Config:
        from_attributes = True

class BulkUploadResponseDTO(BaseModel):
    """Response DTO for bulk upload."""
    total_files: int
    successful: int
    failed: int
    duplicates: int
    document_ids: List[str]
    errors: List[Dict[str, str]]

class ErrorResponseDTO(BaseModel):
    """Error response DTO."""
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None

