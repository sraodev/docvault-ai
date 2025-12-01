# Reading Code Guide - How to Navigate the Codebase

## Quick Start

### I want to understand how file upload works

1. **Start here**: `backend/app/routers/uploads.py`
   - Look at `upload_file()` function
   - See how it receives the HTTP request

2. **Follow the flow**: `backend/app/services/upload_service.py`
   - `upload_single_file()` method handles the logic
   - See how it checks for duplicates, saves files, creates database records

3. **See the details**: 
   - File saving: `backend/app/services/file_service.py`
   - Database operations: `backend/app/services/database/`

### I want to understand how search works

1. **Start here**: `backend/app/routers/search.py`
   - Look at `semantic_search()` function
   - See the query parameters

2. **Follow the flow**: `backend/app/services/search_service.py`
   - `semantic_search()` method does the work
   - See how it generates embeddings and calculates similarity

3. **See the helpers**: `backend/app/utils/search_utils.py`
   - `parse_search_filters()` extracts filters from query
   - `apply_filters()` applies filters to documents

### I want to understand how AI processing works

1. **Start here**: `backend/app/routers/documents.py`
   - Look at `process_document()` function
   - See how it triggers background processing

2. **Follow the flow**: `backend/app/services/document_processing_service.py`
   - `process_document()` method does the AI work
   - See how it extracts text, generates summary, tags, embeddings

3. **See the AI service**: `backend/app/services/ai_service.py`
   - Actual AI provider integration

## Code Structure Map

```
backend/app/
│
├── routers/              # HTTP Layer - Request/Response Only
│   ├── documents.py     # Document CRUD operations
│   ├── uploads.py       # File upload endpoints
│   ├── folders.py      # Folder management
│   ├── search.py        # Search endpoints
│   ├── files.py         # File serving
│   └── dependencies.py  # Service initialization
│
├── services/            # Business Logic Layer
│   ├── upload_service.py              # Upload business logic
│   ├── document_processing_service.py # AI processing logic
│   ├── search_service.py              # Search logic
│   ├── ai_service.py                  # AI provider wrapper
│   ├── file_service.py                # File operations
│   └── database/                      # Database adapters
│
└── utils/               # Helper Functions
    ├── search_utils.py      # Search helpers
    └── document_utils.py    # Document helpers
```

## Reading Patterns

### Pattern 1: Following a Request

When reading code, follow this pattern:

```
HTTP Request
    ↓
Router (routers/*.py)
    ↓
Service (services/*.py)
    ↓
Database/Storage (services/database/ or services/storage/)
    ↓
Response
```

**Example**: Upload a file
1. `routers/uploads.py` → `upload_file()` receives request
2. Calls `upload_service.upload_single_file()`
3. Service calls `file_service.save_upload()`
4. Service calls `db_service.create_document()`
5. Returns document metadata

### Pattern 2: Understanding a Feature

To understand a feature:

1. **Find the router** - Look in `routers/` for the endpoint
2. **Find the service** - Router calls a service method
3. **Read the service** - Business logic is here
4. **Check utilities** - Helper functions in `utils/`

**Example**: Understanding search
1. Router: `routers/search.py` → `semantic_search()`
2. Service: `services/search_service.py` → `semantic_search()`
3. Utils: `utils/search_utils.py` → `parse_search_filters()`

## Code Comments Guide

### Function Docstrings
Every function has a docstring explaining:
- **Purpose**: What it does
- **Args**: Parameters with examples
- **Returns**: What it returns
- **Raises**: Possible exceptions
- **Example**: Usage example

### Inline Comments
Inline comments explain:
- **Why**: Why code exists (not what it does)
- **Complex logic**: Non-obvious operations
- **Edge cases**: Special handling

### Example of Good Documentation

```python
def upload_file(file: UploadFile, folder: Optional[str] = None):
    """
    Upload a single document file.
    
    This endpoint handles both regular files and ZIP archives:
    - Regular files: Saved directly to storage
    - ZIP files: Extracted and each file processed individually
    
    Args:
        file: The file to upload (required)
        folder: Optional folder path
                Example: "Invoices/2024"
    
    Returns:
        DocumentMetadata: Created document metadata
    """
    # Get service via dependency injection
    upload_service = get_upload_service()
    
    # Process upload (handles ZIP extraction, duplicate checking, etc.)
    result = await upload_service.upload_single_file(file, folder)
    
    return result
```

## Common Code Patterns

### 1. Getting a Service
```python
# Pattern: Get service from dependencies
service = get_service_name()  # From dependencies.py
```

### 2. Error Handling
```python
# Pattern: Consistent error handling
try:
    result = await service.do_work()
except HTTPException:
    raise  # Re-raise HTTP exceptions
except Exception as e:
    raise HTTPException(500, detail=str(e))
```

### 3. Background Tasks
```python
# Pattern: Async background processing
background_tasks.add_task(
    service.method_sync,
    arg1,
    arg2
)
```

### 4. Database Operations
```python
# Pattern: Database operations
db_service = get_db_service()
doc = await db_service.get_document(doc_id)
await db_service.update_document(doc_id, {"status": "completed"})
```

## Finding Code

### "Where is the upload logic?"
→ `services/upload_service.py`

### "Where is the search logic?"
→ `services/search_service.py`

### "Where are the HTTP endpoints?"
→ `routers/*.py`

### "Where are helper functions?"
→ `utils/*.py`

### "How do I add a new endpoint?"
1. Add function to appropriate router in `routers/`
2. Call service method from `services/`
3. Return response

## Code Quality Indicators

### ✅ Good Code Has:
- Clear function names (`upload_file` not `do_upload`)
- Docstrings explaining purpose
- Inline comments for complex logic
- Type hints (`str`, `Optional[int]`)
- Error handling
- Small, focused functions

### ❌ Bad Code Has:
- Vague names (`process()` not `process_document()`)
- No documentation
- Long functions (>50 lines)
- Magic numbers (`if count > 1000:` not `if count > MAX_BATCH_SIZE:`)
- No error handling

## Tips for Reading

1. **Start with routers** - They show the API surface
2. **Follow service calls** - Business logic is in services
3. **Read docstrings first** - They explain what code does
4. **Look for patterns** - Code follows consistent patterns
5. **Check utilities** - Common operations are in utils

## Questions?

- **"How does X work?"** → Find the router endpoint, follow to service
- **"Where is Y?"** → Check the file structure map above
- **"How do I add Z?"** → Follow the patterns, add to appropriate layer

