# Text Extractors Module

Modular file format handlers for text extraction using the **Strategy Pattern**.

## Architecture

This module provides a plug-and-play architecture for text extraction from various file formats:

- **Base Interface**: `BaseTextExtractor` - Abstract base class for all extractors
- **Concrete Extractors**: Separate classes for each file format (PDF, DOCX, DOC, RTF, TXT, etc.)
- **Factory Pattern**: `TextExtractorFactory` - Manages registration and retrieval of extractors

## Current Supported Formats

- **PDF** (`.pdf`) - Using `pypdf`
- **DOCX** (`.docx`) - Using `python-docx` (optional)
- **DOC** (`.doc`) - Using `textract` (optional, requires system dependencies)
- **RTF** (`.rtf`) - Using `striprtf` (optional)
- **TXT** (`.txt`) - Plain text
- **Markdown** (`.md`, `.markdown`) - Plain text

## Adding Support for a New File Format

To add support for a new file format, follow these simple steps:

### Step 1: Create a New Extractor Class

Create a new file `backend/app/services/text_extractors/your_format_extractor.py`:

```python
"""
Your Format Text Extractor.

Extracts text from YOUR_FORMAT files using library_name library.
"""
from .base import BaseTextExtractor
from fastapi import HTTPException, status
from ...core.logging_config import get_logger

logger = get_logger(__name__)

# Check if library is available (optional)
try:
    import library_name
    LIBRARY_AVAILABLE = True
except ImportError:
    LIBRARY_AVAILABLE = False
    logger.warning("library_name not installed. YOUR_FORMAT files will be stored but text extraction will fail.")


class YourFormatExtractor(BaseTextExtractor):
    """Extractor for YOUR_FORMAT files."""
    
    def __init__(self):
        super().__init__(".your_ext", "YOUR_FORMAT")
    
    def _check_availability(self) -> bool:
        """Check if library is installed."""
        return LIBRARY_AVAILABLE
    
    def get_error_message(self) -> str:
        """Get error message when support is not available."""
        return "YOUR_FORMAT support not available. Please install library_name: pip install library_name"
    
    def extract(self, file_bytes: bytes) -> str:
        """
        Extract text from YOUR_FORMAT file.
        
        Args:
            file_bytes: File content as bytes
            
        Returns:
            Extracted text content
            
        Raises:
            HTTPException: If extraction fails
        """
        if not self.is_available():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=self.get_error_message()
            )
        
        try:
            # Your extraction logic here
            text_content = library_name.extract_text(file_bytes)
            
            # Validate content (inherited from base class)
            self.validate_content(text_content)
            
            return text_content
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error extracting text from YOUR_FORMAT: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error extracting text from YOUR_FORMAT: {str(e)}"
            )
```

### Step 2: Register the Extractor

Update `backend/app/services/text_extractors/factory.py`:

1. Import your new extractor:
```python
from .your_format_extractor import YourFormatExtractor
```

2. Register it in the `_initialize()` method:
```python
@classmethod
def _initialize(cls):
    """Initialize default extractors."""
    if cls._initialized:
        return
    
    # ... existing registrations ...
    cls.register(YourFormatExtractor())  # Add this line
    
    cls._initialized = True
```

### Step 3: Update Module Exports (Optional)

Update `backend/app/services/text_extractors/__init__.py` to export your extractor:

```python
from .your_format_extractor import YourFormatExtractor

__all__ = [
    # ... existing exports ...
    "YourFormatExtractor",
]
```

### Step 4: Add to Requirements (if needed)

If your extractor requires a new Python package, add it to `backend/requirements.txt`:

```
library_name>=1.0.0
```

## Example: Adding Excel (.xlsx) Support

Here's a complete example for adding Excel file support:

### 1. Create `xlsx_extractor.py`:

```python
"""
Excel Text Extractor.

Extracts text from XLSX files using openpyxl library.
"""
import io
from .base import BaseTextExtractor
from fastapi import HTTPException, status
from ...core.logging_config import get_logger

logger = get_logger(__name__)

try:
    from openpyxl import load_workbook
    XLSX_AVAILABLE = True
except ImportError:
    XLSX_AVAILABLE = False
    logger.warning("openpyxl not installed. XLSX files will be stored but text extraction will fail.")


class XlsxExtractor(BaseTextExtractor):
    """Extractor for XLSX (Excel) files."""
    
    def __init__(self):
        super().__init__(".xlsx", "XLSX")
    
    def _check_availability(self) -> bool:
        return XLSX_AVAILABLE
    
    def get_error_message(self) -> str:
        return "XLSX support not available. Please install openpyxl: pip install openpyxl"
    
    def extract(self, file_bytes: bytes) -> str:
        if not self.is_available():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=self.get_error_message()
            )
        
        try:
            workbook = load_workbook(io.BytesIO(file_bytes), data_only=True)
            text_content = ""
            
            for sheet_name in workbook.sheetnames:
                sheet = workbook[sheet_name]
                text_content += f"\n--- Sheet: {sheet_name} ---\n"
                
                for row in sheet.iter_rows(values_only=True):
                    row_text = [str(cell) for cell in row if cell is not None]
                    if row_text:
                        text_content += " | ".join(row_text) + "\n"
            
            self.validate_content(text_content)
            return text_content
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error extracting text from XLSX: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error extracting text from XLSX: {str(e)}"
            )
```

### 2. Register in `factory.py`:

```python
from .xlsx_extractor import XlsxExtractor

# In _initialize():
cls.register(XlsxExtractor())
```

That's it! The new format is now automatically supported.

## Benefits of This Architecture

1. **Modularity**: Each format has its own file and class
2. **Extensibility**: Easy to add new formats without modifying existing code
3. **Testability**: Each extractor can be tested independently
4. **Maintainability**: Changes to one format don't affect others
5. **Optional Dependencies**: Formats can gracefully handle missing libraries
6. **Single Responsibility**: Each extractor handles one format only

## Usage

The `FileService` automatically uses the extractor factory:

```python
from app.services.file_service import FileService

file_service = FileService()
text = await file_service.extract_text(file_path)
```

The factory automatically selects the appropriate extractor based on file extension.

## Testing

To test a new extractor:

```python
from app.services.text_extractors import YourFormatExtractor

extractor = YourFormatExtractor()
with open("test.your_ext", "rb") as f:
    text = extractor.extract(f.read())
    print(text)
```

