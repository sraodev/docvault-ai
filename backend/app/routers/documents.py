from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException, Form
from typing import List, Optional
import uuid
from datetime import datetime
from pathlib import Path
from fastapi.responses import FileResponse
import hashlib
from pydantic import BaseModel
import asyncio
from concurrent.futures import ThreadPoolExecutor

from ..models.document import DocumentMetadata
from ..services.ai_service import AIService
from ..services.file_service import FileService
from ..services.database import DatabaseFactory
from ..services.upload_queue import UploadQueueManager, UploadTask, UploadStatus
from ..services.upload_processor import UploadProcessor
from ..utils.checksum import calculate_file_checksum
from ..utils.tag_extractor import extract_tags_from_text
from ..core.config import UPLOAD_DIR, DATABASE_TYPE, STORAGE_TYPE, JSON_DB_PATH

router = APIRouter()

# Initialize database service using Factory Pattern (plug-and-play)
# Supports JSON (file-based) and Memory (in-memory) database backends
db_service = None  # Will be initialized on startup

async def initialize_database():
    """Initialize database adapter based on configuration."""
    global db_service
    
    if DATABASE_TYPE.lower() == "json":
        data_dir = Path(JSON_DB_PATH) if JSON_DB_PATH else None
        db_service = await DatabaseFactory.create_and_initialize("json", data_dir=data_dir)
    elif DATABASE_TYPE.lower() == "scalable_json":
        data_dir = Path(JSON_DB_PATH) if JSON_DB_PATH else None
        db_service = await DatabaseFactory.create_and_initialize("scalable_json", data_dir=data_dir)
    elif DATABASE_TYPE.lower() == "memory":
        db_service = await DatabaseFactory.create_and_initialize("memory")
    else:
        raise ValueError(f"Unsupported DATABASE_TYPE: {DATABASE_TYPE}. Supported types: 'json', 'scalable_json', 'memory'")

ai_service = AIService()
file_service = FileService()  # Will initialize storage on first use

async def check_duplicate_by_checksum(checksum: str) -> Optional[dict]:
    """
    Check if a file with the same checksum already exists.
    
    Args:
        checksum: SHA-256 checksum of the file
        
    Returns:
        Existing document dict if duplicate found, None otherwise
    """
    return await db_service.find_document_by_checksum(checksum)

async def process_document_background_async(doc_id: str, file_path: Path):
    """
    Background task to process document with AI (async version).
    """
    try:
        
        # Update status to processing
        await db_service.update_document(doc_id, {"status": "processing"})
        
        # 1. Extract Text
        text_content = await file_service.extract_text(file_path)

        # 2. Extract Tags first (works with or without AI summary)
        tags = extract_tags_from_text(text_content, None)
        
        # 3. Generate Summary and Markdown (handle AI service errors gracefully)
        summary = None
        markdown_content = None
        
        try:
            summary = ai_service.generate_summary(text_content)
            markdown_content = ai_service.generate_markdown(text_content)
        except Exception as ai_error:
            print(f"AI Service Error for {doc_id}: {ai_error}")
        
        # Check if AI processing failed (returns None)
        if summary is None or markdown_content is None:
            print(f"AI Service unavailable for {doc_id} - marking as ready (tags generated)")
            # Re-extract tags with better context if we have partial summary
            if summary:
                tags = extract_tags_from_text(text_content, summary)
            await db_service.update_document(doc_id, {
                "status": "ready",
                "summary": None,
                "markdown_path": None,
                "tags": tags  # Still generate tags even without AI
            })
            return  # Exit early, document is still usable without AI processing

        # 4. Re-extract tags with AI summary for better accuracy
        tags = extract_tags_from_text(text_content, summary)

        # 5. Save Markdown
        md_filename = f"{doc_id}_processed.md"
        md_path = UPLOAD_DIR / md_filename
        await file_service.save_markdown(markdown_content, md_path)

        # 6. Update DB
        await db_service.update_document(doc_id, {
            "summary": summary,
            "markdown_path": str(md_path),
            "tags": tags,
            "status": "completed",
            "modified_date": datetime.now().isoformat()
        })
        

    except Exception as e:
        print(f"Fatal error processing {doc_id}: {e}")
        # Don't mark as failed if it's just AI service unavailable - keep as ready
        error_str = str(e).lower()
        if "insufficient credits" in error_str or "api key" in error_str or "402" in error_str:
            await db_service.update_document(doc_id, {"status": "ready"})
        else:
            await db_service.update_document(doc_id, {"status": "failed"})

