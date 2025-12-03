"""
File Service Interface.

Defines the contract for file operations.
"""
from abc import ABC, abstractmethod
from pathlib import Path


class IFileService(ABC):
    """
    Interface for file operations.
    
    Defines the contract for file storage and text extraction operations.
    Handles file saving, text extraction, deletion, and markdown storage.
    """
    
    @abstractmethod
    async def save_upload(self, file, destination: Path) -> None:
        """
        Save an uploaded file to storage.
        
        Args:
            file: Uploaded file object (FastAPI UploadFile)
            destination: Path where file should be saved
        """
        pass
    
    @abstractmethod
    async def extract_text(self, file_path: Path) -> str:
        """
        Extract text content from a file.
        
        Supports multiple file formats (PDF, DOCX, DOC, RTT, TXT, MD, etc.)
        Uses modular text extractors for format-specific extraction.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Extracted text content
            
        Raises:
            HTTPException: If file format is not supported or extraction fails
        """
        pass
    
    @abstractmethod
    async def delete_file(self, file_path: Path) -> None:
        """
        Delete a file from storage.
        
        Args:
            file_path: Path to the file to delete
        """
        pass
    
    @abstractmethod
    async def save_markdown(self, content: str, destination: Path) -> None:
        """
        Save markdown content to storage.
        
        Args:
            content: Markdown content to save
            destination: Path where markdown should be saved
        """
        pass

