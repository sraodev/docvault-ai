"""
PDF Text Extractor.

Extracts text from PDF files using pypdf library.
"""
import tempfile
from pathlib import Path
from pypdf import PdfReader
from fastapi import HTTPException, status
from .base import BaseTextExtractor
from ...core.logging_config import get_logger

logger = get_logger(__name__)


class PDFExtractor(BaseTextExtractor):
    """Extractor for PDF files."""
    
    def __init__(self):
        super().__init__(".pdf", "PDF")
    
    def extract(self, file_bytes: bytes) -> str:
        """
        Extract text from PDF file.
        
        Args:
            file_bytes: PDF file content as bytes
            
        Returns:
            Extracted text content
            
        Raises:
            HTTPException: If PDF extraction fails
        """
        try:
            # Create temporary file for PDF reading
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                tmp_file.write(file_bytes)
                tmp_path = Path(tmp_file.name)
            
            try:
                reader = PdfReader(tmp_path)
                text_content = ""
                
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_content += page_text + "\n"
                
                # Validate content
                self.validate_content(text_content)
                
                return text_content
            finally:
                # Clean up temp file
                if tmp_path.exists():
                    tmp_path.unlink()
                    
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error extracting text from PDF: {str(e)}"
            )

