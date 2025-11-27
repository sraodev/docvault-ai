"""
Repository layer - Abstracts data access.
Follows Repository Pattern for clean separation of data access from business logic.
"""
from .document_repository import DocumentRepository, IDocumentRepository
from .folder_repository import FolderRepository, IFolderRepository

__all__ = [
    "DocumentRepository",
    "IDocumentRepository",
    "FolderRepository",
    "IFolderRepository"
]

