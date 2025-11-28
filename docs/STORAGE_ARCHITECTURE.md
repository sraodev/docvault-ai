# File Storage Architecture - Plug-and-Play Design Pattern

## Overview

DocVault AI uses a **plug-and-play file storage architecture** that allows switching between different storage backends (Local filesystem, S3, Supabase Storage) **without changing any business logic**.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  Business Logic Layer                    │
│  (documents.py, FileService, etc.)                     │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ Uses
                     ▼
┌─────────────────────────────────────────────────────────┐
│          FileStorageInterface (Abstract)                │
│  - save_file()                                          │
│  - get_file()                                           │
│  - delete_file()                                        │
│  - file_exists()                                        │
│  - get_file_url()                                       │
│  - save_text()                                          │
│  - get_text()                                           │
└───────┬───────────────────────────────┬─────────────────┘
        │                               │
        │ Implements                    │ Implements
        ▼                               ▼
┌──────────────────┐          ┌──────────────────┐
│ LocalFileStorage  │          │   S3FileStorage  │
│  (Local FS)       │          │   (AWS S3)       │
└──────────────────┘          └──────────────────┘
        │                               │
        └───────────┬───────────────────┘
                    │
                    ▼
        ┌───────────────────────┐
        │   FileStorageFactory   │
        │   (Factory Pattern)    │
        └───────────────────────┘
                    │
                    ▼
        ┌───────────────────────┐
        │ SupabaseFileStorage   │
        │  (Supabase Storage)   │
        └───────────────────────┘
```

## Design Patterns Used

### 1. Repository Pattern
- **FileStorageInterface**: Abstract interface defining all storage operations
- **Concrete Adapters**: LocalFileStorage, S3FileStorage, SupabaseFileStorage implement the interface
- **Business Logic**: Depends only on FileStorageInterface, not concrete implementations

### 2. Strategy Pattern
- Different storage strategies can be swapped at runtime
- Selected via `STORAGE_TYPE` environment variable
- No code changes needed to switch storage backends

### 3. Factory Pattern
- **FileStorageFactory**: Creates appropriate storage adapter based on configuration
- Handles initialization automatically
- Single point of storage creation

### 4. Dependency Inversion Principle (SOLID)
- High-level modules (business logic) don't depend on low-level modules (storage)
- Both depend on abstractions (`FileStorageInterface`)

## Available Storage Backends

### LocalFileStorage (Default)
- **Type**: Local filesystem storage
- **Persistence**: Yes (files stored on disk)
- **Storage**: `backend/uploads/` (configurable)
- **Best for**: Development, demos, single-server deployments
- **Setup**: Zero configuration needed

### S3FileStorage (Production)
- **Type**: AWS S3 storage
- **Persistence**: Yes (files stored in S3 buckets)
- **Storage**: S3 bucket (configurable)
- **Best for**: Production, scalable deployments, multi-server setups
- **Setup**: Requires AWS credentials and bucket

### SupabaseFileStorage (Production Alternative)
- **Type**: Supabase Storage
- **Persistence**: Yes (files stored in Supabase buckets)
- **Storage**: Supabase Storage bucket (configurable)
- **Best for**: Production, Supabase-based deployments
- **Setup**: Requires Supabase URL and key

## How to Switch Storage

### Option 1: Local Filesystem (Default)

```bash
export STORAGE_TYPE=local
export LOCAL_STORAGE_DIR=./uploads  # Optional, defaults to backend/uploads

# Start backend
python main.py
```

**Use when:** Development, demos, single-server deployments

### Option 2: AWS S3 (Production)

```bash
export STORAGE_TYPE=s3
export S3_BUCKET_NAME=my-docvault-bucket
export AWS_ACCESS_KEY_ID=your-access-key
export AWS_SECRET_ACCESS_KEY=your-secret-key
export AWS_REGION=us-east-1  # Optional, defaults to us-east-1
export S3_ENDPOINT_URL=  # Optional, for S3-compatible services (MinIO, etc.)

# Start backend
python main.py
```

**Use when:** Production, scalable deployments, multi-server setups

**Note:** You can also use IAM roles instead of access keys (leave AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY unset).

### Option 3: Supabase Storage (Production Alternative)

```bash
export STORAGE_TYPE=supabase
export SUPABASE_URL=https://your-project.supabase.co
export SUPABASE_KEY=your-service-role-key
export SUPABASE_STORAGE_BUCKET=files  # Optional, defaults to "files"