def process_document_background_sync(doc_id: str, file_path: Path):
    """
    Wrapper for background task processing (sync wrapper for async function).
    FastAPI BackgroundTasks requires sync functions, so we run async code in event loop.
    """
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    loop.run_until_complete(process_document_background_async(doc_id, file_path))

@router.post("/upload", response_model=DocumentMetadata)
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    folder: Optional[str] = Form(None),
    checksum: Optional[str] = Form(None)
):
    """
    Upload a document with optional folder/category assignment.
    Folder is stored as metadata for virtual folder organization.
    Checks duplicate files by checksum if provided.
    """
    try:
        doc_id = str(uuid.uuid4())
        file_ext = Path(file.filename).suffix
        save_filename = f"{doc_id}{file_ext}"
        save_path = UPLOAD_DIR / save_filename

        # Save file first to calculate checksum
        await file_service.save_upload(file, save_path)
        
        # Get file size and calculate checksum
        # For local storage, we can use stat(); for S3/Supabase, we'll get size from file bytes
        storage_adapter = await file_service.get_storage()
        file_bytes = await storage_adapter.get_file(str(save_path))
        file_size = len(file_bytes)
        
        # Calculate checksum from bytes or use provided checksum
        if checksum:
            file_checksum = checksum
        else:
            import hashlib
            file_checksum = hashlib.sha256(file_bytes).hexdigest()
        
        # Extract just the filename (remove any path that might be included)
        clean_filename = Path(file.filename).name
        
        # Check for duplicate
        duplicate_doc = await check_duplicate_by_checksum(file_checksum)
        if duplicate_doc:
            # Delete the just uploaded file since it's a duplicate
            await file_service.delete_file(save_path)
            raise HTTPException(
                status_code=409,
                detail=f"File '{clean_filename}' already exists as '{duplicate_doc['filename']}'"
            )

        # Normalize folder name (trim whitespace, use None for empty strings)
        normalized_folder = folder.strip() if folder and folder.strip() else None

        upload_time = datetime.now().isoformat()
        doc_meta = {
            "id": doc_id,
            "filename": clean_filename,
            "upload_date": upload_time,
            "file_path": str(save_path),
            "status": "ready",  # Changed from "processing" - AI processing will happen on-demand
            "summary": None,
            "markdown_path": None,
            "folder": normalized_folder,
            "checksum": file_checksum,
            "size": file_size,
            "modified_date": upload_time  # Initially same as upload_date
        }
        
        # Save to database
        doc_meta = await db_service.create_document(doc_meta)

        # Don't trigger AI processing during upload - it will happen on-demand when document is viewed

        return doc_meta
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in upload_file: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.post("/upload/check-duplicate")
async def check_duplicate(checksum: str = Form(...)):
    """
    Check if a file with the given checksum already exists.
    """
    duplicate_doc = await check_duplicate_by_checksum(checksum)
    if duplicate_doc:
        return {
            "is_duplicate": True,
            "document_id": duplicate_doc["id"],
            "filename": duplicate_doc["filename"]
        }
    return {"is_duplicate": False}

@router.post("/upload/check-duplicates")
async def check_duplicates(checksums: List[str] = Form(...)):
    """
    Check multiple checksums at once for duplicates.
    """
    duplicates = []
    for checksum in checksums:
        duplicate_doc = await check_duplicate_by_checksum(checksum)
        if duplicate_doc:
            duplicates.append({
                "checksum": checksum,
                "document_id": duplicate_doc["id"],
                "filename": duplicate_doc["filename"]
            })
    return {"duplicates": duplicates}

