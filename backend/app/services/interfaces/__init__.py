"""
Service Interfaces Module - Define contracts for business logic services.

This module provides interfaces following the Interface Segregation Principle.
Each interface is in its own file for better organization and maintainability.

To add a new interface:
1. Create a new interface file (e.g., `isearch_service.py`)
2. Define the interface class inheriting from ABC
3. Export it in this __init__.py file
"""
from .idocument_service import IDocumentService
from .ifolder_service import IFolderService
from .ifile_service import IFileService
from .iais_service import IAIService

__all__ = [
    "IDocumentService",
    "IFolderService",
    "IFileService",
    "IAIService",
]