# Start backend
python main.py
```

**Use when:** Production, Supabase-based deployments

**No code changes needed!** Just change the environment variable.

## Benefits

✅ **Zero Business Logic Changes** - Switch storage with one env var  
✅ **Easy to Extend** - Add new storage backends by implementing interface  
✅ **Testable** - Mock FileStorageInterface for unit tests  
✅ **Production Ready** - S3 and Supabase for production, Local for dev  
✅ **SOLID Principles** - Follows best practices  

## Adding a New Storage Backend

### Step 1: Create Adapter

```python
# backend/app/services/storage/azure_storage.py
from .base import FileStorageInterface

class AzureFileStorage(FileStorageInterface):
    async def save_file(self, file: UploadFile, file_path: str) -> str:
        # Azure Blob Storage implementation
        pass
    
    # Implement all other methods from FileStorageInterface
    ...
```

### Step 2: Update Factory

```python
# backend/app/services/storage/factory.py
elif storage_type == "azure":
    return FileStorageFactory._create_azure(**kwargs)
```

### Step 3: Use It

```bash
export STORAGE_TYPE=azure
export AZURE_CONNECTION_STRING=...
```

**Done!** Business logic remains unchanged.

## File Structure

```
backend/app/services/storage/
├── __init__.py              # Exports
├── base.py                  # FileStorageInterface (abstract)
├── local_storage.py          # Local filesystem implementation
├── s3_storage.py            # AWS S3 implementation
├── supabase_storage.py      # Supabase Storage implementation
├── factory.py               # FileStorageFactory
└── migrate_storage.py        # Storage migration utility
```

## Current Status

- ✅ Abstract interface defined (`FileStorageInterface`)
- ✅ Local adapter implemented (filesystem, default)
- ✅ S3 adapter implemented (AWS S3, production-ready)
- ✅ Supabase adapter implemented (Supabase Storage, production-ready)
- ✅ Factory pattern implemented
- ✅ FileService updated to use interface
- ✅ Configuration system in place
- ✅ **Migration utility** - Easy migration between storage backends

## Example Usage

```python
# Business logic (FileService)
from ..services.storage import FileStorageFactory

# Initialize (handled automatically)
storage = await FileStorageFactory.create_and_initialize()

# Use storage (same code for all backends)
await storage.save_file(upload_file, "documents/file.pdf")
file_bytes = await storage.get_file("documents/file.pdf")
await storage.delete_file("documents/file.pdf")
url = await storage.get_file_url("documents/file.pdf", expires_in=3600)
```

**The same code works with Local, S3, Supabase, or any future storage backend!**

## Storage Features

All storage adapters support:
- ✅ File upload and storage
- ✅ File retrieval (as bytes)
- ✅ File deletion
- ✅ File existence checking
- ✅ URL generation (signed URLs for S3/Supabase)
- ✅ Text content storage/retrieval
- ✅ Async operations

## Migration Guide

### Easy Migration Between Storage Backends

**Migrate files between any storage backends with one command!**

#### Quick Migration

```bash
# Local → S3
python -m app.services.storage.migrate_storage local s3

# Local → Supabase
python -m app.services.storage.migrate_storage local supabase

# S3 → Supabase
python -m app.services.storage.migrate_storage s3 supabase

# Any combination works!
```

#### Dry Run (Preview)

```bash
# Preview what would be migrated
python -m app.services.storage.migrate_storage local s3 --dry-run
```

#### Complete Migration Process

1. **Set credentials** for destination storage
2. **Run migration** command
3. **Update `.env`** with new `STORAGE_TYPE`
4. **Restart backend**

**That's it!** All files are migrated automatically.

See [STORAGE_MIGRATION_GUIDE.md](./STORAGE_MIGRATION_GUIDE.md) for detailed instructions.

### Manual Migration (Legacy)

If you prefer manual migration:

1. Set up destination storage (S3 bucket or Supabase Storage)
2. Set `STORAGE_TYPE` and required env vars
3. Restart backend
4. Re-upload files or use migration utility

## Best Practices

1. **Always use FileStorageInterface**: Never import concrete adapters in business logic
2. **Use Factory**: Let FileStorageFactory handle creation
3. **Environment-based config**: Use environment variables for storage selection
4. **Initialize on startup**: Storage is initialized automatically in FileService
5. **Handle errors**: Storage adapters handle their own errors appropriately
6. **Use signed URLs**: For S3/Supabase, use `get_file_url()` for direct access instead of proxying through backend

## Production Recommendations

- **S3**: Use for AWS-based deployments, high scalability needs
- **Supabase Storage**: Use for Supabase-based deployments, simpler setup
- **Local**: Only for development/demos, not recommended for production

All storage backends provide the same interface, so you can switch anytime!

