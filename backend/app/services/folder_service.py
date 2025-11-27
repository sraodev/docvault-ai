"""
Folder Service - Business logic for folder operations.
Follows Single Responsibility Principle.
"""
from datetime import datetime
from typing import List, Optional

from .interfaces import IFolderService
from ..domain.entities import Folder
from ..domain.value_objects import FolderPath
from ..repositories.interfaces import IFolderRepository

class FolderService(IFolderService):
    """
    Service for folder business logic.
    Handles folder creation, validation, and operations.
    """
    
    def __init__(self, folder_repo: IFolderRepository):
        """
        Initialize folder service.
        
        Args:
            folder_repo: Folder repository (dependency injection)
        """
        self._repo = folder_repo
    
    def _validate_folder_name(self, name: str) -> None:
        """Validate folder name."""
        name = name.strip()
        if not name:
            raise ValueError("Folder name cannot be empty")
        
        invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
        if any(char in name for char in invalid_chars):
            raise ValueError(f"Folder name cannot contain: {', '.join(invalid_chars)}")
    
    async def create_folder(self, name: str, parent_folder: Optional[FolderPath] = None) -> Folder:
        """
        Create a new folder.
        
        Args:
            name: Folder name
            parent_folder: Optional parent folder path
        
        Returns:
            Created folder entity
        """
        # Validate folder name
        self._validate_folder_name(name)
        
        # Build full folder path
        if parent_folder:
            full_path = FolderPath(f"{parent_folder}/{name}")
        else:
            full_path = FolderPath(name)
        
        # Check if folder already exists
        existing = await self._repo.get_by_path(full_path)
        if existing:
            raise ValueError(f"Folder '{full_path}' already exists")
        
        # Create folder entity
        folder = Folder(
            folder_path=full_path,
            name=name,
            parent_folder=parent_folder,
            created_date=datetime.now()
        )
        
        # Save to repository
        return await self._repo.create(folder)
    
    async def get_folder(self, folder_path: FolderPath) -> Optional[Folder]:
        """Get a folder by path."""
        return await self._repo.get_by_path(folder_path)
    
    async def get_all_folders(self) -> List[FolderPath]:
        """Get all folders."""
        return await self._repo.get_all()
    
    async def delete_folder(self, folder_path: FolderPath) -> int:
        """
        Delete a folder and all its contents.
        
        Returns:
            Number of items deleted
        """
        return await self._repo.delete(folder_path)
    
    async def move_folder(self, folder_path: FolderPath, new_path: Optional[FolderPath]) -> int:
        """
        Move a folder to a new location.
        
        Returns:
            Number of items moved
        """
        return await self._repo.move(folder_path, new_path)