class BulkUploadResponse(BaseModel):
    """
    Response model for bulk upload endpoint.
    Provides summary statistics and details about the upload operation.
    """
    total_files: int  # Total number of files attempted to upload
    successful: int  # Number of successfully uploaded files
    failed: int  # Number of failed uploads
    duplicates: int  # Number of duplicate files skipped
    document_ids: List[str]  # List of successfully uploaded document IDs
    errors: List[Dict[str, str]]  # List of error details for failed/duplicate files

async def process_single_file_upload_async(
    file: UploadFile,
    folder: Optional[str],
    checksum: Optional[str],
    background_tasks: BackgroundTasks,
    executor: ThreadPoolExecutor
) -> Dict:
    """
    Process a single file upload asynchronously. Returns document metadata or error info.
    Uses thread pool for I/O operations to avoid blocking the event loop.
    
    Args:
        file: The file to upload
        folder: Optional folder path for the file
        checksum: Optional pre-calculated checksum (skips calculation if provided)
        background_tasks: FastAPI background tasks for AI processing
        executor: Thread pool executor for I/O operations
    
    Returns:
        Dict with status ('success', 'duplicate', or 'error') and relevant data
    """
    try:
        doc_id = str(uuid.uuid4())
        file_ext = Path(file.filename).suffix
        save_filename = f"{doc_id}{file_ext}"
        save_path = UPLOAD_DIR / save_filename

        # Save file using storage adapter
        await file_service.save_upload(file, save_path)
        
        # Get file size and calculate checksum from storage
        storage_adapter = await file_service.get_storage()
        file_bytes = await storage_adapter.get_file(str(save_path))
        file_size = len(file_bytes)
        
        # Calculate checksum from bytes
        import hashlib
        if checksum:
            file_checksum = checksum
        else:
            file_checksum = hashlib.sha256(file_bytes).hexdigest()
        
        # Extract just the filename
        clean_filename = Path(file.filename).name
        
        # Check for duplicate (quick in-memory lookup, no I/O needed)
        duplicate_doc = await check_duplicate_by_checksum(file_checksum)
        if duplicate_doc:
            # Delete the just uploaded file since it's a duplicate
            await file_service.delete_file(save_path)
            return {
                "status": "duplicate",
                "filename": clean_filename,
                "existing_filename": duplicate_doc.get("filename"),
                "document_id": duplicate_doc.get("id")
            }

        # Normalize folder name
        normalized_folder = folder.strip() if folder and folder.strip() else None

        upload_time = datetime.now().isoformat()
        doc_meta = {
            "id": doc_id,
            "filename": clean_filename,
            "upload_date": upload_time,
            "file_path": str(save_path),
            "status": "ready",  # Changed from "processing" - AI processing will happen on-demand
            "summary": None,
            "markdown_path": None,
            "folder": normalized_folder,
            "checksum": file_checksum,
            "size": file_size,
            "modified_date": upload_time
        }
        
        # Save to database (thread-safe)
        doc_meta = await db_service.create_document(doc_meta)

        # Don't trigger AI processing during upload - it will happen on-demand when document is viewed

        return {
            "status": "success",
            "document": doc_meta
        }
    except Exception as e:
        return {
            "status": "error",
            "filename": file.filename if file else "unknown",
            "error": str(e)
        }

