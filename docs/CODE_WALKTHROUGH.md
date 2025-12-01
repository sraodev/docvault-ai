# Code Walkthrough - Refactored Architecture

## Overview

This document provides a simple walkthrough of the refactored codebase architecture. The code has been organized into clear layers following SOLID principles.

## Architecture Layers

```
┌─────────────────────────────────────────────────────────┐
│                    HTTP Layer (Routers)                  │
│  - documents.py  - uploads.py  - folders.py            │
│  - search.py     - files.py                            │
│  (Handle HTTP requests/responses only)                   │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                 Business Logic Layer (Services)          │
│  - upload_service.py                                    │
│  - document_processing_service.py                       │
│  - search_service.py                                   │
│  (Contains all business logic)                          │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                  Utility Layer (Utils)                   │
│  - search_utils.py  - document_utils.py                 │
│  (Reusable helper functions)                            │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│              Data Access Layer (Database)                │
│  - Database adapters (JSON, Scalable JSON, Memory)      │
│  (Handles all data persistence)                         │
└─────────────────────────────────────────────────────────┘
```

## File-by-File Walkthrough

### 1. Routers (HTTP Layer)

#### `routers/documents.py`
**Purpose**: Handle document CRUD operations

**Key Functions**:
- `GET /documents` - List all documents
- `GET /documents/{doc_id}` - Get single document
- `DELETE /documents/{doc_id}` - Delete document
- `POST /documents/{doc_id}/process` - Trigger AI processing

**How it works**:
1. Receives HTTP request
2. Gets service from dependency injection
3. Calls service method
4. Returns HTTP response

**Example Flow**:
```
User Request → Router → Service → Database → Service → Router → Response
```

#### `routers/uploads.py`
**Purpose**: Handle file uploads

**Key Functions**:
- `POST /upload` - Single file upload
- `POST /upload/bulk` - Bulk file upload
- `POST /upload/check-duplicate` - Check for duplicates

**How it works**:
1. Receives uploaded file
2. Calls `UploadService.upload_single_file()`
3. Service handles file saving, duplicate checking, database storage
4. Returns document metadata

#### `routers/search.py`
**Purpose**: Handle search operations

**Key Functions**:
- `GET /documents/search` - Semantic search
- `GET /documents/tags` - Get all tags
- `GET /documents/tags/{tag}` - Get documents by tag

**How it works**:
1. Receives search query
2. Calls `SearchService.semantic_search()`
3. Service parses query, generates embeddings, filters results
4. Returns matching documents

### 2. Services (Business Logic Layer)

#### `services/upload_service.py`
**Purpose**: Handle all upload-related business logic

**Key Methods**:
- `upload_single_file()` - Process single file upload
- `upload_bulk_files()` - Process bulk uploads with queue
- `check_duplicate()` - Check for duplicate files

**How it works**:
```python
# Example: Single file upload
1. Receive file from router
2. Check if ZIP file → extract and process each file
3. Calculate checksum
4. Check for duplicates
5. Save file to storage
6. Create document record in database
7. Return document metadata
```

#### `services/document_processing_service.py`
**Purpose**: Handle AI processing of documents

**Key Methods**:
- `process_document()` - Main processing method
- `_generate_tags()` - Generate tags with fallback
- `_generate_embedding()` - Generate search embeddings

**How it works**:
```python
# Example: Process document
1. Extract text from file
2. Generate summary (AI)
3. Generate markdown (AI)
4. Generate tags (AI with rule-based fallback)
5. Generate embedding for semantic search
6. Save markdown file
7. Update database with results
```

#### `services/search_service.py`
**Purpose**: Handle search operations

**Key Methods**:
- `semantic_search()` - Main search method
- `_semantic_search_with_embeddings()` - Use embeddings
- `_text_based_search()` - Fallback to text search

**How it works**:
```python
# Example: Semantic search
1. Parse query for filters (amount, date, type)
2. Generate embedding for query
3. Get all documents
4. Calculate similarity scores
5. Apply filters
6. Sort by relevance
7. Return top results
```

### 3. Utilities (Helper Functions)

