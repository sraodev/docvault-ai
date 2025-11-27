"""
Custom exceptions for API layer.
Separates business exceptions from HTTP exceptions.
"""
from fastapi import HTTPException, status

class DocumentNotFoundError(Exception):
    """Raised when document is not found."""
    pass

class DuplicateFileError(Exception):
    """Raised when duplicate file is detected."""
    pass

class FolderNotFoundError(Exception):
    """Raised when folder is not found."""
    pass

class InvalidFolderNameError(Exception):
    """Raised when folder name is invalid."""
    pass

class FileProcessingError(Exception):
    """Raised when file processing fails."""
    pass

def handle_business_exception(e: Exception) -> HTTPException:
    """
    Convert business exceptions to HTTP exceptions.
    This keeps business logic clean of HTTP concerns.
    """
    if isinstance(e, DocumentNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    elif isinstance(e, DuplicateFileError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    elif isinstance(e, FolderNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    elif isinstance(e, InvalidFolderNameError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    elif isinstance(e, FileProcessingError):
        return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    else:
        return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

