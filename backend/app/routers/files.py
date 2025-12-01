"""
Files Router - Handles file serving.
Refactored to follow Single Responsibility Principle.
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, Response

from .dependencies import get_file_service
from ..core.config import STORAGE_TYPE

router = APIRouter()


@router.get("/files/{filename}")
async def get_file(filename: str):
    """Get a file from storage (works with local, S3, or Supabase)."""
    try:
        file_service = get_file_service()
        storage_adapter = await file_service.get_storage()
        
        # filename is already relative (e.g., "cfcac16d-8cd4-43cd-9899-d601a8372b5a.pdf")
        file_path = filename
        
        # Check if file exists
        if not await storage_adapter.file_exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")
        
        # For markdown/text files, return text content
        if filename.endswith('.md') or filename.endswith('.txt'):
            text_content = await storage_adapter.get_text(file_path)
            return Response(content=text_content, media_type="text/plain; charset=utf-8")
        
        # For local storage, return FileResponse for efficiency
        if STORAGE_TYPE.lower() == "local":
            local_storage = storage_adapter
            local_path = local_storage._get_full_path(file_path)
            if local_path.exists():
                return FileResponse(local_path)
            else:
                raise HTTPException(status_code=404, detail="File not found")
        
        # For S3/Supabase, get file bytes
        file_bytes = await storage_adapter.get_file(file_path)
        return Response(content=file_bytes, media_type="application/octet-stream")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving file: {str(e)}")

