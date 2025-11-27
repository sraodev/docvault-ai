"""
Repository interfaces - Define contracts for data access.
Follows Interface Segregation Principle - specific interfaces for specific needs.
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from ..domain.entities import Document, Folder
from ..domain.value_objects import FileChecksum, FolderPath

class IDocumentRepository(ABC):
    """
    Interface for document data access.
    Business logic depends on this interface, not concrete implementations.
    """
    
    @abstractmethod
    async def create(self, document: Document) -> Document:
        """Create a new document."""
        pass
    
    @abstractmethod
    async def get_by_id(self, doc_id: str) -> Optional[Document]:
        """Get document by ID."""
        pass
    
    @abstractmethod
    async def get_all(self, folder: Optional[FolderPath] = None) -> List[Document]:
        """Get all documents, optionally filtered by folder."""
        pass
    
    @abstractmethod
    async def update(self, document: Document) -> Document:
        """Update a document."""
        pass
    
    @abstractmethod
    async def delete(self, doc_id: str) -> bool:
        """Delete a document."""
        pass
    
    @abstractmethod
    async def find_by_checksum(self, checksum: FileChecksum) -> Optional[Document]:
        """Find document by checksum."""
        pass
    
    @abstractmethod
    async def get_by_folder(self, folder_path: FolderPath, include_subfolders: bool = False) -> List[Document]:
        """Get documents in a folder."""
        pass

class IFolderRepository(ABC):
    """
    Interface for folder data access.
    """
    
    @abstractmethod
    async def create(self, folder: Folder) -> Folder:
        """Create a new folder."""
        pass
    
    @abstractmethod
    async def get_by_path(self, folder_path: FolderPath) -> Optional[Folder]:
        """Get folder by path."""
        pass
    
    @abstractmethod
    async def get_all(self) -> List[FolderPath]:
        """Get all folder paths."""
        pass
    
    @abstractmethod
    async def delete(self, folder_path: FolderPath) -> int:
        """Delete a folder and return count of deleted items."""
        pass
    
    @abstractmethod
    async def move(self, old_path: FolderPath, new_path: Optional[FolderPath]) -> int:
        """Move a folder to a new location."""
        pass

