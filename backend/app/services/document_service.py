"""
Document Service - Business logic for document operations.
Follows Single Responsibility Principle - handles document business logic only.
"""
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .interfaces import IDocumentService, IFileService, IAIService
from ..domain.entities import Document
from ..domain.value_objects import FileChecksum, FolderPath
from ..repositories.interfaces import IDocumentRepository
from ..core.config import UPLOAD_DIR
from ..core.logging_config import get_logger

logger = get_logger(__name__)

class DocumentService(IDocumentService):
    """
    Service for document business logic.
    Coordinates between repositories, file operations, and AI processing.
    Follows Single Responsibility Principle.
    """
    
    def __init__(
        self,
        document_repo: IDocumentRepository,
        file_service: IFileService,
        ai_service: IAIService
    ):
        """
        Initialize document service with dependencies.
        
        Args:
            document_repo: Document repository (dependency injection)
            file_service: File service (dependency injection)
            ai_service: AI service (dependency injection)
        """
        self._repo = document_repo
        self._file_service = file_service
        self._ai_service = ai_service
    
    async def upload_document(
        self,
        file_path: Path,
        filename: str,
        folder: Optional[FolderPath] = None,
        checksum: Optional[FileChecksum] = None
    ) -> Document:
        """
        Upload and process a document.
        
        Args:
            file_path: Path to uploaded file
            filename: Original filename
            folder: Optional folder path
            checksum: Optional pre-calculated checksum
        
        Returns:
            Created document entity
        """
        # Check for duplicates
        if checksum:
            duplicate = await self.check_duplicate(checksum)
            if duplicate:
                raise ValueError(f"Duplicate file: {filename} already exists as {duplicate.filename}")
        
        # Create document entity
        doc_id = str(uuid.uuid4())
        now = datetime.now()
        
        document = Document(
            id=doc_id,
            filename=filename,
            upload_date=now,
            modified_date=now,
            file_path=file_path,
            folder=folder,
            checksum=checksum,
            size=file_path.stat().st_size if file_path.exists() else None,
            status="processing",
            summary=None,
            markdown_path=None,
            upload_progress=0
        )
        
        # Save to repository
        document = await self._repo.create(document)
        
        return document
    
    async def get_document(self, doc_id: str) -> Optional[Document]:
        """Get a document by ID."""
        return await self._repo.get_by_id(doc_id)
    
    async def get_all_documents(self, folder: Optional[FolderPath] = None) -> List[Document]:
        """Get all documents."""
        return await self._repo.get_all(folder=folder)
    
    async def delete_document(self, doc_id: str) -> bool:
        """
        Delete a document.
        Also deletes associated files.
        """
        document = await self._repo.get_by_id(doc_id)
        if not document:
            return False
        
        # Delete files
        if document.file_path and Path(document.file_path).exists():
            self._file_service.delete_file(Path(document.file_path))
        
        if document.markdown_path and Path(document.markdown_path).exists():
            self._file_service.delete_file(Path(document.markdown_path))
        
        # Delete from repository
        return await self._repo.delete(doc_id)
    
    async def check_duplicate(self, checksum: FileChecksum) -> Optional[Document]:
        """Check if a document with this checksum exists."""
        return await self._repo.find_by_checksum(checksum)
    
    async def process_document(self, doc_id: str) -> Document:
        """
        Process a document with AI (extract text, generate summary/markdown).
        This is business logic, not data access.
        """
        document = await self._repo.get_by_id(doc_id)
        if not document:
            raise ValueError(f"Document {doc_id} not found")
        
        file_path = Path(document.file_path)
        
        try:
            # Extract text
            text_content = self._file_service.extract_text(file_path)
            
            # Generate summary and markdown
            summary = self._ai_service.generate_summary(text_content)
            markdown_content = self._ai_service.generate_markdown(text_content)
            
            # Save markdown
            md_filename = f"{doc_id}_processed.md"
            md_path = UPLOAD_DIR / md_filename
            self._file_service.save_markdown(markdown_content, md_path)
            
            # Update document
            document.mark_completed(summary, md_path)
            document = await self._repo.update(document)
            
            return document
        except Exception as e:
            document.mark_failed()
            await self._repo.update(document)
            raise

