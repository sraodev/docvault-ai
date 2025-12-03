"""
Abstract base class for file storage adapters.
All storage implementations must inherit from this class.
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, BinaryIO
from fastapi import UploadFile
from ...core.logging_config import get_logger

logger = get_logger(__name__)

class FileStorageInterface(ABC):
    """
    Abstract interface for file storage operations.
    All storage adapters must implement these methods.
    This allows plug-and-play storage support (local, S3, Supabase) without changing business logic.
    """
    
    @abstractmethod
    async def save_file(self, file: UploadFile, file_path: str) -> str:
        """
        Save an uploaded file to storage.
        
        Args:
            file: FastAPI UploadFile object
            file_path: Path/key where file should be stored (relative path or S3 key)
        
        Returns:
            Storage path/key where file was saved (for retrieval)
        """
        pass
    
    @abstractmethod
    async def get_file(self, file_path: str) -> bytes:
        """
        Retrieve a file from storage.
        
        Args:
            file_path: Storage path/key of the file
        
        Returns:
            File contents as bytes
        """
        pass
    
    @abstractmethod
    async def delete_file(self, file_path: str) -> bool:
        """
        Delete a file from storage.
        
        Args:
            file_path: Storage path/key of the file to delete
        
        Returns:
            True if file was deleted, False if not found
        """
        pass
    
    @abstractmethod
    async def file_exists(self, file_path: str) -> bool:
        """
        Check if a file exists in storage.
        
        Args:
            file_path: Storage path/key to check
        
        Returns:
            True if file exists, False otherwise
        """
        pass
    
    @abstractmethod
    async def get_file_url(self, file_path: str, expires_in: Optional[int] = None) -> str:
        """
        Get a URL to access the file (for direct download/viewing).
        
        Args:
            file_path: Storage path/key of the file
            expires_in: Optional expiration time in seconds (for signed URLs)
        
        Returns:
            URL string for accessing the file
        """
        pass
    
    @abstractmethod
    async def save_text(self, content: str, file_path: str) -> str:
        """
        Save text content to storage.
        
        Args:
            content: Text content to save
            file_path: Storage path/key where content should be saved
        
        Returns:
            Storage path/key where content was saved
        """
        pass
    
    @abstractmethod
    async def get_text(self, file_path: str) -> str:
        """
        Retrieve text content from storage.
        
        Args:
            file_path: Storage path/key of the file
        
        Returns:
            Text content as string
        """
        pass
    
    @abstractmethod
    async def initialize(self):
        """Initialize storage (create buckets/directories, verify connections, etc.)."""
        pass
    
    @abstractmethod
    async def close(self):
        """Close storage connection (cleanup, close clients, etc.)."""
        pass

