"""
Database Factory for creating database adapters.
Implements Factory Pattern for plug-and-play database support.
"""
import os
from pathlib import Path
from typing import Optional

from .base import DatabaseInterface
from .memory_adapter import MemoryAdapter
from .json_adapter import JSONAdapter
from .scalable_json_adapter import ScalableJSONAdapter
from ...core.logging_config import get_logger

logger = get_logger(__name__)

class DatabaseFactory:
    """
    Factory for creating database adapters.
    Supports JSON (file-based), ScalableJSON (shard-based), and Memory (in-memory) database backends.
    """
    
    @staticmethod
    def create(database_type: Optional[str] = None, **kwargs) -> DatabaseInterface:
        """
        Create a database adapter instance.
        
        Args:
            database_type: Type of database ('json', 'scalable_json', 'memory', or None for auto-detect)
            **kwargs: Additional arguments for specific database adapters
        
        Returns:
            DatabaseInterface instance
        
        Examples:
            # JSON (file-based, persistent, legacy)
            db = DatabaseFactory.create('json', data_dir=Path('data/json_db'))
            
            # ScalableJSON (shard-based, scalable to 500K+ records)
            db = DatabaseFactory.create('scalable_json', data_dir=Path('data/json_db'))
            
            # Memory (in-memory, non-persistent)
            db = DatabaseFactory.create('memory')
            
            # Auto-detect from environment
            db = DatabaseFactory.create()
        """
        # Auto-detect database type from environment if not specified
        if database_type is None:
            database_type = os.getenv("DATABASE_TYPE", "scalable_json").lower()
        
        database_type = database_type.lower()
        
        if database_type == "json":
            return DatabaseFactory._create_json(**kwargs)
        elif database_type == "scalable_json":
            return DatabaseFactory._create_scalable_json(**kwargs)
        elif database_type == "memory":
            return DatabaseFactory._create_memory(**kwargs)
        else:
            raise ValueError(
                f"Unsupported database type: {database_type}. "
                f"Supported types: 'json', 'scalable_json', 'memory'"
            )
    
    @staticmethod
    def _create_memory(**kwargs) -> MemoryAdapter:
        """Create in-memory adapter (for demos and testing)."""
        return MemoryAdapter()
    
    @staticmethod
    def _create_json(**kwargs) -> JSONAdapter:
        """Create JSON file-based adapter (legacy, for backward compatibility)."""
        data_dir = kwargs.get("data_dir")
        if data_dir:
            from pathlib import Path
            data_dir = Path(data_dir) if isinstance(data_dir, str) else data_dir
        return JSONAdapter(data_dir=data_dir)
    
    @staticmethod
    def _create_scalable_json(**kwargs) -> ScalableJSONAdapter:
        """Create scalable JSON adapter (shard-based, scalable to 500K+ records)."""
        data_dir = kwargs.get("data_dir")
        if data_dir:
            data_dir = Path(data_dir) if isinstance(data_dir, str) else data_dir
        return ScalableJSONAdapter(data_dir=data_dir)
    
    @staticmethod
    async def create_and_initialize(database_type: Optional[str] = None, **kwargs) -> DatabaseInterface:
        """
        Create database adapter and initialize it.
        
        Args:
            database_type: Type of database
            **kwargs: Additional arguments
        
        Returns:
            Initialized DatabaseInterface instance
        """
        db = DatabaseFactory.create(database_type, **kwargs)
        await db.initialize()
        return db

