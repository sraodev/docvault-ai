# Plug-and-Play Database Architecture

## ✅ Implementation Complete!

DocVault AI now uses a **plug-and-play database architecture** that allows switching between databases **without touching any business logic**.

## Architecture Overview

```
┌─────────────────────────────────────────┐
│         Business Logic Layer            │
│  (documents.py - uses DatabaseInterface)│
└──────────────────┬──────────────────────┘
                   │
                   │ Depends on
                   ▼
┌─────────────────────────────────────────┐
│      DatabaseInterface (Abstract)       │
│  - create_document()                    │
│  - get_document()                       │
│  - update_document()                    │
│  - delete_document()                    │
│  - create_folder()                      │
│  - ... (all operations)                 │
└───┬───────────────────────────────┬─────┘
    │                               │
    │ Implements                    │ Implements
    ▼                               ▼
┌──────────────┐            ┌──────────────┐
│ JSONAdapter  │            │ MemoryAdapter│
│  (JSON)      │            │  (In-Memory) │
└──────────────┘            └──────────────┘
    │                               │
    └───────────────┬───────────────┘
                    │
                    ▼
         ┌──────────────────┐
         │ DatabaseFactory  │
         │ (Factory Pattern) │
         └──────────────────┘
```

## Design Patterns Used

### 1. **Repository Pattern**
- `DatabaseInterface`: Abstract repository defining all operations
- Concrete implementations: `JSONAdapter`, `MemoryAdapter`
- Business logic depends only on the interface

### 2. **Strategy Pattern**
- Different database strategies can be swapped at runtime
- Selected via `DATABASE_TYPE` environment variable

### 3. **Factory Pattern**
- `DatabaseFactory`: Creates appropriate adapter based on config
- Handles initialization automatically

### 4. **Dependency Inversion Principle (SOLID)**
- High-level modules (business logic) don't depend on low-level modules (database)
- Both depend on abstractions (`DatabaseInterface`)

## How to Switch Databases

### Option 1: JSON (Local Demos - Recommended)

```bash
export DATABASE_TYPE=json
export JSON_DB_PATH=./data/json_db  # Optional
```

**Perfect for local demos!** Stores all data in JSON files. Data persists between restarts, easy to inspect and debug.

### Option 2: Memory (Testing Only)

```bash
export DATABASE_TYPE=memory
```

**For testing only!** Stores all data in-memory using Python dicts/lists. Data is lost on restart (on-demand, no persistence).

**No code changes needed!** Just change the environment variable.

## Adding a New Database

To add PostgreSQL, Redis, or any other database:

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
```

**Done!** Business logic remains unchanged.

## Benefits

✅ **Zero Business Logic Changes** - Switch databases with one env var  
✅ **Easy to Extend** - Add new databases by implementing interface  
✅ **Testable** - Mock DatabaseInterface for unit tests  
✅ **Demo Ready** - Use JSON for demos, Memory for testing  
✅ **SOLID Principles** - Follows best practices  

## File Structure

```
backend/app/services/database/
├── __init__.py              # Exports
├── base.py                  # DatabaseInterface (abstract)
├── json_adapter.py          # JSON implementation (demos)
├── memory_adapter.py        # In-memory implementation (testing)
├── factory.py               # DatabaseFactory
└── README.md               # Documentation
```

## Current Status

- ✅ Abstract interface defined
- ✅ JSON adapter implemented (file-based JSON, persistent, perfect for demos)
- ✅ Memory adapter implemented (in-memory, non-persistent, for testing)
- ✅ Factory pattern implemented
- ✅ Business logic updated to use interface
- ✅ Configuration system in place

## Next Steps

1. Set `DATABASE_TYPE` environment variable (`json` or `memory`)
2. Start backend - database initializes automatically
3. Switch databases anytime by changing env var!

## Example Usage

```python
# Business logic (documents.py)
from ..services.database import DatabaseFactory

# Initialize (handled automatically on startup)
db_service = await DatabaseFactory.create_and_initialize()

# Use database (same code for all databases)
doc = await db_service.create_document({...})
docs = await db_service.get_all_documents(folder="folder1")
await db_service.update_document(doc_id, {...})
```

**The same code works with JSON, Memory, PostgreSQL, or any future database!**

## JSON Adapter (Recommended for Local Demos)

The JSON adapter is perfect for:
- **Local Demos** - No database setup required, data persists
- **Development** - Easy to inspect and debug
- **Testing** - Can easily reset by deleting JSON files
- **Portable** - Just copy JSON files to move data

### Features:
- ✅ Stores data in JSON files (human-readable)
- ✅ Data persists between restarts
- ✅ Easy to inspect (`data/json_db/documents.json` and `folders.json`)
- ✅ Easy to backup (just copy the `json_db` folder)
- ✅ Virtual file system support (folders, documents)
- ✅ Zero configuration needed
- ✅ Fast performance (in-memory with periodic saves)

### Usage:
```bash
# Set environment variable
export DATABASE_TYPE=json

# Optional: specify custom data directory
export JSON_DB_PATH=./data/json_db

# Start backend - works immediately!
python main.py
```

### Data Storage:
- Documents: `data/json_db/documents.json`
- Folders: `data/json_db/folders.json`

You can open these files in any text editor to see your data!

## Memory Adapter (Testing Only)

The memory adapter is for:
- **Quick Testing** - Fast, isolated test runs
- **Prototyping** - No persistence needed

### Features:
- ✅ Stores data in-memory using Python dictionaries/lists
- ✅ On-demand (data lost on restart)
- ✅ Zero configuration needed
- ✅ Fast performance (no I/O overhead)

### Usage:
```bash
export DATABASE_TYPE=memory
python main.py
```

All virtual file system operations work exactly the same across all database types!
