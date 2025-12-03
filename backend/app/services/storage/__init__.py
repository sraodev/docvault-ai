"""
File Storage abstraction layer for plug-and-play storage support.
Supports multiple storage backends without changing business logic.
"""
from .base import FileStorageInterface
from .local_storage import LocalFileStorage
from .s3_storage import S3FileStorage
from .factory import FileStorageFactory
from ...core.logging_config import get_logger

logger = get_logger(__name__)

# Conditionally import Supabase only if needed
import os
STORAGE_TYPE = os.getenv("STORAGE_TYPE", "local")
if STORAGE_TYPE.lower() == "supabase":
    try:
        from .supabase_storage import SupabaseFileStorage
        __all__ = [
            "FileStorageInterface",
            "LocalFileStorage",
            "S3FileStorage",
            "SupabaseFileStorage",
            "FileStorageFactory"
        ]
    except ImportError:
        # Supabase not installed, exclude it from exports
        __all__ = [
            "FileStorageInterface",
            "LocalFileStorage",
            "S3FileStorage",
            "FileStorageFactory"
        ]
else:
    __all__ = [
        "FileStorageInterface",
        "LocalFileStorage",
        "S3FileStorage",
        "FileStorageFactory"
    ]

