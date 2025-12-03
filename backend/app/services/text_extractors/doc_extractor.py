"""
DOC Text Extractor.

Extracts text from DOC (old Word format) files using textract library.
Requires system dependencies: antiword or LibreOffice.
"""
import io
from .base import BaseTextExtractor
from fastapi import HTTPException, status
from ...core.logging_config import get_logger

logger = get_logger(__name__)

# Check if textract is available
try:
    import textract
    DOC_AVAILABLE = True
except ImportError:
    DOC_AVAILABLE = False
    # Only log once at module import, not on every request
    import sys
    if not hasattr(sys, '_doc_warning_logged'):
        logger.info("DOC file support: textract not installed (optional). "
                   "DOC files will be stored but text extraction requires: pip install textract "
                   "(also requires system dependency: antiword or LibreOffice)")
        sys._doc_warning_logged = True


class DOCExtractor(BaseTextExtractor):
    """Extractor for DOC (old Word format) files."""
    
    def __init__(self):
        super().__init__(".doc", "DOC")
    
    def _check_availability(self) -> bool:
        """Check if textract is installed."""
        return DOC_AVAILABLE
    
    def get_error_message(self) -> str:
        """Get error message when DOC support is not available."""
        return (
            "DOC (old Word format) extraction requires 'textract' library. "
            "Install with: pip install textract (requires antiword or LibreOffice). "
            "Alternatively, convert DOC to DOCX before uploading."
        )
    
    def extract(self, file_bytes: bytes) -> str:
        """
        Extract text from DOC file.
        
        Args:
            file_bytes: DOC file content as bytes
            
        Returns:
            Extracted text content
            
        Raises:
            HTTPException: If DOC extraction fails or library not available
        """
        if not self.is_available():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=self.get_error_message()
            )
        
        try:
            # Use textract to extract text from DOC files
            # textract requires system dependencies (antiword or LibreOffice)
            text_content = textract.process(io.BytesIO(file_bytes), extension='doc').decode('utf-8')
            
            # Validate content
            self.validate_content(text_content)
            
            return text_content
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error extracting text from DOC: {e}", exc_info=True)
            error_msg = str(e)
            
            if "antiword" in error_msg.lower() or "libreoffice" in error_msg.lower():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"DOC extraction failed: {error_msg}. "
                        "Please ensure antiword or LibreOffice is installed on the system. "
                        "Alternatively, convert DOC to DOCX before uploading."
                    )
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Error extracting text from DOC: {error_msg}"
                )

