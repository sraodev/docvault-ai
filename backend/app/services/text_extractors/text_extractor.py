"""
Plain Text Extractor.

Extracts text from plain text files (TXT, MD, Markdown).
"""
from .base import BaseTextExtractor
from fastapi import HTTPException, status
from ...core.logging_config import get_logger

logger = get_logger(__name__)


class TextExtractor(BaseTextExtractor):
    """Extractor for plain text files (TXT, MD, Markdown)."""
    
    def __init__(self, file_extension: str, format_name: str):
        """
        Initialize text extractor.
        
        Args:
            file_extension: File extension (e.g., '.txt', '.md')
            format_name: Format name (e.g., 'TXT', 'Markdown')
        """
        super().__init__(file_extension, format_name)
    
    def extract(self, file_bytes: bytes) -> str:
        """
        Extract text from plain text file.
        
        Args:
            file_bytes: Text file content as bytes
            
        Returns:
            Extracted text content
            
        Raises:
            HTTPException: If text reading fails
        """
        try:
            text_content = file_bytes.decode('utf-8', errors='ignore')
            
            # Validate content
            self.validate_content(text_content)
            
            return text_content
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error reading text file: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error reading text file: {str(e)}"
            )

