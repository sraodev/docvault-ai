# Storage Migration Guide

## Overview

Easily migrate files between storage backends:
- **Local → S3**
- **Local → Supabase**
- **S3 → Local**
- **S3 → Supabase**
- **Supabase → Local**
- **Supabase → S3**

The migration utility handles all file types (text and binary) and preserves file paths.

## Quick Start

### 1. Set Environment Variables

#### For S3 Migration

```bash
# Source (if migrating FROM S3)
export S3_BUCKET_NAME=your-source-bucket
export AWS_ACCESS_KEY_ID=your-access-key
export AWS_SECRET_ACCESS_KEY=your-secret-key
export AWS_REGION=us-east-1

# Destination (if migrating TO S3)
export S3_BUCKET_NAME=your-dest-bucket
export AWS_ACCESS_KEY_ID=your-access-key
export AWS_SECRET_ACCESS_KEY=your-secret-key
export AWS_REGION=us-east-1
```

#### For Supabase Migration

```bash
# Source (if migrating FROM Supabase)
export SUPABASE_URL=https://your-project.supabase.co
export SUPABASE_KEY=your-service-role-key
export SUPABASE_STORAGE_BUCKET=files

# Destination (if migrating TO Supabase)
export SUPABASE_URL=https://your-project.supabase.co
export SUPABASE_KEY=your-service-role-key
export SUPABASE_STORAGE_BUCKET=files
```

#### For Local Storage

```bash
# Optional: specify custom directory
export LOCAL_STORAGE_DIR=/path/to/uploads
```

### 2. Run Migration

#### Basic Migration

```bash
cd backend
python -m app.services.storage.migrate_storage local s3
```

#### Dry Run (Preview)

```bash
python -m app.services.storage.migrate_storage local s3 --dry-run
```

#### Update Database References

```bash
python -m app.services.storage.migrate_storage local s3 --update-db
```

## Migration Examples

### Example 1: Local → S3

```bash
# Set S3 credentials
export S3_BUCKET_NAME=docvault-files
export AWS_ACCESS_KEY_ID=AKIA...
export AWS_SECRET_ACCESS_KEY=...
export AWS_REGION=us-east-1

# Run migration
python -m app.services.storage.migrate_storage local s3
```

### Example 2: S3 → Supabase

```bash
# Set Supabase credentials
export SUPABASE_URL=https://xxx.supabase.co
export SUPABASE_KEY=eyJ...
export SUPABASE_STORAGE_BUCKET=files

# Run migration
python -m app.services.storage.migrate_storage s3 supabase
```

### Example 3: Supabase → Local

```bash
# Set local storage directory (optional)
export LOCAL_STORAGE_DIR=./backup-uploads

# Run migration
python -m app.services.storage.migrate_storage supabase local
```

## Migration Process

The migration utility:

1. **Scans Database** - Reads all documents from your database
2. **Extracts File Paths** - Gets file paths from document metadata
3. **Reads from Source** - Downloads files from source storage
4. **Writes to Destination** - Uploads files to destination storage
5. **Verifies Migration** - Checks that files exist in destination
6. **Reports Statistics** - Shows migration results

## Features

### ✅ **Automatic File Detection**
- Scans database for all file paths
- Handles both text and binary files
- Preserves file paths and metadata

### ✅ **Progress Reporting**
- Shows progress for each file
- Displays migration statistics
- Reports errors and skipped files

### ✅ **Dry Run Mode**
- Preview what would be migrated
- No actual file transfer
- Safe to test before migrating

### ✅ **Error Handling**
- Continues on individual file errors
- Reports all errors at the end
- Skips files that already exist

### ✅ **Verification**
- Verifies all files were migrated
- Checks file existence in destination
- Reports missing files

## Migration Statistics

After migration, you'll see:

```
📊 Migration Statistics:
   Total files: 150
   ✅ Migrated: 148
   ⏭️  Skipped: 1
   ❌ Failed: 1
```

## Common Scenarios

### Scenario 1: Moving to Production (Local → S3)

