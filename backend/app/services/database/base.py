"""
Abstract base class for database adapters.
All database implementations must inherit from this class.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from ...core.logging_config import get_logger

logger = get_logger(__name__)

class DatabaseInterface(ABC):
    """
    Abstract interface for database operations.
    All database adapters must implement these methods.
    This allows plug-and-play database support without changing business logic.
    """
    
    # Document operations
    @abstractmethod
    async def create_document(self, doc_data: Dict) -> Dict:
        """Create a new document record."""
        pass
    
    @abstractmethod
    async def get_document(self, doc_id: str) -> Optional[Dict]:
        """Get a document by ID."""
        pass
    
    @abstractmethod
    async def get_all_documents(self, folder: Optional[str] = None) -> List[Dict]:
        """Get all documents, optionally filtered by folder."""
        pass
    
    @abstractmethod
    async def update_document(self, doc_id: str, updates: Dict) -> Optional[Dict]:
        """Update a document."""
        pass
    
    @abstractmethod
    async def delete_document(self, doc_id: str) -> bool:
        """Delete a document."""
        pass
    
    @abstractmethod
    async def find_document_by_checksum(self, checksum: str) -> Optional[Dict]:
        """Find a document by checksum."""
        pass
    
    @abstractmethod
    async def get_documents_by_folder(self, folder_path: str, include_subfolders: bool = False) -> List[Dict]:
        """Get documents in a folder, optionally including subfolders."""
        pass
    
    # Folder operations
    @abstractmethod
    async def create_folder(self, folder_data: Dict) -> Dict:
        """Create a folder record."""
        pass
    
    @abstractmethod
    async def get_folder(self, folder_path: str) -> Optional[Dict]:
        """Get a folder by path."""
        pass
    
    @abstractmethod
    async def get_all_folders(self) -> List[str]:
        """Get all folder paths (from both folders collection and documents)."""
        pass
    
    @abstractmethod
    async def delete_folder(self, folder_path: str) -> int:
        """Delete a folder and return count of deleted items."""
        pass
    
    @abstractmethod
    async def update_folder_path(self, old_path: str, new_path: Optional[str]) -> int:
        """Update folder paths when moving folders."""
        pass
    
    @abstractmethod
    async def get_documents_missing_summaries(self, limit: Optional[int] = None) -> List[Dict]:
        """Get documents that are missing summaries (summary is None or empty)."""
        pass
    
    @abstractmethod
    async def initialize(self):
        """Initialize database (create tables/collections, indexes, etc.)."""
        pass
    
    @abstractmethod
    async def close(self):
        """Close database connection."""
        pass

