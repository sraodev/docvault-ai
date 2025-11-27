# Database Switching Guide

## Quick Switch Between Databases

### Switch to MongoDB (Production)

```bash
# Set environment variable
export DATABASE_TYPE=mongodb
export MONGODB_CONNECTION_STRING=mongodb://localhost:27017/
export MONGODB_DB_NAME=docvault

# Start backend
cd backend && python main.py
```

### Switch to SQLite (Development)

```bash
# Set environment variable
export DATABASE_TYPE=sqlite
export SQLITE_DB_PATH=./data/docvault.db

# Start backend
cd backend && python main.py
```

**That's it!** No code changes needed.

## How It Works

1. **Factory Pattern**: `DatabaseFactory` creates the appropriate adapter
2. **Abstract Interface**: All business logic uses `DatabaseInterface`
3. **Configuration**: Database type selected via `DATABASE_TYPE` env var
4. **Zero Changes**: Business logic never touches concrete database code

## Example: Adding PostgreSQL

Want to add PostgreSQL support? Just:

1. Create `PostgreSQLAdapter(DatabaseInterface)`
2. Implement all abstract methods
3. Add to `DatabaseFactory`
4. Set `DATABASE_TYPE=postgresql`

**No business logic changes required!**

