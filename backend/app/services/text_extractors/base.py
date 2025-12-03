"""
Base Text Extractor Interface.

All text extractors must inherit from this base class and implement
the extract() method.
"""
from abc import ABC, abstractmethod
from typing import Optional
from fastapi import HTTPException, status
from ...core.logging_config import get_logger

logger = get_logger(__name__)


class BaseTextExtractor(ABC):
    """
    Abstract base class for text extractors.
    
    Each file format should have its own extractor class that inherits
    from this base class and implements the extract() method.
    """
    
    def __init__(self, file_extension: str, format_name: str):
        """
        Initialize the extractor.
        
        Args:
            file_extension: File extension (e.g., '.pdf', '.docx')
            format_name: Human-readable format name (e.g., 'PDF', 'DOCX')
        """
        self.file_extension = file_extension.lower()
        self.format_name = format_name
        self._available = self._check_availability()
    
    @abstractmethod
    def extract(self, file_bytes: bytes) -> str:
        """
        Extract text from file bytes.
        
        Args:
            file_bytes: Raw file content as bytes
            
        Returns:
            Extracted text content
            
        Raises:
            HTTPException: If extraction fails or format is not supported
        """
        pass
    
    def _check_availability(self) -> bool:
        """
        Check if the required library is available for this extractor.
        
        Override this method in subclasses to check for optional dependencies.
        
        Returns:
            True if the extractor is available, False otherwise
        """
        return True
    
    def is_available(self) -> bool:
        """
        Check if this extractor is available (library installed).
        
        Returns:
            True if available, False otherwise
        """
        return self._available
    
    def get_error_message(self) -> str:
        """
        Get error message when extractor is not available.
        
        Returns:
            Error message with installation instructions
        """
        return f"{self.format_name} support not available. Please install required library."
    
    def validate_content(self, text_content: str) -> None:
        """
        Validate that extracted content is not empty.
        
        Args:
            text_content: Extracted text content
            
        Raises:
            HTTPException: If content is empty
        """
        if not text_content or not text_content.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{self.format_name} file appears to be empty or contains no extractable text"
            )

