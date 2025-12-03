"""
Text Extractors Module - Modular file format handlers.

This module provides a plug-and-play architecture for text extraction
from various file formats using the Strategy pattern.

To add support for a new file format:
1. Create a new extractor class inheriting from BaseTextExtractor
2. Implement the extract() method
3. Register it in TextExtractorFactory

Example:
    class XlsxExtractor(BaseTextExtractor):
        def extract(self, file_bytes: bytes) -> str:
            # Implementation here
            pass
"""
from .base import BaseTextExtractor
from .factory import TextExtractorFactory
from .pdf_extractor import PDFExtractor
from .docx_extractor import DOCXExtractor
from .doc_extractor import DOCExtractor
from .rtf_extractor import RTFExtractor
from .text_extractor import TextExtractor

__all__ = [
    "BaseTextExtractor",
    "TextExtractorFactory",
    "PDFExtractor",
    "DOCXExtractor",
    "DOCExtractor",
    "RTFExtractor",
    "TextExtractor",
]

