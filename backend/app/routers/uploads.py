"""
Upload Router - Handles file upload operations.

This router manages all file upload functionality:
- Single file uploads (regular files and ZIP archives)
- Bulk file uploads with queue-based processing
- Duplicate detection via checksum

Architecture:
- Router handles HTTP request/response only
- UploadService handles all business logic
- Supports unlimited file uploads with adaptive chunking

Example Usage:
    POST /upload - Upload single file
    POST /upload/bulk - Upload multiple files
    POST /upload/check-duplicate - Check if file exists
"""
from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException, Form
from typing import List, Optional
from pydantic import BaseModel

from .dependencies import get_upload_service, get_document_processing_service
from ..core.config import UPLOAD_DIR
from pathlib import Path
from ..core.logging_config import get_logger

logger = get_logger(__name__)

# Create router instance
router = APIRouter()


class BulkUploadResponse(BaseModel):
    """
    Response model for bulk upload endpoint.
    
    Provides comprehensive statistics about the bulk upload operation.
    
    Attributes:
        total_files: Total number of files attempted to upload
        successful: Number of successfully uploaded files
        failed: Number of failed uploads
        duplicates: Number of duplicate files skipped
        document_ids: List of successfully uploaded document IDs
        errors: List of error details for failed/duplicate files
    """
    total_files: int
    successful: int
    failed: int
    duplicates: int
    document_ids: List[str]
    errors: List[dict]


