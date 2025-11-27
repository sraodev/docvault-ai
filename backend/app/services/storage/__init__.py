"""
File Storage abstraction layer for plug-and-play storage support.
Supports multiple storage backends without changing business logic.
"""
from .base import FileStorageInterface
from .local_storage import LocalFileStorage
from .s3_storage import S3FileStorage
from .supabase_storage import SupabaseFileStorage
from .factory import FileStorageFactory

__all__ = [
    "FileStorageInterface",
    "LocalFileStorage",
    "S3FileStorage",
    "SupabaseFileStorage",
    "FileStorageFactory"
]

