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

### ⚠️ **Partially Supported** (Stored but Not Extracted)

| Format | Extension | Status | Issue |
|--------|-----------|--------|-------|
| **Word** | `.docx`, `.doc` | ⚠️ **Storage Only** | Files are saved but text extraction NOT implemented |
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
    # Only handles PDF and text files
    if file_path.suffix.lower() == ".pdf":
        # PDF extraction using pypdf
        reader = PdfReader(tmp_path)
        text_content = ""
        for page in reader.pages:
            text_content += page.extract_text() + "\n"
        return text_content
    else:
        # Assumes all other files are text (UTF-8)
        return file_bytes.decode('utf-8', errors='ignore')
```

**Limitations**:
- ❌ DOCX files are stored but text is NOT extracted
- ❌ Binary files (images, Excel, etc.) cannot be decoded as UTF-8
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

### Option 1: Add DOCX Support (Easy - 1-2 hours)

**Install Library**:
```bash
pip install python-docx
```

**Update**: `backend/app/services/file_service.py`

```python
from docx import Document

async def extract_text(self, file_path: Path) -> str:
    # ... existing PDF handling ...
    
    elif file_path.suffix.lower() == ".docx":
        try:
            doc = Document(io.BytesIO(file_bytes))
            text_content = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            return text_content
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error extracting text from DOCX: {str(e)}"
            )
    
    # ... rest of code ...
```

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

### Phase 1: Quick Wins (1-2 days)
1. **Add DOCX support** (python-docx)
   - Most requested format
   - Easy to implement
   - High impact

2. **Add RTF support** (striprtf)
   ```bash
   pip install striprtf
   ```

3. **Update ZIP extraction** to actually extract DOCX/RTF

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

### Current State
- ✅ **3 formats** fully supported (PDF, TXT, MD)
- ⚠️ **4 formats** stored but not extracted (DOCX, DOC, RTF, ODT)
- ❌ **Many formats** not supported (Excel, PowerPoint, Images, CSV, etc.)

### Recommendation
1. **Immediate**: Add DOCX support (high impact, easy)
2. **Short-term**: Add Excel and CSV support (structured data)
3. **Long-term**: Add Image OCR and PowerPoint support

### Estimated Effort
- **DOCX**: 1-2 hours
- **Excel/CSV**: 4-6 hours
- **Image OCR**: 4-6 hours (plus Tesseract installation)
- **PowerPoint**: 4-6 hours
- **Total**: ~2-3 days for full format support

---

**Would you like me to implement support for any specific format?**