```bash
# 1. Set up S3 bucket
aws s3 mb s3://docvault-production

# 2. Configure credentials
export S3_BUCKET_NAME=docvault-production
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...

# 3. Run migration
python -m app.services.storage.migrate_storage local s3

# 4. Update .env
echo "STORAGE_TYPE=s3" >> .env
```

### Scenario 2: Backup to Local (S3 → Local)

```bash
# 1. Set local backup directory
export LOCAL_STORAGE_DIR=./backup-$(date +%Y%m%d)

# 2. Run migration
python -m app.services.storage.migrate_storage s3 local
```

### Scenario 3: Switching Providers (S3 → Supabase)

```bash
# 1. Set Supabase credentials
export SUPABASE_URL=https://xxx.supabase.co
export SUPABASE_KEY=...
export SUPABASE_STORAGE_BUCKET=files

# 2. Dry run first
python -m app.services.storage.migrate_storage s3 supabase --dry-run

# 3. Run actual migration
python -m app.services.storage.migrate_storage s3 supabase

# 4. Update .env
echo "STORAGE_TYPE=supabase" >> .env
```

## Troubleshooting

### Error: "Bucket does not exist"

**S3:**
```bash
# Create bucket first
aws s3 mb s3://your-bucket-name
```

**Supabase:**
```bash
# Create bucket in Supabase Dashboard
# Storage → Create Bucket → Name: files
```

### Error: "Access denied"

**S3:**
- Check IAM permissions
- Verify AWS credentials
- Ensure bucket policy allows access

**Supabase:**
- Use service role key (not anon key)
- Check RLS policies
- Verify bucket exists

### Error: "File not found"

- Files may have been deleted from source
- Check file paths in database
- Verify source storage is accessible

### Error: "Migration failed"

- Check network connection
- Verify credentials
- Check storage quotas
- Review error messages in output

## Best Practices

### 1. **Always Dry Run First**

```bash
python -m app.services.storage.migrate_storage local s3 --dry-run
```

### 2. **Backup Before Migration**

```bash
# Backup database
cp -r data/json_db data/json_db.backup

# Backup local files
tar -czf uploads-backup.tar.gz uploads/
```

### 3. **Test After Migration**

```bash
# Verify files are accessible
python -m app.services.storage.migrate_storage s3 local --dry-run
```

### 4. **Update Configuration**

After migration, update your `.env`:

```env
STORAGE_TYPE=s3  # or supabase
```

### 5. **Monitor Storage Usage**

- Check S3 bucket size
- Monitor Supabase storage quota
- Verify file counts match

## Performance Tips

### Large Migrations

For large migrations (10,000+ files):

1. **Run in batches** - Migrate by folder
2. **Use parallel uploads** - S3/Supabase support concurrent uploads
3. **Monitor progress** - Check statistics regularly
4. **Handle errors** - Review error log

### Network Optimization

- Use same region for S3 (faster)
- Use CDN for Supabase (faster downloads)
- Compress files before migration (optional)

## After Migration

### 1. Verify Files

```bash
# Check file count
python -c "
from app.services.storage import FileStorageFactory
import asyncio
async def check():
    storage = await FileStorageFactory.create_and_initialize('s3')
    # List files or check count
asyncio.run(check())
"
```

### 2. Update Application

Update `.env`:

```env
STORAGE_TYPE=s3  # or supabase
```

### 3. Test Application

- Upload a test file
- Download a test file
- Verify file serving works

### 4. Clean Up (Optional)

After verifying migration:

```bash
# Remove old local files (if migrated to cloud)
rm -rf uploads/*
```

## Migration Script Reference

### Command Syntax

```bash
python -m app.services.storage.migrate_storage <source> <dest> [options]
```

### Options

- `--dry-run` - Preview migration without transferring files
- `--update-db` - Update database references after migration

### Storage Types

- `local` - Local filesystem storage
- `s3` - AWS S3 storage
- `supabase` - Supabase Storage

## Conclusion

The storage migration utility makes it easy to:

✅ **Switch storage providers** without code changes  
✅ **Backup files** to different storage  
✅ **Move to production** seamlessly  
✅ **Test migrations** with dry-run mode  

All migrations preserve file paths and metadata, making the process transparent to your application!

