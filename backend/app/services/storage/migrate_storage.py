"""
Storage Migration Utility

Easily migrate files between storage backends:
- Local → S3
- Local → Supabase
- S3 → Local
- S3 → Supabase
- Supabase → Local
- Supabase → S3

Usage:
    python -m app.services.storage.migrate_storage local s3
    python -m app.services.storage.migrate_storage s3 supabase
"""
import asyncio
import sys
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

from .factory import FileStorageFactory
from ...services.database import DatabaseFactory
from ...core.config import DATABASE_TYPE, JSON_DB_PATH, STORAGE_TYPE


class StorageMigrator:
    """Migrate files between storage backends."""
    
    def __init__(
        self,
        source_type: str,
        dest_type: str,
        source_config: Optional[Dict] = None,
        dest_config: Optional[Dict] = None
    ):
        """
        Initialize storage migrator.
        
        Args:
            source_type: Source storage type ('local', 's3', 'supabase')
            dest_type: Destination storage type ('local', 's3', 'supabase')
            source_config: Optional source storage configuration
            dest_config: Optional destination storage configuration
        """
        self.source_type = source_type.lower()
        self.dest_type = dest_type.lower()
        self.source_config = source_config or {}
        self.dest_config = dest_config or {}
        
        self.source_storage = None
        self.dest_storage = None
        self.db_service = None
        
        # Statistics
        self.stats = {
            "total_files": 0,
            "migrated": 0,
            "skipped": 0,
            "failed": 0,
            "errors": []
        }
    
    async def initialize(self):
        """Initialize source and destination storage."""
        logger.info(f"🔌 Initializing storage...")
        
        # Initialize source storage
        logger.debug(f"   📥 Source: {self.source_type}")
        self.source_storage = await FileStorageFactory.create_and_initialize(
            self.source_type,
            **self.source_config
        )
        
        # Initialize destination storage
        logger.debug(f"   📤 Destination: {self.dest_type}")
        self.dest_storage = await FileStorageFactory.create_and_initialize(
            self.dest_type,
            **self.dest_config
        )
        
        # Initialize database
        logger.info(f"   💾 Database: {DATABASE_TYPE}")
        data_dir = Path(JSON_DB_PATH) if JSON_DB_PATH else None
        self.db_service = await DatabaseFactory.create_and_initialize(
            DATABASE_TYPE,
            data_dir=data_dir
        )
        
        logger.info(f"✅ Storage initialized")
    
    async def get_all_file_paths(self) -> List[Dict]:
        """Get all file paths from database."""
        documents = await self.db_service.get_all_documents()
        
        file_paths = []
        for doc in documents:
            # Get file path from document metadata
            file_path = doc.get("file_path") or doc.get("path") or doc.get("filename")
            if file_path:
                file_paths.append({
                    "doc_id": doc.get("id"),
                    "file_path": file_path,
                    "filename": doc.get("filename", ""),
                    "size": doc.get("size", 0)
                })
        
        return file_paths
    
    async def migrate_file(self, file_info: Dict) -> bool:
        """
        Migrate a single file from source to destination storage.
        
        Args:
            file_info: Dictionary with doc_id, file_path, filename, size
        
        Returns:
            True if successful, False otherwise
        """
        file_path = file_info["file_path"]
        doc_id = file_info["doc_id"]
        
        try:
            # Check if file exists in source
            if not await self.source_storage.file_exists(file_path):
                logger.warning(f"   ⚠️  File not found in source: {file_path}")
                self.stats["skipped"] += 1
                return False
            
            # Check if file already exists in destination
            if await self.dest_storage.file_exists(file_path):
                logger.info(f"   ⏭️  File already exists in destination: {file_path}")
                self.stats["skipped"] += 1
                return True
            
            # Read file from source
            logger.debug(f"   📥 Reading: {file_path}")
            file_content = await self.source_storage.get_file(file_path)
            
            # Write file to destination
            logger.debug(f"   📤 Writing: {file_path}")
            # Save bytes to storage (works for both text and binary files)
            await self._save_bytes_to_storage(self.dest_storage, file_content, file_path)
            
            # Verify file was written
            if await self.dest_storage.file_exists(file_path):
                logger.info(f"   ✅ Migrated: {file_path}")
                self.stats["migrated"] += 1
                return True
            else:
                logger.error(f"   ❌ Verification failed: {file_path}")
                self.stats["failed"] += 1
                return False
        
        except Exception as e:
            error_msg = f"Error migrating {file_path}: {str(e)}"
            logger.error(f"   ❌ {error_msg}")
            self.stats["failed"] += 1
            self.stats["errors"].append({
                "file_path": file_path,
                "doc_id": doc_id,
                "error": str(e)
            })
            return False
    
    async def _save_bytes_to_storage(self, storage, content: bytes, file_path: str):
        """Save bytes to storage (works for both text and binary files)."""
        # Import here to avoid circular imports
        from fastapi import UploadFile
        from io import BytesIO
        
        # Create a mock UploadFile from bytes
        file_obj = BytesIO(content)
        
        # Determine content type from file extension
        filename = file_path.split('/')[-1]
        content_type = self._get_content_type(filename)
        
        upload_file = UploadFile(
            filename=filename,
            file=file_obj,
            headers={"content-type": content_type}
        )
        
        # Reset file pointer to beginning
        file_obj.seek(0)
        
        await storage.save_file(upload_file, file_path)
    
    def _get_content_type(self, filename: str) -> str:
        """Get content type from filename extension."""
        ext = filename.split('.')[-1].lower() if '.' in filename else ''
        
        content_types = {
            'pdf': 'application/pdf',
            'txt': 'text/plain',
            'md': 'text/markdown',
            'json': 'application/json',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'gif': 'image/gif',
            'doc': 'application/msword',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'xls': 'application/vnd.ms-excel',
            'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        }
        
        return content_types.get(ext, 'application/octet-stream')
    
    async def migrate_all(self, update_database: bool = False, dry_run: bool = False):
        """
        Migrate all files from source to destination storage.
        
        Args:
            update_database: If True, update database references after migration
            dry_run: If True, only show what would be migrated without actually migrating
        """
        logger.info(f"\n🚀 Starting migration: {self.source_type} → {self.dest_type}")
        if dry_run:
            logger.warning(f"   ⚠️  DRY RUN MODE - No files will be migrated")
        
        # Get all file paths
        logger.info(f"\n📋 Scanning database for files...")
        file_paths = await self.get_all_file_paths()
        self.stats["total_files"] = len(file_paths)
        
        logger.info(f"   Found {len(file_paths)} files to migrate")
        
        if not file_paths:
            logger.info("   ✅ No files to migrate")
            return
        
        # Migrate files
        logger.info(f"\n📦 Migrating files...")
        for i, file_info in enumerate(file_paths, 1):
            logger.info(f"\n[{i}/{len(file_paths)}] {file_info['filename']} ({file_info['file_path']})")
            
            if not dry_run:
                await self.migrate_file(file_info)
            else:
                # Dry run - just check if file exists
                exists = await self.source_storage.file_exists(file_info["file_path"])
                if exists:
                    logger.info(f"   ✅ Would migrate: {file_info['file_path']}")
                    self.stats["migrated"] += 1
                else:
                    logger.warning(f"   ⚠️  File not found: {file_info['file_path']}")
                    self.stats["skipped"] += 1
        
        # Print statistics
        self._print_statistics()
        
        # Update database if requested
        if update_database and not dry_run:
            logger.info(f"\n💾 Updating database references...")
            # Database references should remain the same (file_path doesn't change)
            # But we can verify all files are accessible
            await self._verify_migration()
    
    async def _verify_migration(self):
        """Verify all migrated files are accessible."""
        logger.info(f"   🔍 Verifying migrated files...")
        
        file_paths = await self.get_all_file_paths()
        verified = 0
        failed = 0
        
        for file_info in file_paths:
            file_path = file_info["file_path"]
            if await self.dest_storage.file_exists(file_path):
                verified += 1
            else:
                failed += 1
                logger.error(f"   ❌ File not found in destination: {file_path}")
        
        logger.info(f"   ✅ Verified: {verified}/{len(file_paths)} files")
        if failed > 0:
            logger.error(f"   ⚠️  Failed: {failed} files")
    
    def _print_statistics(self):
        """Print migration statistics."""
        logger.info(f"\n📊 Migration Statistics:")
        logger.info(f"   Total files: {self.stats['total_files']}")
        logger.info(f"   ✅ Migrated: {self.stats['migrated']}")
        logger.warning(f"   ⏭️  Skipped: {self.stats['skipped']}")
        logger.error(f"   ❌ Failed: {self.stats['failed']}")
        
        if self.stats["errors"]:
            logger.error(f"\n❌ Errors ({len(self.stats['errors'])}):")
            for error in self.stats["errors"][:10]:  # Show first 10 errors
                logger.error(f"   - {error['file_path']}: {error['error']}")
            if len(self.stats["errors"]) > 10:
                logger.error(f"   ... and {len(self.stats['errors']) - 10} more errors")
    
    async def close(self):
        """Close storage connections."""
        if self.source_storage:
            await self.source_storage.close()
        if self.dest_storage:
            await self.dest_storage.close()
        if self.db_service:
            await self.db_service.close()


def get_storage_config(storage_type: str) -> Dict:
    """Get storage configuration from environment or user input."""
    import os
    
    config = {}
    
    if storage_type == "s3":
        config = {
            "bucket_name": os.getenv("S3_BUCKET_NAME"),
            "aws_access_key_id": os.getenv("AWS_ACCESS_KEY_ID"),
            "aws_secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY"),
            "region_name": os.getenv("AWS_REGION", "us-east-1"),
            "endpoint_url": os.getenv("S3_ENDPOINT_URL")
        }
    elif storage_type == "supabase":
        config = {
            "supabase_url": os.getenv("SUPABASE_URL"),
            "supabase_key": os.getenv("SUPABASE_KEY"),
            "bucket_name": os.getenv("SUPABASE_STORAGE_BUCKET", "files")
        }
    elif storage_type == "local":
        config = {
            "base_dir": os.getenv("LOCAL_STORAGE_DIR")
        }
    
    return config


