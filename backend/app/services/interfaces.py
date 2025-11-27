"""
Service interfaces - Define contracts for business logic services.
Follows Interface Segregation Principle.
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from pathlib import Path
from ..domain.entities import Document, Folder
from ..domain.value_objects import FileChecksum, FolderPath

class IDocumentService(ABC):
    """Interface for document business logic."""
    
    @abstractmethod
    async def upload_document(
        self,
        file_path: Path,
        filename: str,
        folder: Optional[FolderPath] = None,
        checksum: Optional[FileChecksum] = None
    ) -> Document:
        """Upload and process a document."""
        pass
    
    @abstractmethod
    async def get_document(self, doc_id: str) -> Optional[Document]:
        """Get a document by ID."""
        pass
    
    @abstractmethod
    async def get_all_documents(self, folder: Optional[FolderPath] = None) -> List[Document]:
        """Get all documents."""
        pass
    
    @abstractmethod
    async def delete_document(self, doc_id: str) -> bool:
        """Delete a document."""
        pass
    
    @abstractmethod
    async def check_duplicate(self, checksum: FileChecksum) -> Optional[Document]:
        """Check if a document with this checksum exists."""
        pass

class IFolderService(ABC):
    """Interface for folder business logic."""
    
    @abstractmethod
    async def create_folder(self, name: str, parent_folder: Optional[FolderPath] = None) -> Folder:
        """Create a new folder."""
        pass
    
    @abstractmethod
    async def get_folder(self, folder_path: FolderPath) -> Optional[Folder]:
        """Get a folder by path."""
        pass
    
    @abstractmethod
    async def get_all_folders(self) -> List[FolderPath]:
        """Get all folders."""
        pass
    
    @abstractmethod
    async def delete_folder(self, folder_path: FolderPath) -> int:
        """Delete a folder."""
        pass
    
    @abstractmethod
    async def move_folder(self, folder_path: FolderPath, new_path: Optional[FolderPath]) -> int:
        """Move a folder."""
        pass

class IFileService(ABC):
    """Interface for file operations."""
    
    @abstractmethod
    async def save_upload(self, file, destination: Path) -> None:
        """Save uploaded file."""
        pass
    
    @abstractmethod
    async def extract_text(self, file_path: Path) -> str:
        """Extract text from file."""
        pass
    
    @abstractmethod
    async def delete_file(self, file_path: Path) -> None:
        """Delete a file."""
        pass
    
    @abstractmethod
    async def save_markdown(self, content: str, destination: Path) -> None:
        """Save markdown content."""
        pass

class IAIService(ABC):
    """Interface for AI operations."""
    
    @abstractmethod
    def generate_summary(self, text: str) -> str:
        """Generate summary from text."""
        pass
    
    @abstractmethod
    def generate_markdown(self, text: str) -> str:
        """Generate markdown from text."""
        pass

