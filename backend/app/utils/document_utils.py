"""
Document utility functions for metadata normalization and validation.
Extracted from documents router to follow Single Responsibility Principle.
"""
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from ..core.logging_config import get_logger

logger = get_logger(__name__)


async def ensure_document_fields(
    doc: Dict[str, Any],
    db_service,
    update_db: bool = True
) -> Dict[str, Any]:
    """
    Ensure document has required fields (size, modified_date).
    Updates database if fields are missing and update_db is True.
    
    Args:
        doc: Document dictionary
        db_service: Database service for updates
        update_db: Whether to update database if fields are missing
        
    Returns:
        Document dictionary with ensured fields
    """
    # Ensure size field
    if "size" not in doc or doc.get("size") is None:
        file_path = Path(doc.get("file_path", ""))
        if file_path.exists():
            try:
                size = file_path.stat().st_size
                if update_db:
                    await db_service.update_document(doc["id"], {"size": size})
                doc["size"] = size
            except Exception:
                doc["size"] = None
    
    # Set modified_date to upload_date if not present (for backward compatibility)
    if "modified_date" not in doc or doc.get("modified_date") is None:
        doc["modified_date"] = doc.get("upload_date")
    
    return doc


def normalize_folder_name(folder: Optional[str]) -> Optional[str]:
    """
    Normalize folder name (trim whitespace, use None for empty strings).
    
    Args:
        folder: Folder name or path
        
    Returns:
        Normalized folder name or None
    """
    if folder and folder.strip():
        return folder.strip()
    return None


def create_document_metadata(
    doc_id: str,
    filename: str,
    file_path: str,
    file_size: int,
    checksum: str,
    folder: Optional[str] = None,
    status: str = "ready"
) -> Dict[str, Any]:
    """
    Create standardized document metadata dictionary.
    
    Args:
        doc_id: Document ID
        filename: Original filename
        file_path: Path to file
        file_size: File size in bytes
        checksum: File checksum
        folder: Optional folder path
        status: Document status (default: "ready")
        
    Returns:
        Document metadata dictionary
    """
    upload_time = datetime.now().isoformat()
    
    return {
        "id": doc_id,
        "filename": filename,
        "upload_date": upload_time,
        "file_path": file_path,
        "status": status,
        "summary": None,
        "markdown_path": None,
        "folder": normalize_folder_name(folder),
        "checksum": checksum,
        "size": file_size,
        "modified_date": upload_time
    }