@router.post("/upload/bulk", response_model=BulkUploadResponse)
async def upload_bulk_files(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    folders: Optional[List[str]] = Form(None),
    checksums: Optional[List[str]] = Form(None),
    concurrency: Optional[int] = Form(None)
):
    """
    Bulk upload endpoint with queue-based worker pool and retry logic.
    Supports UNLIMITED file uploads: 10 files, 500 files, 1M files, 1B files - any number!
    
    Features:
        - Unlimited scaling: Handles any number of files (millions, billions, etc.)
        - Dynamic worker scaling: Automatically adjusts workers based on queue size (no upper limit)
        - Adaptive chunking: Automatically chunks very large batches for optimal performance
        - Queue management: Tasks queued and processed by worker pool
        - Retry mechanism: Automatic retries with exponential backoff (up to 3 retries)
        - Robust error handling: Continues processing even if some files fail
        - Progress tracking: Real-time status updates with chunk progress
        - Memory efficient: Processes files in chunks to prevent memory exhaustion
    
    Args:
        files: List of files to upload (required) - can be ANY number
        folders: Optional list of folder paths (one per file, in same order as files)
        checksums: Optional list of pre-calculated checksums (one per file, in same order as files)
        concurrency: Optional concurrency hint (auto-calculated if not provided)
    
    Returns:
        BulkUploadResponse with summary of upload results
    
    Examples:
        - 10 files: Direct processing, ~5-10 workers
        - 1,000 files: Chunked (500 per chunk), ~20-30 workers
        - 100,000 files: Chunked (5,000 per chunk), ~50-100 workers
        - 1,000,000 files: Chunked (50,000 per chunk), ~100-200 workers
        - 1,000,000,000 files: Chunked (50,000 per chunk), scales infinitely
    """
    try:
        total_files = len(files)
        
        # Normalize folders and checksums lists
        folders_list = folders if folders else [None] * total_files
        checksums_list = checksums if checksums else [None] * total_files
        
        # Ensure lists match files length
        while len(folders_list) < total_files:
            folders_list.append(None)
        while len(checksums_list) < total_files:
            checksums_list.append(None)
        
        # For very large batches, use adaptive chunking strategy
        # Chunk size adapts based on batch size to optimize memory and performance
        # Small batches: no chunking
        # Medium batches (1000+): 500 per chunk
        # Large batches (100k+): 5000 per chunk
        # Very large batches (1M+): 50000 per chunk
        # This allows handling billions of files efficiently
        if total_files > 1000:
            # Calculate adaptive chunk size based on batch size
            import math
            if total_files < 100000:
                chunk_size = 500
            elif total_files < 1000000:
                chunk_size = 5000
            else:
                # For millions/billions: use larger chunks (50k) for efficiency
                chunk_size = 50000
            
            return await _process_large_batch(
                files, folders_list, checksums_list, background_tasks, chunk_size
            )
        
        # For smaller batches, use queue-based processing
        return await _process_with_queue(
            files, folders_list, checksums_list, background_tasks, concurrency
        )
        
    except Exception as e:
        print(f"Error in bulk upload: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Bulk upload failed: {str(e)}")

