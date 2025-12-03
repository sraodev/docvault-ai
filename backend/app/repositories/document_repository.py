"""
Document Repository - Concrete implementation of document data access.
Maps between domain entities and database adapters.
"""
from typing import List, Optional
from datetime import datetime

from .interfaces import IDocumentRepository
from ..domain.entities import Document
from ..domain.value_objects import FileChecksum, FolderPath
from ..services.database.base import DatabaseInterface
from ..core.logging_config import get_logger

logger = get_logger(__name__)

class DocumentRepository(IDocumentRepository):
    """
    Repository for document data access.
    Maps domain entities to database operations.
    Follows Single Responsibility Principle - only handles data access.
    """
    
    def __init__(self, db_service: DatabaseInterface):
        """
        Initialize repository with database service.
        
        Args:
            db_service: Database adapter (dependency injection)
        """
        self._db = db_service
    
    def _to_entity(self, data: dict) -> Document:
        """Convert database record to domain entity."""
        return Document(
            id=data["id"],
            filename=data["filename"],
            upload_date=datetime.fromisoformat(data["upload_date"]),
            modified_date=datetime.fromisoformat(data["modified_date"]) if data.get("modified_date") else None,
            file_path=data["file_path"],
            folder=data.get("folder"),
            checksum=data.get("checksum"),
            size=data.get("size"),
            status=data.get("status", "processing"),
            summary=data.get("summary"),
            markdown_path=data.get("markdown_path"),
            upload_progress=data.get("upload_progress", 0)
        )
    
    def _to_dict(self, document: Document) -> dict:
        """Convert domain entity to database record."""
        return {
            "id": document.id,
            "filename": document.filename,
            "upload_date": document.upload_date.isoformat(),
            "modified_date": document.modified_date.isoformat() if document.modified_date else None,
            "file_path": str(document.file_path),
            "folder": str(document.folder) if document.folder else None,
            "checksum": str(document.checksum) if document.checksum else None,
            "size": document.size,
            "status": document.status,
            "summary": document.summary,
            "markdown_path": str(document.markdown_path) if document.markdown_path else None,
            "upload_progress": document.upload_progress
        }
    
    async def create(self, document: Document) -> Document:
        """Create a new document."""
        data = self._to_dict(document)
        result = await self._db.create_document(data)
        return self._to_entity(result)
    
    async def get_by_id(self, doc_id: str) -> Optional[Document]:
        """Get document by ID."""
        data = await self._db.get_document(doc_id)
        return self._to_entity(data) if data else None
    
    async def get_all(self, folder: Optional[FolderPath] = None) -> List[Document]:
        """Get all documents, optionally filtered by folder."""
        folder_str = str(folder) if folder else None
        data_list = await self._db.get_all_documents(folder=folder_str)
        return [self._to_entity(data) for data in data_list]
    
    async def update(self, document: Document) -> Document:
        """Update a document."""
        updates = {
            "status": document.status,
            "summary": document.summary,
            "markdown_path": str(document.markdown_path) if document.markdown_path else None,
            "modified_date": document.modified_date.isoformat() if document.modified_date else None,
            "upload_progress": document.upload_progress,
            "size": document.size
        }
        result = await self._db.update_document(document.id, updates)
        return self._to_entity(result) if result else document
    
    async def delete(self, doc_id: str) -> bool:
        """Delete a document."""
        return await self._db.delete_document(doc_id)
    
    async def find_by_checksum(self, checksum: FileChecksum) -> Optional[Document]:
        """Find document by checksum."""
        data = await self._db.find_document_by_checksum(str(checksum))
        return self._to_entity(data) if data else None
    
    async def get_by_folder(self, folder_path: FolderPath, include_subfolders: bool = False) -> List[Document]:
        """Get documents in a folder."""
        data_list = await self._db.get_documents_by_folder(str(folder_path), include_subfolders)
        return [self._to_entity(data) for data in data_list]

