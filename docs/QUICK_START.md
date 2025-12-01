# Quick Start Guide - Understanding the Refactored Code

## 🎯 Goal

Make the codebase easy to read, understand, and modify.

## 📁 File Organization

```
backend/app/
├── routers/          ← HTTP endpoints (thin layer)
├── services/         ← Business logic (thick layer)
└── utils/            ← Helper functions
```

## 🔍 How to Read Code

### Step 1: Find the Router
Look in `routers/` for the endpoint you're interested in.

**Example**: Want to understand file upload?
→ Look at `routers/uploads.py`

### Step 2: Follow to Service
Routers call services. Find the service method being called.

**Example**: Router calls `upload_service.upload_single_file()`
→ Look at `services/upload_service.py`

### Step 3: Read the Service
Services contain the business logic. This is where the real work happens.

**Example**: `upload_single_file()` method shows:
- How files are validated
- How duplicates are checked
- How files are saved
- How database records are created

## 📝 Code Documentation Standards

### Every Function Has:
1. **Docstring** - Explains what it does
2. **Args** - Parameters with examples
3. **Returns** - What it returns
4. **Example** - Usage example

### Example:

```python
def upload_file(file: UploadFile, folder: Optional[str] = None):
    """
    Upload a single document file.
    
    This endpoint handles both regular files and ZIP archives.
    
    Args:
        file: The file to upload (required)
        folder: Optional folder path
                Example: "Invoices/2024"
    
    Returns:
        DocumentMetadata: Created document metadata
        
    Example:
        POST /upload
        file: invoice.pdf
        folder: Invoices/2024
    """
    # Implementation here
```

## 🗺️ Code Flow Examples

### Example 1: Upload a File

```
1. Client sends POST /upload with file
   ↓
2. Router (uploads.py) receives request
   ↓
3. Router calls UploadService.upload_single_file()
   ↓
4. Service:
   - Checks if ZIP → extracts files
   - Calculates checksum
   - Checks for duplicates
   - Saves file to storage
   - Creates database record
   ↓
5. Router returns document metadata
   ↓
6. Client receives response
```

### Example 2: Search Documents

```
1. Client sends GET /documents/search?q="invoices"
   ↓
2. Router (search.py) receives request
   ↓
3. Router calls SearchService.semantic_search()
   ↓
4. Service:
   - Parses query for filters
   - Generates query embedding
   - Gets all documents
   - Calculates similarity scores
   - Applies filters
   - Sorts by relevance
   ↓
5. Router returns search results
   ↓
6. Client receives matching documents
```

## 🎨 Code Patterns

### Pattern 1: Getting a Service
```python
# Always get services from dependencies
service = get_service_name()  # From dependencies.py
```

### Pattern 2: Error Handling
```python
try:
    result = await service.do_work()
except HTTPException:
    raise  # Re-raise HTTP exceptions
except Exception as e:
    raise HTTPException(500, detail=str(e))
```

### Pattern 3: Background Tasks
```python
# For async processing that doesn't block response
background_tasks.add_task(
    service.method_sync,
    arg1,
    arg2
)
```

## 📚 Key Files to Know

### Routers (HTTP Layer)
- `routers/documents.py` - Document CRUD
- `routers/uploads.py` - File uploads
- `routers/search.py` - Search operations
- `routers/folders.py` - Folder management
- `routers/files.py` - File serving

### Services (Business Logic)
- `services/upload_service.py` - Upload logic
- `services/search_service.py` - Search logic
- `services/document_processing_service.py` - AI processing
- `services/file_service.py` - File operations

### Utils (Helpers)
- `utils/search_utils.py` - Search helpers
- `utils/document_utils.py` - Document helpers

## ✅ Code Quality Checklist

When reading code, check for:
- ✅ Clear function names
- ✅ Docstrings explaining purpose
- ✅ Type hints on parameters
- ✅ Error handling
- ✅ Inline comments for complex logic
- ✅ Small, focused functions

## 🚀 Adding New Features

### To Add a New Endpoint:

1. **Add to Router** (`routers/documents.py`):
```python
@router.get("/documents/{doc_id}/metadata")
async def get_metadata(doc_id: str):
    """Get document metadata."""
    db_service = get_db_service()
    doc = await db_service.get_document(doc_id)
    return {"metadata": doc.get("extracted_fields")}
```

2. **Add Service Method** (if needed):
```python
# In services/document_service.py
async def get_metadata(self, doc_id: str):
    doc = await self.db_service.get_document(doc_id)
    return doc.get("extracted_fields")
```

3. **Test**: The endpoint is automatically available!

## 💡 Tips

1. **Start with routers** - They show the API surface
2. **Follow service calls** - Business logic is in services
3. **Read docstrings first** - They explain what code does
4. **Look for patterns** - Code follows consistent patterns
5. **Check utilities** - Common operations are in utils

## ❓ Common Questions

**Q: Where is the upload logic?**
→ `services/upload_service.py`

**Q: Where are the HTTP endpoints?**
→ `routers/*.py`

**Q: How do I add a new feature?**
→ Add router endpoint, add service method if needed

**Q: Where are helper functions?**
→ `utils/*.py`

## 📖 Further Reading

- `docs/CODE_WALKTHROUGH.md` - Detailed architecture walkthrough
- `docs/READING_CODE_GUIDE.md` - Comprehensive reading guide
- `docs/CODING_GUIDELINES.md` - Coding standards

