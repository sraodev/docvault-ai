# File Format Support Analysis

**Last Updated**: January 2025  
**Status**: Limited Support - PDF and Text Files Only

---

## Current File Format Support

### ✅ **Fully Supported** (Text Extraction Works)

| Format | Extension | Library | Status | Notes |
|--------|-----------|---------|--------|-------|
| **PDF** | `.pdf` | `pypdf` | ✅ **Full Support** | Text extraction works, AI processing enabled |
| **Text** | `.txt` | Built-in | ✅ **Full Support** | UTF-8 decoding, AI processing enabled |
| **Markdown** | `.md` | Built-in | ✅ **Full Support** | UTF-8 decoding, AI processing enabled |
| **Word (DOCX)** | `.docx` | `python-docx` | ✅ **Full Support** | Text extraction from paragraphs and tables, AI processing enabled |
| **Word (DOC)** | `.doc` | `textract` (optional) | ✅ **Full Support** | Requires textract + antiword/LibreOffice, AI processing enabled |

### ⚠️ **Partially Supported** (Stored but Not Extracted)

| Format | Extension | Status | Issue |
|--------|-----------|--------|-------|
| **Rich Text** | `.rtf` | ⚠️ **Storage Only** | Files are saved but text extraction NOT implemented |
| **OpenDocument** | `.odt` | ⚠️ **Storage Only** | Files are saved but text extraction NOT implemented |

### ❌ **Not Supported** (No Processing)

| Format | Extension | Status | Notes |
|--------|-----------|--------|-------|
| **Images** | `.jpg`, `.jpeg`, `.png`, `.gif` | ❌ **Display Only** | Shown in UI but no OCR/text extraction |
| **Excel** | `.xlsx`, `.xls` | ❌ **Not Supported** | Not in supported list |
| **PowerPoint** | `.pptx`, `.ppt` | ❌ **Not Supported** | Not in supported list |
| **CSV** | `.csv` | ❌ **Not Supported** | Not in supported list |
| **HTML** | `.html`, `.htm` | ❌ **Not Supported** | Not in supported list |
| **JSON** | `.json` | ❌ **Not Supported** | Not in supported list |
| **XML** | `.xml` | ❌ **Not Supported** | Not in supported list |

---

## Current Implementation

### Text Extraction Logic

**File**: `backend/app/services/file_service.py`

```python
async def extract_text(self, file_path: Path) -> str:
    file_ext = file_path.suffix.lower()
    
    if file_ext == ".pdf":
        # PDF extraction using pypdf
        reader = PdfReader(tmp_path)
        text_content = ""
        for page in reader.pages:
            text_content += page.extract_text() + "\n"
        return text_content
    
    elif file_ext == ".docx":
        # DOCX extraction using python-docx
        doc = DocxDocument(io.BytesIO(file_bytes))
        text_content = ""
        # Extract from paragraphs
        for paragraph in doc.paragraphs:
            text_content += paragraph.text + "\n"
        # Extract from tables
        for table in doc.tables:
            for row in table.rows:
                row_text = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if row_text:
                    text_content += " | ".join(row_text) + "\n"
        return text_content
    
    elif file_ext == ".doc":
        # DOC extraction using textract (requires antiword/LibreOffice)
        text_content = textract.process(io.BytesIO(file_bytes), extension='doc').decode('utf-8')
        return text_content
    
    elif file_ext in [".txt", ".md"]:
        # Plain text files
        return file_bytes.decode('utf-8', errors='ignore')
```

**Current Support**:
- ✅ PDF files - Full text extraction
- ✅ DOCX files - Full text extraction (paragraphs + tables)
- ✅ DOC files - Full text extraction (requires textract)
- ✅ TXT/MD files - UTF-8 decoding
- ❌ Binary files (images, Excel, etc.) - Not supported
- ❌ No OCR for images
- ❌ No structured data extraction (Excel, CSV)

### ZIP File Support

**File**: `backend/app/services/file_service.py` (line 324)

```python
supported_extensions = {'.pdf', '.txt', '.md', '.docx', '.doc', '.rtf', '.odt'}
```

**Issue**: DOCX, DOC, RTF, ODT are listed but **NOT actually extracted** - they're just stored.

---

## Impact on AI Processing

### ✅ **Works** (AI Processing Enabled)
- PDF files → Text extracted → AI summary/markdown/tags generated
- TXT files → Text extracted → AI summary/markdown/tags generated
- MD files → Text extracted → AI summary/markdown/tags generated

### ❌ **Doesn't Work** (No AI Processing)
- DOCX files → **No text extraction** → AI processing fails or processes empty text
- Images → **No OCR** → AI processing fails or processes empty text
- Excel → **Not supported** → Cannot upload
- PowerPoint → **Not supported** → Cannot upload

---

## How to Add Support for More Formats

### ✅ Option 1: DOCX Support (IMPLEMENTED)

**Status**: ✅ **COMPLETE** - DOCX support is now fully implemented!

**Library**: `python-docx` (installed)

**Implementation**: 
- Extracts text from paragraphs
- Extracts text from tables
- Handles empty documents gracefully
- Error handling with clear messages

**Usage**: DOCX files uploaded will now have text extracted and AI processing enabled.

### Option 2: Add Image OCR Support (Medium - 4-6 hours)

**Install Libraries**:
```bash
pip install pytesseract pillow
# Also need Tesseract OCR installed on system
```

**Update**: `backend/app/services/file_service.py`

