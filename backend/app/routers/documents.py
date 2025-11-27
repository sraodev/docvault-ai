from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException, Form
from typing import List, Dict, Optional
import uuid
from datetime import datetime
from pathlib import Path
from fastapi.responses import FileResponse
import hashlib
import urllib.parse
from pydantic import BaseModel
import asyncio
from concurrent.futures import ThreadPoolExecutor

from ..models.document import DocumentMetadata
from ..services.ai_service import AIService
from ..services.file_service import FileService
from ..services.database import DatabaseFactory
from ..core.config import UPLOAD_DIR, DATABASE_TYPE, STORAGE_TYPE, JSON_DB_PATH
from pathlib import Path

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
    elif DATABASE_TYPE.lower() == "memory":
        db_service = await DatabaseFactory.create_and_initialize("memory")
    else:
        raise ValueError(f"Unsupported DATABASE_TYPE: {DATABASE_TYPE}. Supported types: 'json', 'memory'")

ai_service = AIService()
file_service = FileService()  # Will initialize storage on first use

def calculate_file_checksum(file_path: Path) -> str:
    """Calculate SHA-256 checksum of a file"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

async def check_duplicate_by_checksum(checksum: str) -> Optional[dict]:
    """Check if a file with the same checksum already exists"""
    return await db_service.find_document_by_checksum(checksum)

async def process_document_background_async(doc_id: str, file_path: Path):
    """
    Background task to process document with AI (async version).
    """
    try:
        print(f"Processing document {doc_id}...")
        
        # 1. Extract Text
        text_content = await file_service.extract_text(file_path)

        # 2. Generate Summary and Markdown
        summary = ai_service.generate_summary(text_content)
        markdown_content = ai_service.generate_markdown(text_content)

        # 3. Save Markdown
        md_filename = f"{doc_id}_processed.md"
        md_path = UPLOAD_DIR / md_filename
        await file_service.save_markdown(markdown_content, md_path)

        # 4. Update DB
        await db_service.update_document(doc_id, {
            "summary": summary,
            "markdown_path": str(md_path),
            "status": "completed",
            "modified_date": datetime.now().isoformat()
        })
        
        print(f"Finished processing {doc_id}")

    except Exception as e:
        print(f"Fatal error processing {doc_id}: {e}")
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
        storage_adapter = await file_service.storage
        file_bytes = await storage_adapter.get_file(str(save_path))
        file_size = len(file_bytes)
        
        # Calculate checksum from bytes
        import hashlib
        file_checksum = checksum or hashlib.sha256(file_bytes).hexdigest()
        
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
            "status": "processing",
            "summary": None,
            "markdown_path": None,
            "folder": normalized_folder,
            "checksum": file_checksum,
            "size": file_size,
            "modified_date": upload_time  # Initially same as upload_date
        }
        
        # Save to database
        doc_meta = await db_service.create_document(doc_meta)

        # Trigger background processing (async function)
        background_tasks.add_task(process_document_background_sync, doc_id, save_path)

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
        storage_adapter = await file_service.storage
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
            "status": "processing",
            "summary": None,
            "markdown_path": None,
            "folder": normalized_folder,
            "checksum": file_checksum,
            "size": file_size,
            "modified_date": upload_time
        }
        
        # Save to database (thread-safe)
        doc_meta = await db_service.create_document(doc_meta)

        # Trigger background processing (async function)
        background_tasks.add_task(process_document_background_sync, doc_id, save_path)

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
    concurrency: int = 10
):
    """
    Bulk upload endpoint for multiple files and folders with parallel processing.
    Supports uploading 500+ files efficiently in a single request with concurrent processing.
    
    Args:
        files: List of files to upload (required)
        folders: Optional list of folder paths (one per file, in same order as files)
        checksums: Optional list of pre-calculated checksums (one per file, in same order as files)
        concurrency: Number of concurrent uploads (default: 10, max recommended: 20)
    
    Returns:
        BulkUploadResponse with summary of upload results including:
        - total_files: Total number of files attempted
        - successful: Number of successfully uploaded files
        - failed: Number of failed uploads
        - duplicates: Number of duplicate files skipped
        - document_ids: List of successfully uploaded document IDs
        - errors: List of error details for failed/duplicate files
    
    Features:
        - Parallel processing: Files upload concurrently (not sequentially)
        - Non-blocking: Each file doesn't block the next
        - Efficient duplicate checks: Checksums verified during upload, not before
        - Batch processing: All files in single HTTP request
    
    Example:
        POST /upload/bulk
        FormData:
            files: [file1.pdf, file2.docx, ...]
            folders: ["folder1", "folder1/subfolder", ...]
            checksums: ["hash1", "hash2", ...]  # Optional, speeds up processing
    """
    try:
        total_files = len(files)
        successful = 0
        failed = 0
        duplicates = 0
        document_ids = []
        errors = []
        
        # Normalize folders and checksums lists to match files length
        folders_list = folders if folders else [None] * total_files
        checksums_list = checksums if checksums else [None] * total_files
        
        # Ensure lists match files length (pad with None if needed)
        while len(folders_list) < total_files:
            folders_list.append(None)
        while len(checksums_list) < total_files:
            checksums_list.append(None)
        
        # Create thread pool executor for I/O operations
        executor = ThreadPoolExecutor(max_workers=concurrency * 2)  # More workers for I/O
        
        # Process files in parallel batches
        semaphore = asyncio.Semaphore(concurrency)  # Limit concurrent uploads
        
        async def process_with_semaphore(file: UploadFile, folder_path: Optional[str], checksum: Optional[str], idx: int):
            async with semaphore:
                return await process_single_file_upload_async(file, folder_path, checksum, background_tasks, executor)
        
        # Create tasks for all files (they will execute concurrently up to concurrency limit)
        tasks = [
            process_with_semaphore(files[idx], folders_list[idx], checksums_list[idx], idx)
            for idx in range(total_files)
        ]
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results and aggregate statistics
        # Results can be success dicts, error dicts, or Exception objects
        for result in results:
            if isinstance(result, Exception):
                # Handle exceptions that occurred during upload
                failed += 1
                errors.append({
                    "filename": "unknown",
                    "error": str(result)
                })
            elif result["status"] == "success":
                # Successful upload - add document ID to results
                successful += 1
                document_ids.append(result["document"]["id"])
            elif result["status"] == "duplicate":
                # Duplicate file detected - skip and record
                duplicates += 1
                errors.append({
                    "filename": result["filename"],
                    "error": f"Duplicate of '{result['existing_filename']}'"
                })
            else:
                # Other errors (file save failures, etc.)
                failed += 1
                errors.append({
                    "filename": result.get("filename", "unknown"),
                    "error": result.get("error", "Unknown error")
                })
        
        # Shutdown executor (don't wait for pending tasks to avoid blocking)
        executor.shutdown(wait=False)
        
        return BulkUploadResponse(
            total_files=total_files,
            successful=successful,
            failed=failed,
            duplicates=duplicates,
            document_ids=document_ids,
            errors=errors
        )
    except Exception as e:
        print(f"Error in bulk upload: {e}")
        raise HTTPException(status_code=500, detail=f"Bulk upload failed: {str(e)}")

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
                    print(f"Error calculating size for {doc.get('id')}: {e}")
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
                print(f"Error calculating size for {doc_id}: {e}")
                doc["size"] = None
    
    # Set modified_date to upload_date if not present (for backward compatibility)
    if "modified_date" not in doc or doc.get("modified_date") is None:
        doc["modified_date"] = doc.get("upload_date")
    
    return doc

@router.get("/files/{filename}")
async def get_file(filename: str):
    """Get a file from storage (works with local, S3, or Supabase)."""
    try:
        storage_adapter = await file_service.storage
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
                print(f"Warning: Error deleting files for {doc['id']}: {file_err}")
        
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