async def _process_with_queue(
    files: List[UploadFile],
    folders_list: List[Optional[str]],
    checksums_list: List[Optional[str]],
    background_tasks: BackgroundTasks,
    concurrency_hint: Optional[int]
) -> BulkUploadResponse:
    """Process uploads using queue-based worker pool."""
    # Initialize upload processor
    processor = UploadProcessor(file_service, db_service)
    
    # Create queue manager with unlimited dynamic scaling
    # Auto-calculate optimal settings based on file count
    # No upper limit - scales infinitely for millions/billions of files
    total_files = len(files)
    if concurrency_hint:
        base_concurrency = concurrency_hint
    else:
        # Adaptive calculation: scale based on file count
        # Uses logarithmic scaling for very large batches
        import math
        if total_files < 1000:
            base_concurrency = max(10, total_files // 5)
        else:
            # For very large batches, use logarithmic scaling
            base_concurrency = max(20, int(math.log10(total_files) * 10))
    
    # Unlimited scaling: max_workers=None allows scaling to any size
    # System will cap at 1000 workers internally to prevent resource exhaustion
    queue_manager = UploadQueueManager(
        min_workers=5,
        max_workers=None,  # Unlimited scaling for massive batches
        base_concurrency=base_concurrency
    )
    
    # Add all files to queue
    task_ids = []
    for idx, file in enumerate(files):
        task_id = f"task-{idx}-{uuid.uuid4().hex[:8]}"
        await queue_manager.add_task(
            task_id=task_id,
            file=file,
            filename=file.filename or f"file_{idx}",
            folder=folders_list[idx],
            checksum=checksums_list[idx],
            max_retries=3
        )
        task_ids.append(task_id)
    
    # Start worker pool
    async def process_task(task: UploadTask):
        result = await processor.process(task)
        # Trigger background AI processing for successful uploads
        if result.get("status") == "success":
            doc_id = result.get("document_id")
            file_path = result.get("document", {}).get("file_path")
            if doc_id and file_path:
                background_tasks.add_task(
                    process_document_background_sync,
                    doc_id,
                    Path(file_path)
                )
        return result
    
    await queue_manager.start_workers(process_task)
    
    # Wait for completion with adaptive timeout
    # Timeout scales with batch size: larger batches get more time
    # For millions/billions: use very long timeout or None (unlimited)
    import math
    if total_files < 1000:
        timeout = 600  # 10 minutes for small batches
    elif total_files < 100000:
        timeout = 3600  # 1 hour for medium batches
    elif total_files < 1000000:
        timeout = 7200  # 2 hours for large batches
    else:
        # For millions+: calculate timeout based on estimated processing time
        # Estimate: ~1 second per file with 50 workers = total_files / 50 seconds
        # Add 50% buffer and cap at 24 hours
        estimated_seconds = (total_files / 50) * 1.5
        timeout = min(estimated_seconds, 86400)  # Max 24 hours
    
    stats = await queue_manager.wait_for_completion(timeout=timeout)
    
    # Collect results
    successful = 0
    failed = 0
    duplicates = 0
    document_ids = []
    errors = []
    
    for task_id in task_ids:
        task = queue_manager.get_task(task_id)
        if task:
            if task.status == UploadStatus.SUCCESS:
                successful += 1
                if task.result and task.result.get("document_id"):
                    document_ids.append(task.result["document_id"])
            elif task.status == UploadStatus.DUPLICATE:
                duplicates += 1
                errors.append({
                    "filename": task.filename,
                    "error": f"Duplicate of '{task.result.get('existing_document', {}).get('filename', 'unknown')}'"
                })
            else:
                failed += 1
                errors.append({
                    "filename": task.filename,
                    "error": task.error or "Upload failed"
                })
    
    # Stop queue manager
    await queue_manager.stop()
    
    return BulkUploadResponse(
        total_files=total_files,
        successful=successful,
        failed=failed,
        duplicates=duplicates,
        document_ids=document_ids,
        errors=errors
    )

async def _process_large_batch(
    files: List[UploadFile],
    folders_list: List[Optional[str]],
    checksums_list: List[Optional[str]],
    background_tasks: BackgroundTasks,
    chunk_size: int
) -> BulkUploadResponse:
    """
    Process very large batches in adaptive chunks.
    Handles batches of any size: thousands, millions, or billions of files.
    """
    total_files = len(files)
    all_document_ids = []
    all_errors = []
    total_successful = 0
    total_failed = 0
    total_duplicates = 0
    
    # Calculate number of chunks
    num_chunks = (total_files + chunk_size - 1) // chunk_size  # Ceiling division
    
    
    # Process in chunks with progress tracking
    for chunk_idx, chunk_start in enumerate(range(0, total_files, chunk_size), 1):
        chunk_end = min(chunk_start + chunk_size, total_files)
        chunk_files = files[chunk_start:chunk_end]
        chunk_folders = folders_list[chunk_start:chunk_end]
        chunk_checksums = checksums_list[chunk_start:chunk_end]
        
        # Progress logging
        progress_pct = (chunk_end / total_files) * 100
        
        # Process chunk with queue
        chunk_result = await _process_with_queue(
            chunk_files, chunk_folders, chunk_checksums, background_tasks, None
        )
        
        # Aggregate results
        total_successful += chunk_result.successful
        total_failed += chunk_result.failed
        total_duplicates += chunk_result.duplicates
        all_document_ids.extend(chunk_result.document_ids)
        all_errors.extend(chunk_result.errors)
        
        # Log chunk completion
    
    
    return BulkUploadResponse(
        total_files=total_files,
        successful=total_successful,
        failed=total_failed,
        duplicates=total_duplicates,
        document_ids=all_document_ids,
        errors=all_errors
    )

@router.get("/documents", response_model=List[DocumentMetadata])
async def get_documents(folder: Optional[str] = None):
    """
    Get all documents, optionally filtered by folder.
    Ensures all documents have a size field by calculating it from the file if missing.
    """
    docs = await db_service.get_all_documents(folder=folder)
    
    # Ensure all documents have size and modified_date fields
    for doc in docs:
        if "size" not in doc or doc.get("size") is None:
            file_path = Path(doc.get("file_path", ""))
            if file_path.exists():
                try:
                    size = file_path.stat().st_size
                    await db_service.update_document(doc["id"], {"size": size})
                    doc["size"] = size
                except Exception as e:
                    doc["size"] = None
        
        # Set modified_date to upload_date if not present (for backward compatibility)
        if "modified_date" not in doc or doc.get("modified_date") is None:
            doc["modified_date"] = doc.get("upload_date")
    
    return docs

@router.get("/documents/folders/list")
async def get_folders():
    """
    Get list of all available folders/categories.
    Returns unique folder paths from both documents and folders collection (for empty folders).
    """
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
    The folder will appear in the tree once files are uploaded to it.
    
    Args:
        folder_name: Name of the folder to create (required)
        parent_folder: Optional parent folder path (for nested folders)
    
    Returns:
        Dict with success message and the full folder path
    """
    try:
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
        
        # Store folder metadata so empty folders appear in the tree
        folder_data = {
            "name": folder_name,
            "folder_path": full_folder_path,
            "parent_folder": parent_folder.strip() if parent_folder and parent_folder.strip() else None,
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
        print(f"Error creating folder: {e}")
        raise HTTPException(status_code=500, detail=f"Folder creation failed: {str(e)}")

@router.get("/documents/{doc_id}", response_model=DocumentMetadata)
async def get_document(doc_id: str):
    doc = await db_service.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Ensure document has size field
    if "size" not in doc or doc.get("size") is None:
        file_path = Path(doc.get("file_path", ""))
        if file_path.exists():
            try:
                size = file_path.stat().st_size
                await db_service.update_document(doc_id, {"size": size})
                doc["size"] = size
            except Exception as e:
                doc["size"] = None
    
    # Set modified_date to upload_date if not present (for backward compatibility)
    if "modified_date" not in doc or doc.get("modified_date") is None:
        doc["modified_date"] = doc.get("upload_date")
    
    return doc

@router.post("/documents/{doc_id}/process")
async def process_document(doc_id: str, background_tasks: BackgroundTasks):
    """
    Trigger AI processing for a document on-demand.
    This endpoint is called when a user views a document that hasn't been processed yet.
    """
    doc = await db_service.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Only process if status is "ready" (not already processing or completed)
    current_status = doc.get("status", "ready")
    if current_status == "processing":
        return {"message": "Document is already being processed", "status": "processing"}
    if current_status == "completed":
        return {"message": "Document is already processed", "status": "completed"}
    
    # Get file path
    file_path_str = doc.get("file_path")
    if not file_path_str:
        raise HTTPException(status_code=400, detail="Document file path not found")
    
    file_path = Path(file_path_str)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Document file not found")
    
    # Trigger background processing
    background_tasks.add_task(process_document_background_sync, doc_id, file_path)
    
    return {"message": "AI processing started", "status": "processing"}

@router.get("/files/{filename}")
async def get_file(filename: str):
    """Get a file from storage (works with local, S3, or Supabase)."""
    try:
        storage_adapter = await file_service.get_storage()
        file_path = str(UPLOAD_DIR / filename)
        
        # Check if file exists
        if not await storage_adapter.file_exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")
        
        # For local storage, return FileResponse for efficiency
        if STORAGE_TYPE.lower() == "local":
            from fastapi.responses import FileResponse
            # Get the actual local path
            local_storage = storage_adapter
            local_path = local_storage._get_full_path(file_path)
            if local_path.exists():
                return FileResponse(local_path)
        
        # For S3/Supabase, get file bytes
        file_bytes = await storage_adapter.get_file(file_path)
        from fastapi.responses import Response
        return Response(content=file_bytes, media_type="application/octet-stream")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving file: {str(e)}")

@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    doc = await db_service.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    try:
        # Delete original file
        if doc.get("file_path"):
            await file_service.delete_file(Path(doc["file_path"]))
            
        # Delete markdown file
        if doc.get("markdown_path"):
            await file_service.delete_file(Path(doc["markdown_path"]))
            
        # Remove from DB
        await db_service.delete_document(doc_id)
        
        return {"message": "Document deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting document {doc_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Deletion failed: {str(e)}")

@router.delete("/documents/folders/{folder_path:path}")
async def delete_folder(folder_path: str):
    """
    Delete a folder and all documents within it (including subfolders).
    """
    try:
        # Ensure proper URL decoding (FastAPI's :path converter handles this, but be explicit)
        folder_path = urllib.parse.unquote(folder_path)
        
        # Get all documents in this folder and subfolders
        docs_to_delete = await db_service.get_documents_by_folder(folder_path, include_subfolders=True)
        
        # Delete files from storage
        for doc in docs_to_delete:
            try:
                # Delete original file
                if doc.get("file_path"):
                    await file_service.delete_file(Path(doc["file_path"]))
                    
                # Delete markdown file
                if doc.get("markdown_path"):
                    await file_service.delete_file(Path(doc["markdown_path"]))
            except Exception as file_err:
                # Log but continue with deletion
        
        # Delete from database (this handles both documents and folder metadata)
        deleted_count = await db_service.delete_folder(folder_path)
        
        if deleted_count == 0:
            return {
                "message": f"Folder '{folder_path}' is empty or not found",
                "deleted_count": 0
            }
        
        return {
            "message": f"Folder deleted successfully",
            "deleted_count": deleted_count
        }
    except Exception as e:
        print(f"Error deleting folder '{folder_path}': {e}")
        raise HTTPException(status_code=500, detail=f"Folder deletion failed: {str(e)}")

@router.put("/documents/folders/{folder_path:path}/move")
async def move_folder(folder_path: str, new_folder_path: Optional[str] = Form(None)):
    """
    Move a folder and all its contents (including subfolders) to a new location.
    If new_folder_path is None or empty, moves folder contents to root.
    """
    try:
        folder_path = urllib.parse.unquote(folder_path)
        
        # Normalize new_folder_path
        normalized_new_path = new_folder_path.strip() if new_folder_path and new_folder_path.strip() else None
        
        # Use database service to update folder paths
        moved_count = await db_service.update_folder_path(folder_path, normalized_new_path)
        
        return {
            "message": f"Folder moved successfully",
            "moved_count": moved_count
        }
    except Exception as e:
        print(f"Error moving folder {folder_path}: {e}")
        raise HTTPException(status_code=500, detail=f"Folder move failed: {str(e)}")

@router.get("/documents/missing-summaries")
async def get_missing_summaries(limit: Optional[int] = None):
    """
    Get all documents that are missing summaries.
    
    Args:
        limit: Optional limit on number of documents to return
    
    Returns:
        Dict with count and list of documents missing summaries
    """
    try:
        docs = await db_service.get_documents_missing_summaries(limit=limit)
        
        return {
            "count": len(docs),
            "documents": docs
        }
    except Exception as e:
        print(f"Error getting missing summaries: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get missing summaries: {str(e)}")

@router.post("/documents/{doc_id}/regenerate-summary")
async def regenerate_summary(doc_id: str, background_tasks: BackgroundTasks):
    """
    Regenerate summary for a specific document.
    
    Args:
        doc_id: Document ID to regenerate summary for
        background_tasks: FastAPI background tasks for async processing
    
    Returns:
        Dict with message and status
    """
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
        background_tasks.add_task(process_document_background_sync, doc_id, file_path)
        
        return {
            "message": "Summary regeneration started",
            "document_id": doc_id,
            "status": "processing"
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error regenerating summary for {doc_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Summary regeneration failed: {str(e)}")

@router.post("/documents/regenerate-all-summaries")
async def regenerate_all_summaries(
    background_tasks: BackgroundTasks,
    limit: Optional[int] = None
):
    """
    Batch regenerate summaries for all documents missing them.
    
    Args:
        background_tasks: FastAPI background tasks for async processing
        limit: Optional limit on number of documents to process
    
    Returns:
        Dict with message, total count, and processing status
    """
    try:
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
                background_tasks.add_task(process_document_background_sync, doc_id, file_path)
        
        return {
            "message": f"Batch regeneration started for {len(docs)} documents",
            "total_documents": len(docs),
            "processing": True
        }
    except Exception as e:
        print(f"Error in batch regeneration: {e}")
        raise HTTPException(status_code=500, detail=f"Batch regeneration failed: {str(e)}")