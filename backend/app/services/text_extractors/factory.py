"""
Text Extractor Factory.

Manages registration and retrieval of text extractors for different file formats.
Uses the Factory pattern to provide plug-and-play text extraction.
"""
from typing import Dict, Optional
from pathlib import Path
from fastapi import HTTPException, status
from .base import BaseTextExtractor
from .pdf_extractor import PDFExtractor
from .docx_extractor import DOCXExtractor
from .doc_extractor import DOCExtractor
from .rtf_extractor import RTFExtractor
from .text_extractor import TextExtractor
from ...core.logging_config import get_logger

logger = get_logger(__name__)


class TextExtractorFactory:
    """
    Factory for managing text extractors.
    
    Provides a centralized registry of extractors and easy extension
    for new file formats.
    """
    
    _extractors: Dict[str, BaseTextExtractor] = {}
    _initialized = False
    
    @classmethod
    def _initialize(cls):
        """Initialize default extractors."""
        if cls._initialized:
            return
        
        # Register default extractors (skip_init=True to avoid recursion)
        cls.register(PDFExtractor(), skip_init=True)
        cls.register(DOCXExtractor(), skip_init=True)
        cls.register(DOCExtractor(), skip_init=True)
        cls.register(RTFExtractor(), skip_init=True)
        
        # Register plain text extractors for various file types
        cls.register(TextExtractor(".txt", "TXT"), skip_init=True)
        cls.register(TextExtractor(".md", "Markdown"), skip_init=True)
        cls.register(TextExtractor(".markdown", "Markdown"), skip_init=True)
        
        # Register code/text file extractors (plain text files)
        code_extensions = [
            (".c", "C"),
            (".cpp", "C++"),
            (".h", "C Header"),
            (".hpp", "C++ Header"),
            (".java", "Java"),
            (".js", "JavaScript"),
            (".ts", "TypeScript"),
            (".py", "Python"),
            (".rb", "Ruby"),
            (".go", "Go"),
            (".rs", "Rust"),
            (".php", "PHP"),
            (".swift", "Swift"),
            (".kt", "Kotlin"),
            (".scala", "Scala"),
            (".sh", "Shell Script"),
            (".bash", "Bash Script"),
            (".zsh", "Zsh Script"),
            (".yaml", "YAML"),
            (".yml", "YAML"),
            (".json", "JSON"),
            (".xml", "XML"),
            (".html", "HTML"),
            (".css", "CSS"),
            (".sql", "SQL"),
            (".log", "Log File"),
            (".csv", "CSV"),
            (".ini", "INI"),
            (".conf", "Config"),
            (".config", "Config"),
        ]
        
        for ext, name in code_extensions:
            cls.register(TextExtractor(ext, name), skip_init=True)
        
        cls._initialized = True
        logger.info(f"TextExtractorFactory initialized with {len(cls._extractors)} extractors")
    
    @classmethod
    def register(cls, extractor: BaseTextExtractor, skip_init: bool = False):
        """
        Register a text extractor.
        
        Args:
            extractor: Text extractor instance to register
            skip_init: If True, skip initialization check (used internally)
        """
        if not skip_init:
            cls._initialize()
        extension = extractor.file_extension
        
        if extension in cls._extractors:
            logger.warning(f"Overriding existing extractor for {extension}")
        
        cls._extractors[extension] = extractor
        logger.debug(f"Registered extractor for {extension}: {extractor.format_name}")
    
    @classmethod
    def get_extractor(cls, file_path: Path) -> Optional[BaseTextExtractor]:
        """
        Get extractor for a file based on its extension.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Text extractor instance or None if not found
        """
        cls._initialize()
        file_ext = file_path.suffix.lower()
        return cls._extractors.get(file_ext)
    
    @classmethod
    def get_extractor_by_extension(cls, extension: str) -> Optional[BaseTextExtractor]:
        """
        Get extractor by file extension.
        
        Args:
            extension: File extension (e.g., '.pdf', '.docx')
            
        Returns:
            Text extractor instance or None if not found
        """
        cls._initialize()
        extension = extension.lower()
        if not extension.startswith('.'):
            extension = f'.{extension}'
        return cls._extractors.get(extension)
    
    @classmethod
    def extract_text(cls, file_bytes: bytes, file_path: Path) -> str:
        """
        Extract text from file using appropriate extractor.
        
        Args:
            file_bytes: File content as bytes
            file_path: Path to the file (used to determine format)
            
        Returns:
            Extracted text content
            
        Raises:
            HTTPException: If extraction fails or format not supported
        """
        cls._initialize()
        
        file_ext = file_path.suffix.lower()
        filename = file_path.name
        
        extractor = cls.get_extractor(file_path)
        
        if extractor is None:
            # Try UTF-8 decoding as fallback
            try:
                decoded = file_bytes.decode('utf-8', errors='ignore')
                if decoded.strip():
                    logger.info(f"Successfully decoded unsupported format '{file_ext}' as UTF-8 text: {filename}")
                    return decoded
            except Exception:
                pass
            
            # Format not supported
            supported_formats = cls.get_supported_formats()
            supported_extensions = cls.get_supported_extensions()
            error_message = (
                f"File format '{file_ext}' is not supported for text extraction. "
                f"Supported formats: {', '.join(sorted(set(supported_formats)))} "
                f"({', '.join(sorted(supported_extensions))})"
            )
            
            logger.warning(
                f"Unsupported file format attempted: {filename} (extension: {file_ext}). "
                f"Supported formats: {', '.join(sorted(set(supported_formats)))}"
            )
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_message
            )
        
        # Check if extractor is available
        if not extractor.is_available():
            error_message = extractor.get_error_message()
            logger.warning(
                f"File format '{file_ext}' requires library installation: {filename}. "
                f"Error: {error_message}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_message
            )
        
        # Extract text
        try:
            logger.debug(f"Extracting text from {filename} using {extractor.format_name} extractor")
            text_content = extractor.extract(file_bytes)
            logger.info(f"Successfully extracted {len(text_content)} characters from {filename} ({extractor.format_name})")
            return text_content
        except HTTPException:
            # Re-raise HTTP exceptions (already properly formatted)
            raise
        except Exception as e:
            logger.error(
                f"Error extracting text from {filename} ({extractor.format_name}): {str(e)}",
                exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error extracting text from {extractor.format_name} file '{filename}': {str(e)}"
            )
    
    @classmethod
    def get_supported_formats(cls) -> list:
        """
        Get list of supported file formats.
        
        Returns:
            List of supported format names
        """
        cls._initialize()
        return sorted([ext.format_name for ext in cls._extractors.values()])
    
    @classmethod
    def get_supported_extensions(cls) -> list:
        """
        Get list of supported file extensions.
        
        Returns:
            List of supported file extensions
        """
        cls._initialize()
        return sorted([ext for ext in cls._extractors.keys()])
    
    @classmethod
    def is_format_supported(cls, file_path: Path) -> bool:
        """
        Check if a file format is supported.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if format is supported, False otherwise
        """
        cls._initialize()
        extractor = cls.get_extractor(file_path)
        return extractor is not None and extractor.is_available()

