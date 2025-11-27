"""
Mappers between domain entities and DTOs.
Separates domain layer from API layer.
"""
from typing import List
from ..domain.entities import Document, Folder
from ..domain.value_objects import FolderPath
from .dto import DocumentDTO, FolderDTO

class DocumentMapper:
    """Maps between Document entity and DocumentDTO."""
    
    @staticmethod
    def to_dto(document: Document) -> DocumentDTO:
        """Convert domain entity to DTO."""
        return DocumentDTO(
            id=document.id,
            filename=document.filename,
            upload_date=document.upload_date.isoformat(),
            modified_date=document.modified_date.isoformat() if document.modified_date else None,
            file_path=str(document.file_path),
            folder=str(document.folder) if document.folder else None,
            checksum=str(document.checksum) if document.checksum else None,
            size=document.size,
            status=document.status,
            summary=document.summary,
            markdown_path=str(document.markdown_path) if document.markdown_path else None,
            upload_progress=document.upload_progress
        )
    
    @staticmethod
    def to_dto_list(documents: List[Document]) -> List[DocumentDTO]:
        """Convert list of entities to DTOs."""
        return [DocumentMapper.to_dto(doc) for doc in documents]

class FolderMapper:
    """Maps between Folder entity and FolderDTO."""
    
    @staticmethod
    def to_dto(folder: Folder) -> FolderDTO:
        """Convert domain entity to DTO."""
        return FolderDTO(
            folder_path=str(folder.folder_path),
            name=folder.name,
            parent_folder=str(folder.parent_folder) if folder.parent_folder else None,
            created_date=folder.created_date.isoformat()
        )
    
    @staticmethod
    def paths_to_dto_list(paths: List[FolderPath]) -> List[str]:
        """Convert folder paths to list of strings."""
        return [str(path) for path in paths]

