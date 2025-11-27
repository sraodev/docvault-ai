# Database Architecture - Plug-and-Play Design Pattern

## Overview

DocVault AI uses a **Repository Pattern** with **Strategy Pattern** to provide plug-and-play database support. This allows switching between different database backends (JSON, Memory, PostgreSQL, etc.) **without changing any business logic**.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  Business Logic Layer                    │
│  (documents.py, useDocuments.ts, etc.)                  │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ Uses
                     ▼
┌─────────────────────────────────────────────────────────┐
│              DatabaseInterface (Abstract)               │
│  - create_document()                                    │
│  - get_document()                                       │
│  - update_document()                                    │
│  - delete_document()                                    │
│  - create_folder()                                      │
│  - ... (all database operations)                       │
└───────┬───────────────────────────────┬─────────────────┘
        │                               │
        │ Implements                    │ Implements
        ▼                               ▼
┌──────────────────┐          ┌──────────────────┐
│   JSONAdapter    │          │  MemoryAdapter   │
│   (JSON Files)   │          │  (In-Memory)     │
└──────────────────┘          └──────────────────┘
        │                               │
        └───────────┬───────────────────┘
                    │
                    ▼
        ┌───────────────────────┐
        │   DatabaseFactory      │
        │   (Factory Pattern)    │
        └───────────────────────┘
```

## Design Patterns Used

### 1. Repository Pattern
- **DatabaseInterface**: Abstract interface defining all database operations
- **Concrete Adapters**: JSONAdapter, MemoryAdapter implement the interface
- **Business Logic**: Depends only on DatabaseInterface, not concrete implementations

### 2. Strategy Pattern
- Different database strategies can be swapped at runtime
- Selected via `DATABASE_TYPE` environment variable
- No code changes needed to switch databases

### 3. Factory Pattern
- **DatabaseFactory**: Creates appropriate adapter based on configuration
- Handles initialization automatically
- Single point of database creation

### 4. Dependency Inversion Principle (SOLID)
- High-level modules (business logic) don't depend on low-level modules (database)
- Both depend on abstractions (`DatabaseInterface`)

## Available Databases

### JSON Adapter (Recommended for Demos)
- **Type**: File-based JSON storage
- **Persistence**: Yes (data survives restarts)
- **Storage**: `data/json_db/documents.json` and `folders.json`
- **Best for**: Local demos, development, easy debugging
- **Setup**: Zero configuration needed

### Memory Adapter (Testing)
- **Type**: In-memory Python dictionaries
- **Persistence**: No (data lost on restart)
- **Storage**: RAM only
- **Best for**: Testing, quick prototyping
- **Setup**: Zero configuration needed

## How It Works

### 1. Business Logic Layer
```python
# documents.py - Uses DatabaseInterface
from ..services.database import DatabaseFactory

db_service = await DatabaseFactory.create_and_initialize()

# Same code works with all databases!
doc = await db_service.create_document({...})
docs = await db_service.get_all_documents(folder="folder1")
```

### 2. Database Factory
```python
# factory.py - Creates appropriate adapter
if DATABASE_TYPE == "json":
    return JSONAdapter(data_dir=...)
elif DATABASE_TYPE == "memory":
    return MemoryAdapter()
```

### 3. Adapter Implementation
```python
# json_adapter.py - Implements DatabaseInterface
class JSONAdapter(DatabaseInterface):
    async def create_document(self, doc_data: Dict) -> Dict:
        # JSON-specific implementation
        ...
```

## Benefits

✅ **Zero Business Logic Changes** - Switch databases with one env var  
✅ **Easy to Extend** - Add new databases by implementing interface  
✅ **Testable** - Mock DatabaseInterface for unit tests  
✅ **Demo Ready** - JSON for demos, Memory for testing  
✅ **SOLID Principles** - Follows best practices  

## Adding a New Database

### Step 1: Create Adapter
```python
# backend/app/services/database/postgresql_adapter.py
from .base import DatabaseInterface

class PostgreSQLAdapter(DatabaseInterface):
    async def create_document(self, doc_data: Dict) -> Dict:
        # PostgreSQL implementation
        pass
    
    # Implement all other methods from DatabaseInterface
    ...
```

### Step 2: Update Factory
```python
# backend/app/services/database/factory.py
elif database_type == "postgresql":
    return DatabaseFactory._create_postgresql(**kwargs)
```

### Step 3: Use It
```bash
export DATABASE_TYPE=postgresql
python main.py
```

**Done!** Business logic remains unchanged.

## File Structure

```
backend/app/services/database/
├── __init__.py              # Exports
├── base.py                  # DatabaseInterface (abstract)
├── json_adapter.py          # JSON implementation
├── memory_adapter.py         # Memory implementation
├── factory.py               # DatabaseFactory
└── README.md               # Documentation
```

## Current Status

- ✅ Abstract interface defined (`DatabaseInterface`)
- ✅ JSON adapter implemented (file-based, persistent)
- ✅ Memory adapter implemented (in-memory, non-persistent)
- ✅ Factory pattern implemented
- ✅ Business logic updated to use interface
- ✅ Configuration system in place

## Example Usage

```python
# Business logic (documents.py)
from ..services.database import DatabaseFactory

# Initialize (handled automatically on startup)
db_service = await DatabaseFactory.create_and_initialize()

# Use database (same code for all databases)
doc = await db_service.create_document({
    "id": "123",
    "filename": "test.pdf",
    "folder": "folder1"
})
docs = await db_service.get_all_documents(folder="folder1")
await db_service.update_document("123", {"status": "completed"})
```

**The same code works with JSON, Memory, PostgreSQL, or any future database!**
