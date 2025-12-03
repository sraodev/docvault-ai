"""
RTF Text Extractor.

Extracts text from RTF (Rich Text Format) files using striprtf library.
"""
from .base import BaseTextExtractor
from fastapi import HTTPException, status
from ...core.logging_config import get_logger

logger = get_logger(__name__)

# Check if striprtf is available
try:
    from striprtf.striprtf import rtf_to_text
    RTF_AVAILABLE = True
except ImportError:
    RTF_AVAILABLE = False
    logger.warning("striprtf not installed. RTF files will be stored but text extraction will fail. "
                   "Install with: pip install striprtf")


class RTFExtractor(BaseTextExtractor):
    """Extractor for RTF (Rich Text Format) files."""
    
    def __init__(self):
        super().__init__(".rtf", "RTF")
    
    def _check_availability(self) -> bool:
        """Check if striprtf is installed."""
        return RTF_AVAILABLE
    
    def get_error_message(self) -> str:
        """Get error message when RTF support is not available."""
        return "RTF support not available. Please install striprtf: pip install striprtf"
    
    def extract(self, file_bytes: bytes) -> str:
        """
        Extract text from RTF file.
        
        Args:
            file_bytes: RTF file content as bytes
            
        Returns:
            Extracted text content
            
        Raises:
            HTTPException: If RTF extraction fails or library not available
        """
        if not self.is_available():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=self.get_error_message()
            )
        
        try:
            # Decode RTF content (RTF files are typically encoded as text)
            rtf_content = file_bytes.decode('utf-8', errors='ignore')
            
            # Convert RTF to plain text
            text_content = rtf_to_text(rtf_content)
            
            # Validate content
            self.validate_content(text_content)
            
            return text_content
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error extracting text from RTF: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error extracting text from RTF: {str(e)}"
            )

