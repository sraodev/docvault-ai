"""
Database abstraction layer for plug-and-play database support.
Supports JSON (file-based) and Memory (in-memory) database backends.
"""
from .base import DatabaseInterface
from .memory_adapter import MemoryAdapter
from .json_adapter import JSONAdapter
from .factory import DatabaseFactory
from ...core.logging_config import get_logger

logger = get_logger(__name__)

__all__ = [
    "DatabaseInterface",
    "MemoryAdapter",
    "JSONAdapter",
    "DatabaseFactory"
]

