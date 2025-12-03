"""
Folder Service Interface.

Defines the contract for folder business logic operations.
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from ...domain.entities import Folder
from ...domain.value_objects import FolderPath


class IFolderService(ABC):
    """
    Interface for folder business logic.
    
    Defines the contract for folder operations including:
    - Creation
    - Retrieval
    - Deletion
    - Moving/renaming
    """
    
    @abstractmethod
    async def create_folder(self, name: str, parent_folder: Optional[FolderPath] = None) -> Folder:
        """
        Create a new folder.
        
        Args:
            name: Folder name
            parent_folder: Optional parent folder path
            
        Returns:
            Created Folder entity
        """
        pass
    
    @abstractmethod
    async def get_folder(self, folder_path: FolderPath) -> Optional[Folder]:
        """
        Get a folder by path.
        
        Args:
            folder_path: Folder path
            
        Returns:
            Folder entity if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def get_all_folders(self) -> List[FolderPath]:
        """
        Get all folders.
        
        Returns:
            List of folder paths
        """
        pass
    
    @abstractmethod
    async def delete_folder(self, folder_path: FolderPath) -> int:
        """
        Delete a folder and all its contents.
        
        Args:
            folder_path: Folder path to delete
            
        Returns:
            Number of documents deleted
        """
        pass
    
    @abstractmethod
    async def move_folder(self, folder_path: FolderPath, new_path: Optional[FolderPath]) -> int:
        """
        Move a folder to a new location.
        
        Args:
            folder_path: Current folder path
            new_path: New folder path (None for root)
            
        Returns:
            Number of documents moved
        """
        pass

