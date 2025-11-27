# Database Abstraction Layer

This module provides a plug-and-play database abstraction layer using the **Repository Pattern** and **Strategy Pattern**.

## Architecture

```
DatabaseInterface (Abstract)
    ├── JSONAdapter (file-based JSON, persistent)
    ├── MemoryAdapter (in-memory, non-persistent)
    └── [Future: PostgreSQLAdapter, RedisAdapter, etc.]
```

## Usage

### Basic Usage

```python
from app.services.database import DatabaseFactory

# Create database adapter (auto-detects from DATABASE_TYPE env var)
db = await DatabaseFactory.create_and_initialize()

# Use database (same API for all databases)
doc = await db.create_document({...})
docs = await db.get_all_documents(folder="folder1")
```

### Configuration

Set `DATABASE_TYPE` environment variable:

```bash
# JSON (file-based, persistent) - Recommended for demos
export DATABASE_TYPE=json

# Memory (in-memory, non-persistent) - For testing
export DATABASE_TYPE=memory
```

## Available Databases

### JSON Adapter
- **Type**: `json`
- **Storage**: JSON files (`data/json_db/documents.json` and `folders.json`)
- **Persistence**: Yes (data survives restarts)
- **Best for**: Local demos, development, easy debugging

### Memory Adapter
- **Type**: `memory`
- **Storage**: In-memory Python dictionaries
- **Persistence**: No (data lost on restart)
- **Best for**: Testing, quick prototyping

## Adding a New Database

1. Create adapter class inheriting from `DatabaseInterface`
2. Implement all abstract methods
3. Add to `DatabaseFactory`
4. Done! No business logic changes needed.

See `DATABASE_ARCHITECTURE.md` for detailed guide.
