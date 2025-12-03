"""
Documents Router - Handles document CRUD operations.

This router is responsible for:
- Listing and retrieving documents
- Deleting documents
- Triggering AI processing for documents
- Regenerating summaries

Architecture:
- Router handles HTTP request/response only
- Business logic delegated to services
- Follows Single Responsibility Principle

Example Usage:
    GET /documents - List all documents
    GET /documents/{doc_id} - Get specific document
    DELETE /documents/{doc_id} - Delete document
    POST /documents/{doc_id}/process - Process document with AI
"""
from fastapi import APIRouter, BackgroundTasks, HTTPException
from typing import List, Optional
from pathlib import Path

from ..models.document import DocumentMetadata
from .dependencies import (
    get_db_service,
    get_document_processing_service,
    get_file_service
)
from ..utils.document_utils import ensure_document_fields
from ..core.config import UPLOAD_DIR
from ..core.logging_config import get_logger

logger = get_logger(__name__)

# Create router instance for this module
router = APIRouter()


@router.get("/documents", response_model=List[DocumentMetadata])
async def get_documents(folder: Optional[str] = None):
    """
    Get all documents, optionally filtered by folder.
    
    This endpoint retrieves all documents from the database. If a folder
    is specified, only documents in that folder are returned.
    
    The endpoint ensures all documents have required fields (size, modified_date)
    by normalizing them if missing.
    
    Args:
        folder: Optional folder path to filter documents. If None, returns all documents.
                Example: "Invoices/2024" or None for all documents.
    
    Returns:
        List[DocumentMetadata]: List of document metadata objects
        
    Example Response:
        [
            {
                "id": "abc-123",
                "filename": "invoice.pdf",
                "folder": "Invoices/2024",
                "status": "completed",
                "summary": "Invoice for services...",
                ...
            }
        ]
    
    Status Codes:
        200: Success
        500: Internal server error
    """
    # Get database service via dependency injection
    db_service = get_db_service()
    
    # Retrieve documents from database (filtered by folder if provided)
    docs = await db_service.get_all_documents(folder=folder)
    
    # Normalize document metadata: ensure all documents have required fields
    # This handles backward compatibility for documents created before certain fields existed
    for doc in docs:
        await ensure_document_fields(doc, db_service)
    
    return docs


@router.get("/documents/{doc_id}", response_model=DocumentMetadata)
async def get_document(doc_id: str):
    """
    Get a single document by its unique ID.
    
    Retrieves complete document metadata including summary, tags, and processing status.
    Ensures document has all required fields before returning.
    
    Args:
        doc_id: Unique document identifier (UUID format)
                Example: "550e8400-e29b-41d4-a716-446655440000"
    
    Returns:
        DocumentMetadata: Complete document metadata object
        
    Raises:
        HTTPException: 404 if document not found
                      500 if database error occurs
    
    Example Response:
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "filename": "contract.pdf",
            "folder": "Contracts",
            "status": "completed",
            "summary": "Service agreement between...",
            "tags": ["legal", "contract", "2024"],
            "upload_date": "2024-01-15T10:30:00",
            ...
        }
    """
    # Get database service
    db_service = get_db_service()
    
    # Retrieve document from database
    doc = await db_service.get_document(doc_id)
    
    # Validate document exists
    if not doc:
        raise HTTPException(
            status_code=404,
            detail=f"Document with ID '{doc_id}' not found"
        )
    
    # Ensure document has all required fields (size, modified_date, etc.)
    await ensure_document_fields(doc, db_service)
    
    return doc


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    """
    Delete a document and all its associated files.
    
    This endpoint performs a complete deletion:
    1. Deletes the original uploaded file from storage
    2. Deletes the AI-generated markdown file (if exists)
    3. Removes the document record from the database
    
    The deletion is atomic - if any step fails, an error is returned.
    
    Args:
        doc_id: Unique document identifier to delete
                Example: "550e8400-e29b-41d4-a716-446655440000"
    
    Returns:
        dict: Success message
        
    Raises:
        HTTPException: 404 if document not found
                      500 if deletion fails
    
    Example Response:
        {
            "message": "Document deleted successfully"
        }
    
    Note:
        This operation cannot be undone. All associated files are permanently deleted.
    """
    # Get required services
    db_service = get_db_service()
    file_service = get_file_service()
    
    # Verify document exists before attempting deletion
    doc = await db_service.get_document(doc_id)
    if not doc:
        raise HTTPException(
            status_code=404,
            detail=f"Document with ID '{doc_id}' not found"
        )
    
    try:
        # Step 1: Delete original uploaded file from storage
        # Storage can be local filesystem, S3, or Supabase
        if doc.get("file_path"):
            await file_service.delete_file(Path(doc["file_path"]))
        
        # Step 2: Delete AI-generated markdown file (if it exists)
        # This is the processed markdown version created during AI processing
        if doc.get("markdown_path"):
            await file_service.delete_file(Path(doc["markdown_path"]))
        
        # Step 3: Remove document record from database
        # This removes all metadata (summary, tags, embeddings, etc.)
        await db_service.delete_document(doc_id)
        
        return {"message": "Document deleted successfully"}
        
    except HTTPException:
        # Re-raise HTTP exceptions (like 404) as-is
        raise
    except Exception as e:
        # Wrap unexpected errors in HTTPException
        raise HTTPException(
            status_code=500,
            detail=f"Deletion failed: {str(e)}"
        )


