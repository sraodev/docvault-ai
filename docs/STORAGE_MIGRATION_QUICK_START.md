# Storage Migration Quick Start

## 🚀 One-Command Migration

### Local → S3

```bash
# 1. Set S3 credentials
export S3_BUCKET_NAME=your-bucket
export AWS_ACCESS_KEY_ID=your-key
export AWS_SECRET_ACCESS_KEY=your-secret

# 2. Migrate
cd backend
python -m app.services.storage.migrate_storage local s3
```

### Local → Supabase

```bash
# 1. Set Supabase credentials
export SUPABASE_URL=https://xxx.supabase.co
export SUPABASE_KEY=your-key
export SUPABASE_STORAGE_BUCKET=files

# 2. Migrate
cd backend
python -m app.services.storage.migrate_storage local supabase
```

### S3 → Supabase

```bash
# 1. Set both credentials
export S3_BUCKET_NAME=source-bucket
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...

export SUPABASE_URL=https://xxx.supabase.co
export SUPABASE_KEY=...
export SUPABASE_STORAGE_BUCKET=files

# 2. Migrate
python -m app.services.storage.migrate_storage s3 supabase
```

## 📋 All Migration Paths

| From → To | Command |
|-----------|---------|
| Local → S3 | `python -m app.services.storage.migrate_storage local s3` |
| Local → Supabase | `python -m app.services.storage.migrate_storage local supabase` |
| S3 → Local | `python -m app.services.storage.migrate_storage s3 local` |
| S3 → Supabase | `python -m app.services.storage.migrate_storage s3 supabase` |
| Supabase → Local | `python -m app.services.storage.migrate_storage supabase local` |
| Supabase → S3 | `python -m app.services.storage.migrate_storage supabase s3` |

## 🔍 Dry Run (Preview)

```bash
python -m app.services.storage.migrate_storage local s3 --dry-run
```

## ✅ After Migration

Update `.env`:

```env
STORAGE_TYPE=s3  # or supabase
```

That's it! Your application will now use the new storage automatically.

## 📚 Full Documentation

See [STORAGE_MIGRATION_GUIDE.md](./STORAGE_MIGRATION_GUIDE.md) for detailed instructions.