async def main():
    """Main migration function."""
    import os
    
    # Parse command line arguments
    if len(sys.argv) < 3:
        logger.info("Usage: python -m app.services.storage.migrate_storage <source> <dest> [--dry-run] [--update-db]")
        logger.info("\nExamples:")
        logger.info("  python -m app.services.storage.migrate_storage local s3")
        logger.info("  python -m app.services.storage.migrate_storage s3 supabase --dry-run")
        logger.info("  python -m app.services.storage.migrate_storage local supabase --update-db")
        logger.info("\nSupported storage types: local, s3, supabase")
        return
    
    source_type = sys.argv[1].lower()
    dest_type = sys.argv[2].lower()
    dry_run = "--dry-run" in sys.argv
    update_db = "--update-db" in sys.argv
    
    # Validate storage types
    valid_types = ["local", "s3", "supabase"]
    if source_type not in valid_types:
        logger.error(f"❌ Invalid source type: {source_type}")
        logger.info(f"   Supported types: {', '.join(valid_types)}")
        return
    
    if dest_type not in valid_types:
        logger.error(f"❌ Invalid destination type: {dest_type}")
        logger.info(f"   Supported types: {', '.join(valid_types)}")
        return
    
    if source_type == dest_type:
        logger.error(f"❌ Source and destination cannot be the same: {source_type}")
        return
    
    # Get storage configurations
    logger.info(f"📋 Configuration:")
    logger.info(f"   Source: {source_type}")
    logger.info(f"   Destination: {dest_type}")
    
    source_config = get_storage_config(source_type)
    dest_config = get_storage_config(dest_type)
    
    # Check required environment variables
    if source_type == "s3":
        if not source_config.get("bucket_name"):
            logger.error("❌ S3_BUCKET_NAME environment variable required for source")
            return
    elif source_type == "supabase":
        if not source_config.get("supabase_url") or not source_config.get("supabase_key"):
            logger.error("❌ SUPABASE_URL and SUPABASE_KEY environment variables required for source")
            return
    
    if dest_type == "s3":
        if not dest_config.get("bucket_name"):
            logger.error("❌ S3_BUCKET_NAME environment variable required for destination")
            return
    elif dest_type == "supabase":
        if not dest_config.get("supabase_url") or not dest_config.get("supabase_key"):
            logger.error("❌ SUPABASE_URL and SUPABASE_KEY environment variables required for destination")
            return
    
    # Confirm migration
    logger.warning(f"\n⚠️  This will migrate files from {source_type} to {dest_type}")
    if dry_run:
        logger.info(f"   DRY RUN MODE - No files will actually be migrated")
    logger.info(f"   Continue? (yes/no): ", end='")
    
    response = input().strip().lower()
    if response not in ['yes', 'y']:
        logger.info("Migration cancelled.")
        return
    
    # Create migrator and run migration
    migrator = StorageMigrator(
        source_type=source_type,
        dest_type=dest_type,
        source_config=source_config,
        dest_config=dest_config
    )
    
    try:
        await migrator.initialize()
        await migrator.migrate_all(update_database=update_db, dry_run=dry_run)
    except Exception as e:
        logger.error(f"\n❌ Migration failed: {e}")
        import traceback
from ...core.logging_config import get_logger

logger = get_logger(__name__)
        traceback.print_exc()
    finally:
        await migrator.close()


if __name__ == "__main__":
    asyncio.run(main())

