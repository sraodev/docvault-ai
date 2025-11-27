# Quick Guide: Switching Between Databases

DocVault AI supports **two database backends** that can be switched instantly with a single environment variable change.

## Available Databases

1. **JSON** - Local demos, file-based JSON, persistent (recommended for demos)
2. **Memory** - Testing, in-memory, non-persistent

## How to Switch

### Option 1: JSON (Local Demos - Recommended)

```bash
export DATABASE_TYPE=json
export JSON_DB_PATH=./data/json_db  # Optional, defaults to backend/data/json_db

# Start backend
python main.py
```

**Use when:** Local demos, want persistence, easy to inspect/debug, no database setup needed

**Benefits:**
- ✅ Data persists between restarts
- ✅ Easy to inspect (just look at JSON files)
- ✅ No database setup required
- ✅ Perfect for demos and local development
- ✅ Human-readable JSON format

### Option 2: Memory (Testing Only)

```bash
export DATABASE_TYPE=memory

# Start backend
python main.py
```

**Use when:** Quick testing, no persistence needed, data lost on restart

---

## Quick Switch Examples

### Switch from Memory to JSON (save data)
```bash
# Stop backend (Ctrl+C)
export DATABASE_TYPE=json
python main.py  # Creates JSON files, starts fresh
```

### Switch from JSON to Memory (testing)
```bash
# Stop backend
export DATABASE_TYPE=memory
python main.py  # Starts fresh with empty in-memory database
```

## Important Notes

⚠️ **Data Persistence:**
- **JSON**: Data persists in JSON files (`data/json_db/documents.json` and `folders.json`)
- **Memory**: Data is **lost on restart** (on-demand, non-persistent)

⚠️ **Switching Databases:**
- Each database has its own storage
- Switching databases means starting with a fresh/empty database
- Data from one database doesn't automatically migrate to another

## Verification

After starting the backend, check the console output:

```
🔌 Initializing database: json
✅ Database initialized: json
ℹ️  JSON database: No migrations needed (file-based JSON storage)
```

or

```
🔌 Initializing database: memory
✅ Database initialized: memory
ℹ️  Memory database: No migrations needed (in-memory, no persistence)
```

## All Features Work the Same

Regardless of which database you use:
- ✅ File uploads
- ✅ Virtual folders
- ✅ Document management
- ✅ Checksum deduplication
- ✅ AI processing
- ✅ Bulk uploads

**The same code works with both databases!**

## JSON Database Details

The JSON adapter stores data in two files:
- `data/json_db/documents.json` - All document metadata
- `data/json_db/folders.json` - All folder metadata

You can:
- **Inspect data**: Open JSON files in any text editor
- **Backup data**: Copy the `json_db` folder
- **Reset data**: Delete JSON files (fresh start)
- **Debug easily**: See exactly what's stored

Perfect for demos because you can show the data structure easily!
