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
from ..core.config import UPLOAD_DIR

router = APIRouter()

# In-memory database (Mock)
documents_db: Dict[str, dict] = {}

ai_service = AIService()
file_service = FileService()

def calculate_file_checksum(file_path: Path) -> str:
    """Calculate SHA-256 checksum of a file"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def check_duplicate_by_checksum(checksum: str) -> Optional[dict]:
    """Check if a file with the same checksum already exists"""
    for doc_id, doc in documents_db.items():
        if doc.get("checksum") == checksum:
            return doc
    return None

def process_document_background(doc_id: str, file_path: Path):
    """
    Background task to process document with AI.
    """
    try:
        print(f"Processing document {doc_id}...")
        
        # 1. Extract Text
        text_content = file_service.extract_text(file_path)

        # 2. Generate Summary and Markdown
        summary = ai_service.generate_summary(text_content)
        markdown_content = ai_service.generate_markdown(text_content)

        # 3. Save Markdown
        md_filename = f"{doc_id}_processed.md"
        md_path = UPLOAD_DIR / md_filename
        file_service.save_markdown(markdown_content, md_path)

        # 4. Update DB
        if doc_id in documents_db:
            documents_db[doc_id]["summary"] = summary
            documents_db[doc_id]["markdown_path"] = str(md_path)
            documents_db[doc_id]["status"] = "completed"
            documents_db[doc_id]["modified_date"] = datetime.now().isoformat()
        
        print(f"Finished processing {doc_id}")

    except Exception as e:
        print(f"Fatal error processing {doc_id}: {e}")
        if doc_id in documents_db:
            documents_db[doc_id]["status"] = "failed"

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
        file_service.save_upload(file, save_path)
        
        # Get file size
        file_size = save_path.stat().st_size
        
        # Calculate checksum
        file_checksum = checksum or calculate_file_checksum(save_path)
        
        # Extract just the filename (remove any path that might be included)
        clean_filename = Path(file.filename).name
        
        # Check for duplicate
        duplicate_doc = check_duplicate_by_checksum(file_checksum)
        if duplicate_doc:
            # Delete the just uploaded file since it's a duplicate
            file_service.delete_file(save_path)
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
        
        documents_db[doc_id] = doc_meta

        # Trigger background processing
        background_tasks.add_task(process_document_background, doc_id, save_path)

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
    duplicate_doc = check_duplicate_by_checksum(checksum)
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
        duplicate_doc = check_duplicate_by_checksum(checksum)
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

        # Save file in thread pool (I/O operation)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(executor, file_service.save_upload, file, save_path)
        
        # Get file size
        file_size = await loop.run_in_executor(executor, lambda: save_path.stat().st_size)
        
        # Calculate checksum in thread pool (CPU-intensive)
        if checksum:
            file_checksum = checksum
        else:
            file_checksum = await loop.run_in_executor(executor, calculate_file_checksum, save_path)
        
        # Extract just the filename
        clean_filename = Path(file.filename).name
        
        # Check for duplicate (quick in-memory lookup, no I/O needed)
        duplicate_doc = check_duplicate_by_checksum(file_checksum)
        if duplicate_doc:
            # Delete the just uploaded file since it's a duplicate
            await loop.run_in_executor(executor, file_service.delete_file, save_path)
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
        
        # Thread-safe database update (in-memory dict, but still use lock if needed)
        documents_db[doc_id] = doc_meta

        # Trigger background processing
        background_tasks.add_task(process_document_background, doc_id, save_path)

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
    docs = list(documents_db.values())
    
    # Filter by folder if specified
    if folder:
        docs = [doc for doc in docs if doc.get("folder") == folder]
    
    # Ensure all documents have size and modified_date fields
    for doc in docs:
        if "size" not in doc or doc.get("size") is None:
            file_path = Path(doc.get("file_path", ""))
            if file_path.exists():
                try:
                    doc["size"] = file_path.stat().st_size
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
    Returns unique folder names from all documents.
    """
    folders = set()
    for doc in documents_db.values():
        folder = doc.get("folder")
        if folder:
            folders.add(folder)
    return {"folders": sorted(list(folders))}