```python
from PIL import Image
import pytesseract

async def extract_text(self, file_path: Path) -> str:
    # ... existing code ...
    
    elif file_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif']:
        try:
            image = Image.open(io.BytesIO(file_bytes))
            text_content = pytesseract.image_to_string(image)
            return text_content
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error extracting text from image: {str(e)}"
            )
```

### Option 3: Add Excel Support (Medium - 4-6 hours)

**Install Library**:
```bash
pip install openpyxl pandas
```

**Update**: `backend/app/services/file_service.py`

```python
import pandas as pd
from openpyxl import load_workbook

async def extract_text(self, file_path: Path) -> str:
    # ... existing code ...
    
    elif file_path.suffix.lower() in ['.xlsx', '.xls']:
        try:
            # Read Excel file
            df = pd.read_excel(io.BytesIO(file_bytes), sheet_name=None)
            text_content = ""
            for sheet_name, sheet_df in df.items():
                text_content += f"\n=== Sheet: {sheet_name} ===\n"
                text_content += sheet_df.to_string() + "\n"
            return text_content
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error extracting text from Excel: {str(e)}"
            )
```

### Option 4: Add PowerPoint Support (Medium - 4-6 hours)

**Install Library**:
```bash
pip install python-pptx
```

**Update**: `backend/app/services/file_service.py`

```python
from pptx import Presentation

async def extract_text(self, file_path: Path) -> str:
    # ... existing code ...
    
    elif file_path.suffix.lower() in ['.pptx', '.ppt']:
        try:
            prs = Presentation(io.BytesIO(file_bytes))
            text_content = ""
            for slide_num, slide in enumerate(prs.slides, 1):
                text_content += f"\n=== Slide {slide_num} ===\n"
                for shape in slide.shapes:
                    if hasattr(shape, "text"):
                        text_content += shape.text + "\n"
            return text_content
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error extracting text from PowerPoint: {str(e)}"
            )
```

---

## Recommended Implementation Plan

### ✅ Phase 1: Quick Wins (COMPLETE)
1. ✅ **DOCX support** (python-docx) - **IMPLEMENTED**
   - Text extraction from paragraphs and tables
   - AI processing enabled
   - Full support complete

2. ✅ **DOC support** (textract) - **IMPLEMENTED**
   - Requires textract library (optional)
   - Requires system dependencies (antiword or LibreOffice)
   - AI processing enabled when available

### Phase 2: Additional Formats (Next Steps)
1. **Add RTF support** (striprtf)
   ```bash
   pip install striprtf
   ```

2. **Add ODT support** (odfpy or python-odf)
   ```bash
   pip install odfpy
   ```

### Phase 2: Structured Data (1 week)
1. **Add Excel support** (openpyxl, pandas)
   - Extract text from cells
   - Handle multiple sheets
   - Preserve structure

2. **Add CSV support** (built-in csv module)
   - Simple text extraction
   - Preserve structure

### Phase 3: Advanced (2 weeks)
1. **Add Image OCR** (pytesseract)
   - Extract text from images
   - Handle multiple languages
   - PDF with images

2. **Add PowerPoint support** (python-pptx)
   - Extract text from slides
   - Handle notes and comments

---

## Current Code Locations

### Text Extraction
- **File**: `backend/app/services/file_service.py`
- **Function**: `extract_text()` (line 92)
- **Current Logic**: Only handles PDF and assumes UTF-8 for others

### File Type Validation
- **File**: `backend/app/services/file_service.py`
- **Function**: `extract_zip_files()` (line 324)
- **Supported List**: `{'.pdf', '.txt', '.md', '.docx', '.doc', '.rtf', '.odt'}`

### Frontend Icons
- **File**: `frontend/src/components/DriveView.tsx`
- **Function**: `getFileIcon()` (line 15)
- **Supported**: PDF, DOCX, Images (JPG/PNG/GIF)

---

## Testing Different Formats

### Test Uploads

**Currently Works**:
```bash
# PDF
curl -X POST http://localhost:8000/upload \
  -F "file=@document.pdf"

# TXT
curl -X POST http://localhost:8000/upload \
  -F "file=@document.txt"

# MD
curl -X POST http://localhost:8000/upload \
  -F "file=@document.md"
```

**Stored but No AI Processing**:
```bash
# DOCX (stored but text not extracted)
curl -X POST http://localhost:8000/upload \
  -F "file=@document.docx"
# Result: File saved, but AI processing fails (empty text)
```

**Not Supported**:
```bash
# Excel (rejected or fails)
curl -X POST http://localhost:8000/upload \
  -F "file=@spreadsheet.xlsx"
# Result: May be rejected or stored without processing
```

---

## Summary

### Current State (Updated)
- ✅ **5 formats** fully supported (PDF, TXT, MD, DOCX, DOC)
- ⚠️ **2 formats** stored but not extracted (RTF, ODT)
- ❌ **Many formats** not supported (Excel, PowerPoint, Images, CSV, etc.)

### Recent Updates
- ✅ **DOCX**: Full support implemented (python-docx)
- ✅ **DOC**: Full support implemented (textract, optional)

### Recommendation
1. ✅ **COMPLETE**: DOCX and DOC support added
2. **Short-term**: Add Excel and CSV support (structured data)
3. **Medium-term**: Add RTF and ODT support
4. **Long-term**: Add Image OCR and PowerPoint support

### Estimated Effort (Remaining)
- **RTF**: 2-3 hours
- **ODT**: 2-3 hours
- **Excel/CSV**: 4-6 hours
- **Image OCR**: 4-6 hours (plus Tesseract installation)
- **PowerPoint**: 4-6 hours
- **Total**: ~2-3 days for remaining format support

---

**Would you like me to implement support for any specific format?**

