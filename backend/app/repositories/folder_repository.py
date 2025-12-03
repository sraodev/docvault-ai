"""
Folder Repository - Concrete implementation of folder data access.
"""
from typing import List, Optional
from datetime import datetime

from .interfaces import IFolderRepository
from ..domain.entities import Folder
from ..domain.value_objects import FolderPath
from ..services.database.base import DatabaseInterface
from ..core.logging_config import get_logger

logger = get_logger(__name__)

class FolderRepository(IFolderRepository):
    """
    Repository for folder data access.
    Maps domain entities to database operations.
    """
    
    def __init__(self, db_service: DatabaseInterface):
        """
        Initialize repository with database service.
        
        Args:
            db_service: Database adapter (dependency injection)
        """
        self._db = db_service
    
    def _to_entity(self, data: dict) -> Folder:
        """Convert database record to domain entity."""
        return Folder(
            folder_path=data["folder_path"],
            name=data["name"],
            parent_folder=data.get("parent_folder"),
            created_date=datetime.fromisoformat(data["created_date"])
        )
    
    def _to_dict(self, folder: Folder) -> dict:
        """Convert domain entity to database record."""
        return {
            "folder_path": str(folder.folder_path),
            "name": folder.name,
            "parent_folder": str(folder.parent_folder) if folder.parent_folder else None,
            "created_date": folder.created_date.isoformat()
        }
    
    async def create(self, folder: Folder) -> Folder:
        """Create a new folder."""
        data = self._to_dict(folder)
        result = await self._db.create_folder(data)
        return self._to_entity(result)
    
    async def get_by_path(self, folder_path: FolderPath) -> Optional[Folder]:
        """Get folder by path."""
        data = await self._db.get_folder(str(folder_path))
        return self._to_entity(data) if data else None
    
    async def get_all(self) -> List[FolderPath]:
        """Get all folder paths."""
        paths = await self._db.get_all_folders()
        return [FolderPath(path) for path in paths]
    
    async def delete(self, folder_path: FolderPath) -> int:
        """Delete a folder and return count of deleted items."""
        return await self._db.delete_folder(str(folder_path))
    
    async def move(self, old_path: FolderPath, new_path: Optional[FolderPath]) -> int:
        """Move a folder to a new location."""
        new_path_str = str(new_path) if new_path else None
        return await self._db.update_folder_path(str(old_path), new_path_str)