@router.get("/documents/{doc_id}", response_model=DocumentMetadata)
async def get_document(doc_id: str):
    if doc_id not in documents_db:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc = documents_db[doc_id]
    
    # Ensure document has size field
    if "size" not in doc or doc.get("size") is None:
        file_path = Path(doc.get("file_path", ""))
        if file_path.exists():
            try:
                doc["size"] = file_path.stat().st_size
            except Exception as e:
                print(f"Error calculating size for {doc_id}: {e}")
                doc["size"] = None
    
    # Set modified_date to upload_date if not present (for backward compatibility)
    if "modified_date" not in doc or doc.get("modified_date") is None:
        doc["modified_date"] = doc.get("upload_date")
    
    return doc

@router.get("/files/{filename}")
async def get_file(filename: str):
    file_path = UPLOAD_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)

@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    if doc_id not in documents_db:
        raise HTTPException(status_code=404, detail="Document not found")
    
    try:
        doc = documents_db[doc_id]
        
        # Delete original file
        if doc.get("file_path"):
            file_service.delete_file(Path(doc["file_path"]))
            
        # Delete markdown file
        if doc.get("markdown_path"):
            file_service.delete_file(Path(doc["markdown_path"]))
            
        # Remove from DB
        del documents_db[doc_id]
        
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
        
        deleted_count = 0
        doc_ids_to_delete = []
        
        # Find all documents in this folder and subfolders
        for doc_id, doc in documents_db.items():
            doc_folder = doc.get("folder")
            if doc_folder:
                # Check if document belongs to this folder or any subfolder
                if doc_folder == folder_path or doc_folder.startswith(f"{folder_path}/"):
                    doc_ids_to_delete.append(doc_id)
        
        if len(doc_ids_to_delete) == 0:
            return {
                "message": f"Folder '{folder_path}' is empty or not found",
                "deleted_count": 0
            }
        
        # Delete all documents in the folder
        for doc_id in doc_ids_to_delete:
            doc = documents_db[doc_id]
            
            try:
                # Delete original file
                if doc.get("file_path"):
                    file_service.delete_file(Path(doc["file_path"]))
                    
                # Delete markdown file
                if doc.get("markdown_path"):
                    file_service.delete_file(Path(doc["markdown_path"]))
            except Exception as file_err:
                # Log but continue with deletion
                print(f"Warning: Error deleting files for {doc_id}: {file_err}")
            
            # Remove from DB
            del documents_db[doc_id]
            deleted_count += 1
        
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
        moved_count = 0
        
        # Find all documents in this folder and subfolders
        for doc_id, doc in documents_db.items():
            doc_folder = doc.get("folder")
            if doc_folder:
                # Check if document belongs to this folder or any subfolder
                if doc_folder == folder_path or doc_folder.startswith(f"{folder_path}/"):
                    # Calculate new folder path
                    if doc_folder == folder_path:
                        # Root level files in the folder go to new location
                        new_doc_folder = new_folder_path.strip() if new_folder_path and new_folder_path.strip() else None
                    else:
                        # Subfolder files: replace the old folder path prefix with new one
                        relative_path = doc_folder[len(folder_path) + 1:]  # Remove old folder path prefix
                        if new_folder_path and new_folder_path.strip():
                            new_doc_folder = f"{new_folder_path.strip()}/{relative_path}"
                        else:
                            new_doc_folder = relative_path if relative_path else None
                    
                    # Update document folder
                    doc["folder"] = new_doc_folder.strip() if new_doc_folder else None
                    moved_count += 1
        
        return {
            "message": f"Folder moved successfully",
            "moved_count": moved_count
        }
    except Exception as e:
        print(f"Error moving folder {folder_path}: {e}")
        raise HTTPException(status_code=500, detail=f"Folder move failed: {str(e)}")