@router.post("/documents/{doc_id}/process")
async def process_document(doc_id: str, background_tasks: BackgroundTasks):
    """
    Trigger AI processing for a document on-demand.
    
    This endpoint initiates AI processing for a document that hasn't been processed yet.
    Processing includes:
    - Text extraction from the document
    - AI-generated summary
    - AI-generated markdown conversion
    - Tag extraction (AI + rule-based fallback)
    - Embedding generation for semantic search
    
    Processing happens asynchronously in the background, so this endpoint returns
    immediately with a "processing" status.
    
    Args:
        doc_id: Unique document identifier to process
                Example: "550e8400-e29b-41d4-a716-446655440000"
        background_tasks: FastAPI background tasks manager (injected automatically)
    
    Returns:
        dict: Processing status message
        
    Raises:
        HTTPException: 404 if document not found
                      400 if file path is missing
                      404 if file doesn't exist
    
    Example Response:
        {
            "message": "AI processing started",
            "status": "processing"
        }
    
    Status Handling:
        - "ready": Document will be processed
        - "processing": Already being processed, returns immediately
        - "completed": Already processed, returns immediately
    
    Note:
        Processing is idempotent - calling this multiple times is safe.
        The document status prevents duplicate processing.
    """
    # Get required services
    db_service = get_db_service()
    processing_service = get_document_processing_service()
    
    # Retrieve document from database
    doc = await db_service.get_document(doc_id)
    if not doc:
        raise HTTPException(
            status_code=404,
            detail=f"Document with ID '{doc_id}' not found"
        )
    
    # Check current processing status to avoid duplicate processing
    current_status = doc.get("status", "ready")
    
    if current_status == "processing":
        # Document is already being processed - return immediately
        return {
            "message": "Document is already being processed",
            "status": "processing"
        }
    
    if current_status == "completed":
        # Document is already processed - return immediately
        return {
            "message": "Document is already processed",
            "status": "completed"
        }
    
    # Get file path from document metadata
    file_path_str = doc.get("file_path")
    if not file_path_str:
        raise HTTPException(
            status_code=400,
            detail="Document file path not found in database"
        )
    
    file_path = Path(file_path_str)
    
    # Handle path resolution issues (legacy compatibility)
    # Some old documents may have incorrect paths stored in database
    if not file_path.exists():
        # Try common path variations to find the actual file
        filename = file_path.name
        possible_paths = [
            UPLOAD_DIR / filename,  # Standard upload directory
            # Handle duplicated path segments (legacy bug fix)
            Path(file_path_str.replace(str(UPLOAD_DIR) + str(UPLOAD_DIR), str(UPLOAD_DIR))),
        ]
        
        # Search for file in possible locations
        found_path = None
        for possible_path in possible_paths:
            if possible_path.exists():
                found_path = possible_path
                # Update database with correct path for future use
                await db_service.update_document(
                    doc_id,
                    {"file_path": str(found_path)}
                )
                logger.info(f"Fixed file path for {doc_id}: {file_path_str} -> {found_path}")
                break
        
        if found_path:
            file_path = found_path
        else:
            # File not found in any expected location
            raise HTTPException(
                status_code=404,
                detail=f"Document file not found at {file_path_str}"
            )
    
    # Queue AI processing as background task
    # This runs asynchronously and doesn't block the HTTP response
    background_tasks.add_task(
        processing_service.process_document_sync,
        doc_id,
        file_path
    )
    
    return {
        "message": "AI processing started",
        "status": "processing"
    }


@router.post("/documents/{doc_id}/regenerate-summary")
async def regenerate_summary(doc_id: str, background_tasks: BackgroundTasks):
    """
    Regenerate summary for a specific document.
    """
    db_service = get_db_service()
    processing_service = get_document_processing_service()
    
    try:
        # Get document
        doc = await db_service.get_document(doc_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Check if file exists
        file_path = Path(doc.get("file_path", ""))
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Document file not found")
        
        # Update status to processing
        await db_service.update_document(doc_id, {
            "status": "processing",
            "summary": None,
            "markdown_path": None
        })
        
        # Trigger background processing
        background_tasks.add_task(
            processing_service.process_document_sync,
            doc_id,
            file_path
        )
        
        return {
            "message": "Summary regeneration started",
            "document_id": doc_id,
            "status": "processing"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summary regeneration failed: {str(e)}")


@router.post("/documents/regenerate-all-summaries")
async def regenerate_all_summaries(
    background_tasks: BackgroundTasks,
    limit: Optional[int] = None
):
    """
    Batch regenerate summaries for all documents missing them.
    """
    try:
        db_service = get_db_service()
        processing_service = get_document_processing_service()
        
        # Get all documents with missing summaries
        docs = await db_service.get_documents_missing_summaries(limit=limit)
        
        if not docs:
            return {
                "message": "No documents found with missing summaries",
                "total_documents": 0,
                "processing": False
            }
        
        # Queue all for background processing
        for doc in docs:
            doc_id = doc.get("id")
            file_path = Path(doc.get("file_path", ""))
            
            if file_path.exists():
                # Update status to processing
                await db_service.update_document(doc_id, {
                    "status": "processing",
                    "summary": None,
                    "markdown_path": None
                })
                
                # Trigger background processing
                background_tasks.add_task(
                    processing_service.process_document_sync,
                    doc_id,
                    file_path
                )
        
        return {
            "message": f"Batch regeneration started for {len(docs)} documents",
            "total_documents": len(docs),
            "processing": True
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch regeneration failed: {str(e)}")


@router.get("/documents/missing-summaries")
async def get_missing_summaries(limit: Optional[int] = None):
    """
    Get all documents that are missing summaries.
    """
    try:
        db_service = get_db_service()
        docs = await db_service.get_documents_missing_summaries(limit=limit)
        
        return {
            "count": len(docs),
            "documents": docs
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get missing summaries: {str(e)}")

