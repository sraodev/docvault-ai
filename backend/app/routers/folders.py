"""
Folders Router - Handles folder operations.
Refactored to follow Single Responsibility Principle.
"""
from fastapi import APIRouter, HTTPException, Form
from typing import Optional
import urllib.parse

from .dependencies import get_db_service
from ..utils.document_utils import normalize_folder_name

router = APIRouter()


@router.get("/documents/folders/list")
async def get_folders():
    """
    Get list of all available folders/categories.
    Returns unique folder paths from both documents and folders collection.
    """
    db_service = get_db_service()
    folders = await db_service.get_all_folders()
    return {"folders": folders}


@router.post("/documents/folders")
async def create_folder(
    folder_name: str = Form(...),
    parent_folder: Optional[str] = Form(None)
):
    """
    Create a new folder. Since folders are virtual (metadata only),
    this validates the folder name and returns success.
    """
    try:
        db_service = get_db_service()
        
        # Validate folder name
        folder_name = folder_name.strip()
        if not folder_name:
            raise HTTPException(status_code=400, detail="Folder name cannot be empty")
        
        # Validate folder name doesn't contain invalid characters
        invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
        if any(char in folder_name for char in invalid_chars):
            raise HTTPException(
                status_code=400,
                detail=f"Folder name cannot contain: {', '.join(invalid_chars)}"
            )
        
        # Build full folder path
        if parent_folder and parent_folder.strip():
            full_folder_path = f"{parent_folder.strip()}/{folder_name}"
        else:
            full_folder_path = folder_name
        
        # Check if folder already exists
        existing_folder = await db_service.get_folder(full_folder_path)
        if existing_folder:
            raise HTTPException(
                status_code=409,
                detail=f"Folder '{full_folder_path}' already exists"
            )
        
        # Check if any documents use this folder path
        docs_in_folder = await db_service.get_documents_by_folder(full_folder_path)
        if docs_in_folder:
            raise HTTPException(
                status_code=409,
                detail=f"Folder '{full_folder_path}' already exists"
            )
        
        # Store folder metadata
        from datetime import datetime
        folder_data = {
            "name": folder_name,
            "folder_path": full_folder_path,
            "parent_folder": normalize_folder_name(parent_folder),
            "created_date": datetime.now().isoformat()
        }
        await db_service.create_folder(folder_data)
        
        return {
            "message": "Folder created successfully",
            "folder_path": full_folder_path,
            "folder_name": folder_name
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Folder creation failed: {str(e)}")


@router.delete("/documents/folders/{folder_path:path}")
async def delete_folder(folder_path: str):
    """
    Delete a folder and all documents within it (including subfolders).
    """
    try:
        db_service = get_db_service()
        
        # Ensure proper URL decoding
        folder_path = urllib.parse.unquote(folder_path)
        
        # Get all documents in this folder and subfolders
        docs_to_delete = await db_service.get_documents_by_folder(
            folder_path,
            include_subfolders=True
        )
        
        # Delete files from storage
        from .dependencies import get_file_service
        file_service = get_file_service()
        
        for doc in docs_to_delete:
            try:
                if doc.get("file_path"):
                    from pathlib import Path
                    await file_service.delete_file(Path(doc["file_path"]))
                if doc.get("markdown_path"):
                    from pathlib import Path
                    await file_service.delete_file(Path(doc["markdown_path"]))
            except Exception as file_err:
                print(f"Error deleting file for folder '{folder_path}': {file_err}")
        
        # Delete from database
        deleted_count = await db_service.delete_folder(folder_path)
        
        if deleted_count == 0:
            return {
                "message": f"Folder '{folder_path}' is empty or not found",
                "deleted_count": 0
            }
        
        return {
            "message": "Folder deleted successfully",
            "deleted_count": deleted_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Folder deletion failed: {str(e)}")


@router.put("/documents/folders/{folder_path:path}/move")
async def move_folder(folder_path: str, new_folder_path: Optional[str] = Form(None)):
    """
    Move a folder and all its contents (including subfolders) to a new location.
    If new_folder_path is None or empty, moves folder contents to root.
    """
    try:
        db_service = get_db_service()
        folder_path = urllib.parse.unquote(folder_path)
        
        # Normalize new_folder_path
        normalized_new_path = normalize_folder_name(new_folder_path)
        
        # Update folder paths
        moved_count = await db_service.update_folder_path(folder_path, normalized_new_path)
        
        return {
            "message": "Folder moved successfully",
            "moved_count": moved_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Folder move failed: {str(e)}")