@router.post("/upload")
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    folder: Optional[str] = Form(None),
    checksum: Optional[str] = Form(None)
):
    """
    Upload a single document file.
    
    This endpoint handles both regular files and ZIP archives:
    - Regular files: Saved directly to storage
    - ZIP files: Extracted and each file processed individually
    
    The upload process:
    1. Validates file (checks for ZIP)
    2. Calculates or uses provided checksum
    3. Checks for duplicates
    4. Saves file to storage (local/S3/Supabase)
    5. Creates document record in database
    6. Triggers background AI processing
    
    Args:
        background_tasks: FastAPI background tasks manager (injected)
        file: The file to upload (required)
        folder: Optional folder path for organization
                Example: "Invoices/2024" or None for root
        checksum: Optional pre-calculated SHA-256 checksum
                  If provided, skips checksum calculation
    
    Returns:
        DocumentMetadata: Created document metadata
        
    Raises:
        HTTPException: 409 if file is duplicate
                      500 if upload fails
    
    Example Request:
        POST /upload
        Content-Type: multipart/form-data
        file: invoice.pdf
        folder: Invoices/2024
    
    Example Response:
        {
            "id": "abc-123",
            "filename": "invoice.pdf",
            "folder": "Invoices/2024",
            "status": "ready",
            "checksum": "sha256...",
            ...
        }
    
    Note:
        - ZIP files are NOT saved - only extracted files are processed
        - Duplicate files are rejected with 409 status
        - AI processing happens asynchronously in background
    """
    try:
        # Get required services via dependency injection
        upload_service = get_upload_service()
        processing_service = get_document_processing_service()
        
        # Process upload through service layer
        # Service handles: ZIP extraction, duplicate checking, file saving, DB storage
        result = await upload_service.upload_single_file(file, folder, checksum)
        
        # Handle duplicate file case
        if result.get("status") == "duplicate":
            raise HTTPException(
                status_code=409,  # Conflict
                detail=f"File '{file.filename}' already exists as '{result.get('existing_filename')}'"
            )
        
        # Handle upload error case
        if result.get("status") == "error":
            raise HTTPException(
                status_code=500,
                detail=f"Upload failed: {result.get('error')}"
            )
        
        # Trigger AI processing for successful uploads
        # This runs asynchronously and doesn't block the response
        if result.get("status") == "success":
            doc = result.get("document")
            if doc and doc.get("id") and doc.get("file_path"):
                background_tasks.add_task(
                    processing_service.process_document_sync,
                    doc["id"],
                    Path(doc["file_path"])
                )
        
        # Return document metadata for successful uploads
        return result.get("document") if result.get("status") == "success" else result
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Wrap unexpected errors
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.post("/upload/bulk", response_model=BulkUploadResponse)
async def upload_bulk_files(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    folders: Optional[List[str]] = Form(None),
    checksums: Optional[List[str]] = Form(None),
    concurrency: Optional[int] = Form(None)
):
    """
    Upload multiple files efficiently using queue-based worker pool.
    
    This endpoint is optimized for handling large numbers of files:
    - Small batches (<1000): Direct queue processing
    - Large batches (1000+): Adaptive chunking for memory efficiency
    - Very large batches (100k+): Larger chunks with optimized workers
    
    Features:
    - Automatic retry with exponential backoff (up to 3 retries)
    - Dynamic worker scaling based on batch size
    - Duplicate detection for all files
    - Progress tracking and error reporting
    
    Args:
        background_tasks: FastAPI background tasks manager (injected)
        files: List of files to upload (required)
        folders: Optional list of folder paths (one per file, same order)
                 Example: ["Invoices/2024", "Contracts/2024", None]
        checksums: Optional list of pre-calculated checksums (one per file)
        concurrency: Optional concurrency hint (auto-calculated if not provided)
    
    Returns:
        BulkUploadResponse: Summary statistics and results
        
    Example Request:
        POST /upload/bulk
        files: [file1.pdf, file2.pdf, file3.pdf]
        folders: ["Invoices", "Contracts", None]
    
    Example Response:
        {
            "total_files": 3,
            "successful": 2,
            "failed": 0,
            "duplicates": 1,
            "document_ids": ["id1", "id2"],
            "errors": [
                {"filename": "file3.pdf", "error": "Duplicate of 'file1.pdf'"}
            ]
        }
    
    Performance:
        - 10 files: ~5-10 workers, ~10 seconds
        - 1,000 files: ~20-30 workers, ~5 minutes
        - 100,000 files: ~50-100 workers, ~2 hours
        - Scales to millions of files with adaptive chunking
    """
    try:
        # Get required services
        upload_service = get_upload_service()
        processing_service = get_document_processing_service()
        
        # Process bulk upload through service
        # Service handles: chunking, queue management, worker scaling, retries
        result = await upload_service.upload_bulk_files(
            files, folders, checksums, background_tasks, concurrency
        )
        
        # Trigger AI processing for all successfully uploaded documents
        # This happens asynchronously and doesn't block the response
        for doc_id in result.get("document_ids", []):
            doc = await upload_service.db.get_document(doc_id)
            if doc and doc.get("file_path"):
                background_tasks.add_task(
                    processing_service.process_document_sync,
                    doc_id,
                    Path(doc["file_path"])
                )
        
        # Return structured response with statistics
        return BulkUploadResponse(**result)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Bulk upload failed: {str(e)}"
        )


@router.post("/upload/check-duplicate")
async def check_duplicate(checksum: str = Form(...)):
    """Check if a file with the given checksum already exists."""
    upload_service = get_upload_service()
    duplicate_doc = await upload_service.check_duplicate(checksum)
    
    if duplicate_doc:
        return {
            "is_duplicate": True,
            "document_id": duplicate_doc["id"],
            "filename": duplicate_doc["filename"]
        }
    return {"is_duplicate": False}


@router.post("/upload/check-duplicates")
async def check_duplicates(checksums: List[str] = Form(...)):
    """Check multiple checksums at once for duplicates."""
    upload_service = get_upload_service()
    duplicates = []
    
    for checksum in checksums:
        duplicate_doc = await upload_service.check_duplicate(checksum)
        if duplicate_doc:
            duplicates.append({
                "checksum": checksum,
                "document_id": duplicate_doc["id"],
                "filename": duplicate_doc["filename"]
            })
    
    return {"duplicates": duplicates}

