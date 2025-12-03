"""
File Storage Factory for creating storage adapters.
Implements Factory Pattern for plug-and-play storage support.
"""
import os
from pathlib import Path
from typing import Optional

from .base import FileStorageInterface
from .local_storage import LocalFileStorage
from .s3_storage import S3FileStorage
from ...core.logging_config import get_logger

logger = get_logger(__name__)
# Supabase import is conditional - only imported when needed

class FileStorageFactory:
    """
    Factory for creating file storage adapters.
    Supports multiple storage backends: Local, S3, Supabase Storage.
    """
    
    @staticmethod
    def create(storage_type: Optional[str] = None, **kwargs) -> FileStorageInterface:
        """
        Create a storage adapter instance.
        
        Args:
            storage_type: Type of storage ('local', 's3', 'supabase', or None for auto-detect)
            **kwargs: Additional arguments for specific storage adapters
        
        Returns:
            FileStorageInterface instance
        
        Examples:
            # Local filesystem
            storage = FileStorageFactory.create('local', base_dir=Path('uploads'))
            
            # S3
            storage = FileStorageFactory.create('s3', bucket_name='my-bucket', ...)
            
            # Supabase Storage
            storage = FileStorageFactory.create('supabase', bucket_name='files', ...)
            
            # Auto-detect from environment
            storage = FileStorageFactory.create()
        """
        # Auto-detect storage type from environment if not specified
        if storage_type is None:
            storage_type = os.getenv("STORAGE_TYPE", "local").lower()
        
        storage_type = storage_type.lower()
        
        if storage_type == "local":
            return FileStorageFactory._create_local(**kwargs)
        elif storage_type == "s3":
            return FileStorageFactory._create_s3(**kwargs)
        elif storage_type == "supabase":
            return FileStorageFactory._create_supabase(**kwargs)
        else:
            raise ValueError(
                f"Unsupported storage type: {storage_type}. "
                f"Supported types: 'local', 's3', 'supabase'"
            )
    
    @staticmethod
    def _create_local(**kwargs) -> LocalFileStorage:
        """Create local filesystem storage adapter."""
        base_dir = kwargs.get("base_dir")
        
        if base_dir is None:
            # Default to backend/uploads
            from ...core.config import BASE_DIR
            base_dir = BASE_DIR / "uploads"
        elif isinstance(base_dir, str):
            base_dir = Path(base_dir)
        
        return LocalFileStorage(base_dir=base_dir)
    
    @staticmethod
    def _create_s3(**kwargs) -> S3FileStorage:
        """Create S3 storage adapter."""
        bucket_name = kwargs.get(
            "bucket_name",
            os.getenv("S3_BUCKET_NAME")
        )
        if not bucket_name:
            raise ValueError("S3 bucket_name is required")
        
        aws_access_key_id = kwargs.get(
            "aws_access_key_id",
            os.getenv("AWS_ACCESS_KEY_ID")
        )
        aws_secret_access_key = kwargs.get(
            "aws_secret_access_key",
            os.getenv("AWS_SECRET_ACCESS_KEY")
        )
        region_name = kwargs.get(
            "region_name",
            os.getenv("AWS_REGION", "us-east-1")
        )
        endpoint_url = kwargs.get(
            "endpoint_url",
            os.getenv("S3_ENDPOINT_URL")  # For S3-compatible services
        )
        
        return S3FileStorage(
            bucket_name=bucket_name,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region_name,
            endpoint_url=endpoint_url
        )
    
    @staticmethod
    def _create_supabase(**kwargs):
        """Create Supabase Storage adapter."""
        try:
            from .supabase_storage import SupabaseFileStorage
        except ImportError:
            raise ImportError(
                "Supabase storage requires the 'supabase' package. "
                "Install it with: pip install supabase"
            )
        
        supabase_url = kwargs.get(
            "supabase_url",
            os.getenv("SUPABASE_URL")
        )
        if not supabase_url:
            raise ValueError("Supabase URL is required")
        
        supabase_key = kwargs.get(
            "supabase_key",
            os.getenv("SUPABASE_KEY")
        )
        if not supabase_key:
            raise ValueError("Supabase key is required")
        
        bucket_name = kwargs.get(
            "bucket_name",
            os.getenv("SUPABASE_STORAGE_BUCKET", "files")
        )
        
        return SupabaseFileStorage(
            supabase_url=supabase_url,
            supabase_key=supabase_key,
            bucket_name=bucket_name
        )
    
    @staticmethod
    async def create_and_initialize(storage_type: Optional[str] = None, **kwargs) -> FileStorageInterface:
        """
        Create storage adapter and initialize it.
        
        Args:
            storage_type: Type of storage
            **kwargs: Additional arguments
        
        Returns:
            Initialized FileStorageInterface instance
        """
        storage = FileStorageFactory.create(storage_type, **kwargs)
        await storage.initialize()
        return storage

