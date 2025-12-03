"""
Domain entities - Core business objects.
These represent the business concepts, not database models.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from .value_objects import FileChecksum, FilePath, FolderPath
from ..core.logging_config import get_logger

logger = get_logger(__name__)

@dataclass
class Document:
    """
    Document entity - represents a document in the domain.
    This is a pure domain object, independent of persistence.
    """
    id: str
    filename: str
    upload_date: datetime
    modified_date: Optional[datetime]
    file_path: FilePath
    folder: Optional[FolderPath]
    checksum: Optional[FileChecksum]
    size: Optional[int]
    status: str  # processing, completed, failed, uploading
    summary: Optional[str]
    markdown_path: Optional[FilePath]
    upload_progress: int = 0
    
    def is_completed(self) -> bool:
        """Check if document processing is completed."""
        return self.status == "completed"
    
    def is_processing(self) -> bool:
        """Check if document is being processed."""
        return self.status == "processing"
    
    def is_failed(self) -> bool:
        """Check if document processing failed."""
        return self.status == "failed"
    
    def mark_completed(self, summary: str, markdown_path: FilePath):
        """Mark document as completed with results."""
        self.status = "completed"
        self.summary = summary
        self.markdown_path = markdown_path
        self.modified_date = datetime.now()
    
    def mark_failed(self):
        """Mark document as failed."""
        self.status = "failed"
        self.modified_date = datetime.now()

@dataclass
class Folder:
    """
    Folder entity - represents a folder in the domain.
    """
    folder_path: FolderPath
    name: str
    parent_folder: Optional[FolderPath]
    created_date: datetime
    
    def is_root(self) -> bool:
        """Check if folder is root folder."""
        return self.parent_folder is None
    
    def get_depth(self) -> int:
        """Get folder depth in hierarchy."""
        if self.is_root():
            return 0
        return len(str(self.folder_path).split('/'))