#### `utils/search_utils.py`
**Purpose**: Search-related helper functions

**Key Functions**:
- `parse_search_filters()` - Extract filters from query
- `clean_query_for_semantic_search()` - Remove filter keywords
- `apply_filters()` - Apply filters to documents

**Example**:
```python
# Query: "invoices above ₹50,000"
filters = parse_search_filters(query)
# Returns: {"amount_min": 50000, "doc_type": "Invoice"}
```

#### `utils/document_utils.py`
**Purpose**: Document metadata utilities

**Key Functions**:
- `ensure_document_fields()` - Ensure required fields exist
- `normalize_folder_name()` - Normalize folder paths
- `create_document_metadata()` - Create standardized metadata

## Request Flow Examples

### Example 1: Upload a File

```
1. Client → POST /upload (with file)
2. Router (uploads.py) → receives request
3. Router → UploadService.upload_single_file()
4. UploadService:
   a. Checks if ZIP → extracts files
   b. Calculates checksum
   c. Checks for duplicates
   d. Saves file to storage
   e. Creates document in database
5. Router → triggers background AI processing
6. Router → returns document metadata
7. Client ← receives document metadata
```

### Example 2: Search Documents

```
1. Client → GET /documents/search?q="invoices above ₹50,000"
2. Router (search.py) → receives request
3. Router → SearchService.semantic_search()
4. SearchService:
   a. Parses query → extracts filters
   b. Generates query embedding
   c. Gets all documents
   d. Calculates similarity scores
   e. Applies filters (amount, type)
   f. Sorts by relevance
5. Router → returns filtered results
6. Client ← receives matching documents
```

### Example 3: Process Document

```
1. Client → POST /documents/{id}/process
2. Router (documents.py) → receives request
3. Router → checks document status
4. Router → queues background task
5. Background Task → DocumentProcessingService.process_document()
6. ProcessingService:
   a. Extracts text
   b. Generates summary (AI)
   c. Generates markdown (AI)
   d. Generates tags (AI + fallback)
   e. Generates embedding
   f. Saves markdown file
   g. Updates database
7. Document status → "completed"
```

## Key Design Patterns

### 1. Dependency Injection
Services are injected into routers, not created globally:
```python
# Good (Dependency Injection)
def get_documents():
    db_service = get_db_service()  # Injected
    return db_service.get_all_documents()

# Bad (Global State)
db_service = DatabaseService()  # Global
```

### 2. Single Responsibility
Each file has one clear purpose:
- Routers: HTTP only
- Services: Business logic only
- Utils: Helper functions only

### 3. Error Handling
Consistent error handling pattern:
```python
try:
    result = service.do_something()
    return result
except HTTPException:
    raise  # Re-raise HTTP exceptions
except Exception as e:
    raise HTTPException(500, detail=str(e))  # Wrap others
```

## Benefits of This Architecture

1. **Testability**: Each layer can be tested independently
2. **Maintainability**: Easy to find and modify code
3. **Scalability**: Easy to add new features
4. **Readability**: Clear separation of concerns
5. **Reusability**: Services can be reused across routers

## Adding New Features

### Adding a New Endpoint

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

## Code Quality Checklist

- ✅ Each function has a docstring
- ✅ Complex logic has inline comments
- ✅ Error handling is consistent
- ✅ Type hints are used
- ✅ Functions are small and focused
- ✅ No code duplication
- ✅ Clear variable names

## Common Patterns

### Getting a Service
```python
service = get_service_name()  # From dependencies.py
```

### Error Handling
```python
try:
    result = await service.do_work()
except HTTPException:
    raise  # Re-raise HTTP exceptions
except Exception as e:
    raise HTTPException(500, detail=str(e))
```

### Background Tasks
```python
background_tasks.add_task(
    service.method_sync,
    arg1,
    arg2
)
```

## Questions?

- **Where is business logic?** → `services/` directory
- **Where are HTTP endpoints?** → `routers/` directory
- **Where are helpers?** → `utils/` directory
- **How to add a feature?** → Add router endpoint, add service method if needed

