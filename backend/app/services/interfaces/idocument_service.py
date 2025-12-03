"""
Document Service Interface.

Defines the contract for document business logic operations.
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from pathlib import Path
from ...domain.entities import Document
from ...domain.value_objects import FileChecksum, FolderPath


class IDocumentService(ABC):
    """
    Interface for document business logic.
    
    Defines the contract for document operations including:
    - Upload and processing
    - Retrieval
    - Deletion
    - Duplicate detection
    """
    
    @abstractmethod
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
            file_path: Path to the uploaded file
            filename: Name of the file
            folder: Optional folder path for organization
            checksum: Optional file checksum for duplicate detection
            
        Returns:
            Document entity with metadata
        """
        pass
    
    @abstractmethod
    async def get_document(self, doc_id: str) -> Optional[Document]:
        """
        Get a document by ID.
        
        Args:
            doc_id: Document identifier
            
        Returns:
            Document entity if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def get_all_documents(self, folder: Optional[FolderPath] = None) -> List[Document]:
        """
        Get all documents, optionally filtered by folder.
        
        Args:
            folder: Optional folder path to filter documents
            
        Returns:
            List of Document entities
        """
        pass
    
    @abstractmethod
    async def delete_document(self, doc_id: str) -> bool:
        """
        Delete a document.
        
        Args:
            doc_id: Document identifier
            
        Returns:
            True if deleted successfully, False otherwise
        """
        pass
    
    @abstractmethod
    async def check_duplicate(self, checksum: FileChecksum) -> Optional[Document]:
        """
        Check if a document with this checksum already exists.
        
        Args:
            checksum: File checksum to check
            
        Returns:
            Existing Document if duplicate found, None otherwise
        """
        pass

