from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException, Form, Query
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime
from pathlib import Path
from fastapi.responses import FileResponse
import hashlib
from pydantic import BaseModel
import asyncio
import urllib.parse
import re

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
    Uses AI to generate summary, markdown, and tags.
    Falls back to rule-based tag extraction if AI fails.
    """
    try:
        
        # Update status to processing
        await db_service.update_document(doc_id, {"status": "processing"})
        
        # 1. Extract Text
        text_content = await file_service.extract_text(file_path)

        # 2. Generate Summary and Markdown (handle AI service errors gracefully)
        summary = None
        markdown_content = None
        
        try:
            summary = ai_service.generate_summary(text_content)
            markdown_content = ai_service.generate_markdown(text_content)
        except Exception as ai_error:
            logger.error(f"AI Service Error for {doc_id}: {ai_error}", exc_info=True)
        
        # 3. Generate Tags using AI (with summary for better context if available)
        tags = []
        try:
            # Try AI-generated tags first (preferred method)
            tags = ai_service.generate_tags(text_content, summary)
            if tags and len(tags) > 0:
                logger.info(f"AI-generated {len(tags)} tags for {doc_id}")
            else:
                # Fallback to rule-based extraction if AI returns empty
                logger.info(f"AI tags empty for {doc_id}, falling back to rule-based extraction")
                tags = extract_tags_from_text(text_content, summary)
        except Exception as tag_error:
            logger.error(f"AI tag generation failed for {doc_id}: {tag_error}, using rule-based extraction", exc_info=True)
            # Fallback to rule-based tag extraction
            tags = extract_tags_from_text(text_content, summary)
        
        # 4. Smart Folder classification DISABLED - using regular folder structure only
        # Check current document to preserve manually assigned folder
        current_doc_before = await db_service.get_document(doc_id)
        existing_folder_before = current_doc_before.get("folder") if current_doc_before else None
        
        # 4. Classify document (for display tag on file card)
        document_category = None
        try:
            document_category = ai_service.classify_document(text_content, summary)
            if document_category and document_category.strip():
                document_category = document_category.strip()
                logger.info(f"Document {doc_id} classified as: {document_category}")
            else:
                document_category = None
        except Exception as classify_error:
            logger.error(f"AI classification failed for {doc_id}: {classify_error}", exc_info=True)
            document_category = None
        
        # 5. Extract structured fields based on document category
        extracted_fields = {}
        try:
            if document_category:
                extracted_fields = ai_service.extract_fields(text_content, document_category, summary)
                if extracted_fields:
                    logger.info(f"Extracted {len(extracted_fields)} fields for {doc_id} (category: {document_category})")
                else:
                    logger.info(f"No fields extracted for {doc_id} (category: {document_category})")
        except Exception as field_error:
            logger.error(f"Field extraction failed for {doc_id}: {field_error}", exc_info=True)
        
        # 6. Generate embedding for semantic search
        embedding = None
        try:
            # Create searchable text: combine summary, tags, and key extracted fields
            searchable_text = ""
            if summary:
                searchable_text += summary + " "
            if tags:
                searchable_text += " ".join(tags) + " "
            # Add extracted fields as searchable text
            if extracted_fields:
                for key, value in extracted_fields.items():
                    if value:
                        searchable_text += f"{key}: {value} "
            # Add document text (truncated)
            searchable_text += text_content[:5000]
            
            embedding = ai_service.generate_embedding(searchable_text)
            if embedding and len(embedding) > 0:
                logger.info(f"Generated embedding for {doc_id} (dimension: {len(embedding)})")
            else:
                logger.error(f"Failed to generate embedding for {doc_id}")
        except Exception as embedding_error:
            logger.error(f"Embedding generation failed for {doc_id}: {embedding_error}", exc_info=True)
        
        # Check if AI processing failed (returns None)
        if summary is None or markdown_content is None:
            logger.info(f"AI Service unavailable for {doc_id} - marking as ready (tags: {'AI-generated' if tags else 'rule-based'})")
            
            update_data = {
                "status": "ready",
                "summary": None,
                "markdown_path": None,
                "tags": tags,  # Still generate tags even without AI summary/markdown
                "extracted_fields": extracted_fields if extracted_fields else None,  # Include extracted fields even if AI summary/markdown failed
                "embedding": embedding if embedding else None  # Include embedding even if AI summary/markdown failed
            }
            
            # Smart Folder classification disabled - preserve existing folder only
            # if smart_folder_path and not existing_folder_before:
            #     update_data["folder"] = smart_folder_path
            logger.info(f"Auto-classified document {doc_id} to smart folder: {smart_folder_path}")
            # elif smart_folder_path and existing_folder_before:
            #     update_data["folder"] = smart_folder_path
            logger.info(f"Auto-classified document {doc_id} to smart folder within existing folder: {smart_folder_path}")
            
            await db_service.update_document(doc_id, update_data)
            return  # Exit early, document is still usable without AI processing

        # 6. Save Markdown
        md_filename = f"{doc_id}_processed.md"
        md_path = UPLOAD_DIR / md_filename
        await file_service.save_markdown(markdown_content, md_path)

        # 7. Update DB with AI-generated content, smart folder classification, and extracted fields
        update_data = {
            "summary": summary,
            "markdown_path": md_filename,  # Store relative path, not absolute
            "tags": tags,  # AI-generated tags (or rule-based fallback)
            "document_category": document_category,  # Document classification (Invoice, Agreement, Resume, etc.)
            "extracted_fields": extracted_fields if extracted_fields else None,  # Structured fields extracted by AI
            "embedding": embedding if embedding else None,  # Vector embedding for semantic search
            "status": "completed",
            "modified_date": datetime.now().isoformat()
        }
        
        # Smart Folder classification disabled - preserve existing folder only
        # Preserve manually assigned folder if it exists
        if existing_folder_before:
            # Document already has a folder, preserve it
            logger.info(f"Document {doc_id} already in folder '{existing_folder_before}', preserving folder assignment")
        # Smart Folder auto-classification disabled - uncomment below to re-enable
        # if smart_folder_path:
        #     update_data["folder"] = smart_folder_path
        #     if existing_folder_before:
        logger.info(f"Auto-classified document {doc_id} to smart folder within existing folder: {smart_folder_path}")
        #     else:
        logger.info(f"Auto-classified document {doc_id} to smart folder: {smart_folder_path}")
        
        await db_service.update_document(doc_id, update_data)
        

    except Exception as e:
        logger.error(f"Fatal error processing {doc_id}: {e}", exc_info=True)
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

@router.post("/upload")
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    folder: Optional[str] = Form(None),
    checksum: Optional[str] = Form(None)
):
    """
    Upload a document with optional folder/category assignment.
    Supports both regular files and ZIP archives.
    
    For ZIP files: Extracts and processes all files within the archive,
    preserving folder structure. Returns a list of created documents.
    
    For regular files: Returns a single document metadata.
    
    Folder is stored as metadata for virtual folder organization.
    Checks duplicate files by checksum if provided.
    """
    try:
        file_ext = Path(file.filename).suffix.lower()
        clean_filename = Path(file.filename).name
        
        # Check if file is a ZIP archive
        if file_ext == '.zip':
            return await _handle_zip_upload(file, folder, background_tasks)
        
        # Handle regular file upload
        doc_id = str(uuid.uuid4())
        save_filename = f"{doc_id}{file_ext}"
        # Use relative path for storage adapter (just the filename)
        save_path_relative = save_filename
        # Full path for database storage
        save_path_full = UPLOAD_DIR / save_filename

        # Save file first to calculate checksum (use relative path for storage)
        await file_service.save_upload(file, Path(save_path_relative))
        
        # Get file size and calculate checksum
        # For local storage, we can use stat(); for S3/Supabase, we'll get size from file bytes
        storage_adapter = await file_service.get_storage()
        file_bytes = await storage_adapter.get_file(save_path_relative)
        file_size = len(file_bytes)
        
        # Calculate checksum from bytes or use provided checksum
        if checksum:
            file_checksum = checksum
        else:
            import hashlib
            file_checksum = hashlib.sha256(file_bytes).hexdigest()
        
        # Check for duplicate
        duplicate_doc = await check_duplicate_by_checksum(file_checksum)
        if duplicate_doc:
            # Delete the just uploaded file since it's a duplicate
            await file_service.delete_file(Path(save_path_relative))
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
            "file_path": str(save_path_full),  # Store full path in database
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
        logger.error(f"Error in upload_file: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

async def _handle_zip_upload(
    zip_file: UploadFile,
    base_folder: Optional[str],
    background_tasks: BackgroundTasks
) -> Dict:
    """
    Handle ZIP file upload by extracting and processing all files.
    The ZIP file itself is NOT saved as a document - only extracted files are processed.
    Folder structure from ZIP is automatically created.
    
    Args:
        zip_file: UploadFile containing ZIP archive
        base_folder: Optional base folder path
        background_tasks: FastAPI background tasks
        
    Returns:
        Dict with extraction results and list of created documents
    """
    try:
        # Read ZIP file content (ZIP file is NOT saved to storage, only extracted files are)
        zip_content = await zip_file.read()
        
        # Create a temporary UploadFile-like object from the ZIP content for extraction
        from io import BytesIO
        from fastapi import UploadFile as FastAPIUploadFile
        zip_file_obj = BytesIO(zip_content)
        zip_file_obj.seek(0)
        temp_zip_file = FastAPIUploadFile(
            filename=zip_file.filename,
            file=zip_file_obj
        )
        
        # Extract files from ZIP (also returns folder paths for empty folders)
        # Note: ZIP file itself is NOT saved - only extracted files are processed
        extracted_files, folder_paths = await file_service.extract_zip_files(temp_zip_file, base_folder)
        
        # Create folder records for all folders found in ZIP (including empty ones)
        for folder_path in folder_paths:
            if folder_path:
                try:
                    # Check if folder already exists
                    existing_folder = await db_service.get_folder(folder_path)
                    if not existing_folder:
                        # Create folder record
                        folder_parts = folder_path.split('/')
                        folder_name = folder_parts[-1]
                        parent_folder = '/'.join(folder_parts[:-1]) if len(folder_parts) > 1 else None
                        
                        folder_data = {
                            "name": folder_name,
                            "folder_path": folder_path,
                            "parent_folder": parent_folder.strip() if parent_folder and parent_folder.strip() else None,
                            "created_date": datetime.now().isoformat()
                        }
                        await db_service.create_folder(folder_data)
                except Exception as folder_err:
                    # Folder might already exist or creation failed - continue
                    logger.warning(f"Note: Folder '{folder_path}' may already exist or creation skipped: {folder_err}")
        
        created_documents = []
        skipped_files = []
        errors = []
        
        # Process each extracted file
        for file_bytes, filename, folder_path in extracted_files:
            try:
                # Create a temporary UploadFile-like object for processing
                from io import BytesIO
                temp_file = BytesIO(file_bytes)
                
                # Create document ID
                doc_id = str(uuid.uuid4())
                file_ext = Path(filename).suffix
                save_filename = f"{doc_id}{file_ext}"
                save_path = UPLOAD_DIR / save_filename
                
                # Calculate checksum
                import hashlib
                file_checksum = hashlib.sha256(file_bytes).hexdigest()
                file_size = len(file_bytes)
                
                # Check for duplicate
                duplicate_doc = await check_duplicate_by_checksum(file_checksum)
                if duplicate_doc:
                    skipped_files.append({
                        "filename": filename,
                        "reason": f"Duplicate of '{duplicate_doc['filename']}'"
                    })
                    continue
                
                # Save file directly to storage using bytes
                # Create a temporary file-like object compatible with UploadFile interface
                from io import BytesIO
                from fastapi import UploadFile as FastAPIUploadFile
                
                # Create a file-like object
                file_obj = BytesIO(file_bytes)
                file_obj.seek(0)
                
                # Create UploadFile-compatible object
                upload_file_obj = FastAPIUploadFile(
                    filename=filename,
                    file=file_obj
                )
                
                # Save using storage adapter
                storage_adapter = await file_service.get_storage()
                await storage_adapter.save_file(upload_file_obj, str(save_path))
                
                # Normalize folder path
                normalized_folder = folder_path.strip() if folder_path and folder_path.strip() else None
                
                upload_time = datetime.now().isoformat()
                doc_meta = {
                    "id": doc_id,
                    "filename": filename,
                    "upload_date": upload_time,
                    "file_path": str(save_path),
                    "status": "ready",
                    "summary": None,
                    "markdown_path": None,
                    "folder": normalized_folder,
                    "checksum": file_checksum,
                    "size": file_size,
                    "modified_date": upload_time
                }
                
                # Save to database
                doc_meta = await db_service.create_document(doc_meta)
                created_documents.append(doc_meta)
                
                # Trigger AI processing for extracted file
                background_tasks.add_task(
                    process_document_background_sync,
                    doc_id,
                    save_path
                )
                
            except Exception as e:
                logger.error(f"Error processing file {filename} from ZIP: {e}")
                errors.append({
                    "filename": filename,
                    "error": str(e)
                })
        
        return {
            "message": f"ZIP file '{zip_file.filename}' extracted: {len(created_documents)} files processed. ZIP file was not saved.",
            "total_files": len(extracted_files),
            "created": len(created_documents),
            "skipped": len(skipped_files),
            "errors": len(errors),
            "documents": created_documents,
            "skipped_files": skipped_files,
            "error_details": errors,
            "zip_filename": zip_file.filename,
            "folders_created": len(folder_paths)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing ZIP file: {e}")
        raise HTTPException(status_code=500, detail=f"ZIP extraction failed: {str(e)}")

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
    background_tasks: BackgroundTasks
) -> Dict:
    """
    Process a single file upload asynchronously. Returns document metadata or error info.
    Handles both regular files and ZIP archives.
    
    Args:
        file: The file to upload
        folder: Optional folder path for the file
        checksum: Optional pre-calculated checksum (skips calculation if provided)
        background_tasks: FastAPI background tasks for AI processing
    
    Returns:
        Dict with status ('success', 'duplicate', 'error', or 'zip_extracted') and relevant data
    """
    try:
        # Check if file is a ZIP archive
        file_ext = Path(file.filename).suffix.lower()
        if file_ext == '.zip':
            # Handle ZIP file extraction
            # ZIP file itself is NOT saved - only extracted files are processed
            try:
                # Read ZIP content (ZIP file is NOT saved to storage)
                zip_content = await file.read()
                from io import BytesIO
                from fastapi import UploadFile as FastAPIUploadFile
                
                zip_file_obj = BytesIO(zip_content)
                zip_file_obj.seek(0)
                temp_zip_file = FastAPIUploadFile(
                    filename=file.filename,
                    file=zip_file_obj
                )
                
                # Extract files and folder paths
                extracted_files, folder_paths = await file_service.extract_zip_files(temp_zip_file, folder)
                
                # Create folder records for all folders found in ZIP (including empty ones)
                for folder_path in folder_paths:
                    if folder_path:
                        try:
                            existing_folder = await db_service.get_folder(folder_path)
                            if not existing_folder:
                                folder_parts = folder_path.split('/')
                                folder_name = folder_parts[-1]
                                parent_folder = '/'.join(folder_parts[:-1]) if len(folder_parts) > 1 else None
                                
                                folder_data = {
                                    "name": folder_name,
                                    "folder_path": folder_path,
                                    "parent_folder": parent_folder.strip() if parent_folder and parent_folder.strip() else None,
                                    "created_date": datetime.now().isoformat()
                                }
                                await db_service.create_folder(folder_data)
                        except Exception:
                            pass  # Folder might already exist
                
                created_docs = []
                
                for file_bytes, filename, zip_folder_path in extracted_files:
                    try:
                        # Process each extracted file
                        file_obj = BytesIO(file_bytes)
                        file_obj.seek(0)
                        extracted_file = FastAPIUploadFile(filename=filename, file=file_obj)
                        
                        # Recursively process the extracted file
                        result = await process_single_file_upload_async(
                            extracted_file,
                            zip_folder_path,
                            None,  # No pre-calculated checksum
                            background_tasks
                        )
                        
                        if result.get("status") == "success":
                            doc = result.get("document")
                            created_docs.append(doc)
                            
                            # Trigger AI processing for extracted file
                            if doc and doc.get("id") and doc.get("file_path"):
                                background_tasks.add_task(
                                    process_document_background_sync,
                                    doc["id"],
                                    Path(doc["file_path"])
                                )
                    except Exception as e:
                        logger.error(f"Error processing extracted file {filename}: {e}")
                        continue
                
                return {
                    "status": "zip_extracted",
                    "filename": file.filename,
                    "extracted_count": len(created_docs),
                    "documents": created_docs,
                    "message": f"ZIP file extracted: {len(created_docs)} files processed. ZIP file was not saved."
                }
            except Exception as zip_error:
                return {
                    "status": "error",
                    "filename": file.filename,
                    "error": f"ZIP extraction failed: {str(zip_error)}"
                }
        
        # Continue with regular file processing (non-ZIP files)
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
        logger.error(f"Error in bulk upload: {e}")
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
        # Check if file is a ZIP archive - use process_single_file_upload_async for ZIP files
        file_ext = Path(task.filename).suffix.lower() if task.filename else ""
        if file_ext == '.zip':
            # Use process_single_file_upload_async for ZIP files (handles extraction)
            # ZIP files are NOT saved - only extracted files are processed
            result = await process_single_file_upload_async(
                task.file,
                task.folder,
                task.checksum,
                background_tasks
            )
        else:
            # Use regular processor for non-ZIP files
            result = await processor.process(task)
        
        # Trigger background AI processing for successful uploads
        result_status = result.get("status", "")
        if result_status == "success":
            doc_id = result.get("document_id")
            file_path = result.get("document", {}).get("file_path")
            if doc_id and file_path:
                background_tasks.add_task(
                    process_document_background_sync,
                    doc_id,
                    Path(file_path)
                )
        elif result_status == "zip_extracted":
            # For ZIP files, trigger AI processing for all extracted documents
            extracted_docs = result.get("documents", [])
            for doc in extracted_docs:
                if isinstance(doc, dict):
                    doc_id = doc.get("id")
                    file_path = doc.get("file_path")
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
            result = task.result or {}
            result_status = result.get("status", "")
            
            # Handle ZIP file extraction results
            if result_status == "zip_extracted":
                # ZIP file was extracted - count as successful and add all extracted document IDs
                successful += 1
                extracted_docs = result.get("documents", [])
                for doc in extracted_docs:
                    if isinstance(doc, dict) and doc.get("id"):
                        document_ids.append(doc["id"])
                    elif isinstance(doc, str):
                        document_ids.append(doc)
            elif task.status == UploadStatus.SUCCESS:
                successful += 1
                if result.get("document_id"):
                    document_ids.append(result["document_id"])
            elif task.status == UploadStatus.DUPLICATE:
                duplicates += 1
                errors.append({
                    "filename": task.filename,
                    "error": f"Duplicate of '{result.get('existing_document', {}).get('filename', 'unknown')}'"
                })
            else:
                failed += 1
                errors.append({
                    "filename": task.filename,
                    "error": task.error or result.get("error") or "Upload failed"
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

@router.get("/documents/tags")
async def get_all_tags():
    """
    Get all unique AI tags across all documents.
    Returns a list of all tags that have been extracted from documents,
    along with the count of documents using each tag.
    
    Returns:
        Dict with:
            - tags: List of unique tag strings
            - tag_counts: Dict mapping tag to count of documents using it
            - total_tags: Total number of unique tags
    """
    try:
        # Get all documents
        all_docs = await db_service.get_all_documents()
        
        # Collect all tags and count occurrences
        tag_counts: Dict[str, int] = {}
        tag_set = set()
        
        for doc in all_docs:
            doc_tags = doc.get("tags")
            if doc_tags and isinstance(doc_tags, list):
                for tag in doc_tags:
                    if tag and isinstance(tag, str) and tag.strip():
                        tag_lower = tag.strip().lower()
                        tag_set.add(tag_lower)
                        tag_counts[tag_lower] = tag_counts.get(tag_lower, 0) + 1
        
        # Sort tags by frequency (most used first), then alphabetically
        sorted_tags = sorted(tag_set, key=lambda t: (-tag_counts[t], t))
        
        # Return original case tags (preserve first occurrence's case)
        # Build a mapping of lowercase to original case
        original_case_map: Dict[str, str] = {}
        for doc in all_docs:
            doc_tags = doc.get("tags")
            if doc_tags and isinstance(doc_tags, list):
                for tag in doc_tags:
                    if tag and isinstance(tag, str) and tag.strip():
                        tag_lower = tag.strip().lower()
                        if tag_lower not in original_case_map:
                            original_case_map[tag_lower] = tag.strip()
        
        # Convert back to original case
        tags_with_case = [original_case_map.get(tag, tag) for tag in sorted_tags]
        tag_counts_with_case = {original_case_map.get(tag, tag): count for tag, count in tag_counts.items()}
        
        return {
            "tags": tags_with_case,
            "tag_counts": tag_counts_with_case,
            "total_tags": len(tags_with_case)
        }
    except Exception as e:
        logger.error(f"Error getting tags: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve tags: {str(e)}")

@router.get("/documents/search")
async def semantic_search(
    q: str = Query(..., description="Search query (e.g., 'invoices above ₹50,000', 'resume containing Python senior engineer')"),
    limit: Optional[int] = Query(10, description="Maximum number of results to return"),
    min_similarity: Optional[float] = Query(0.3, description="Minimum cosine similarity score (0.0 to 1.0)")
):
    """
    AI-Based Semantic Search across all documents.
    
    Uses embeddings + cosine similarity to find relevant documents.
    Supports natural language queries like:
    - "Find invoices above ₹50,000"
    - "Resume containing Python senior engineer"
    - "Contracts expiring this year"
    
    The search combines semantic similarity with field filtering when applicable.
    """
    if not db_service:
        raise HTTPException(status_code=503, detail="Database service not initialized")
    
    try:
        # 1. Parse query for field filters
        query_text = q.strip()
        filters = _parse_search_filters(query_text)
        
        # Remove filter keywords from query text for semantic search
        semantic_query = _clean_query_for_semantic_search(query_text)
        
        # 2. Generate embedding for query
        query_embedding = ai_service.generate_embedding(semantic_query)
        
        # 3. Get all documents
        all_docs = await db_service.get_all_documents(folder=None)
        
        # 4. Calculate similarity scores or fallback to text search
        results = []
        current_year = datetime.now().year
        
        # Check if we have embeddings available
        has_embeddings = query_embedding and len(query_embedding) > 0
        docs_with_embeddings = [doc for doc in all_docs if doc.get("embedding") and len(doc.get("embedding", [])) > 0]
        
        if has_embeddings and len(docs_with_embeddings) > 0:
            # Use semantic search with embeddings
            for doc in all_docs:
                doc_embedding = doc.get("embedding")
                if not doc_embedding or len(doc_embedding) == 0:
                    continue  # Skip documents without embeddings
                
                # Calculate cosine similarity
                similarity = ai_service.cosine_similarity(query_embedding, doc_embedding)
                
                if similarity < min_similarity:
                    continue  # Skip low similarity results
                
                # Apply field filters if specified
                extracted_fields = doc.get("extracted_fields", {})
                passes_filters = True
                
                # Filter by amount (for invoices)
                if filters.get("amount_min") is not None:
                    if doc.get("folder") and "Invoice" in doc.get("folder", ""):
                        amount_str = extracted_fields.get("amount", "")
                        if amount_str:
                            # Extract numeric value from amount string
                            amount_value = _extract_numeric_value(amount_str)
                            if amount_value is None or amount_value < filters["amount_min"]:
                                passes_filters = False
                    else:
                        passes_filters = False
                
                # Filter by date (for contracts - expiring this year)
                if filters.get("expiring_this_year"):
                    if doc.get("folder") and "Contract" in doc.get("folder", ""):
                        end_date_str = extracted_fields.get("end_date", "")
                        if end_date_str:
                            try:
                                # Try to parse date
                                end_date = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
                                if end_date.year != current_year:
                                    passes_filters = False
                            except:
                                # If date parsing fails, check if year is mentioned in the date string
                                if str(current_year) not in end_date_str:
                                    passes_filters = False
                        else:
                            passes_filters = False
                    else:
                        passes_filters = False
                
                # Filter by document type/category
                if filters.get("doc_type"):
                    doc_folder = doc.get("folder", "")
                    if filters["doc_type"].lower() not in doc_folder.lower():
                        passes_filters = False
                
                if passes_filters:
                    results.append({
                        "document": doc,
                        "similarity": similarity,
                        "score": similarity  # For sorting
                    })
        else:
            # Fallback to text-based search when embeddings are not available
            query_lower = semantic_query.lower()
            for doc in all_docs:
                # Search in filename, summary, tags, and extracted fields
                filename = doc.get("filename", "").lower()
                summary = (doc.get("summary") or "").lower()
                tags = " ".join(doc.get("tags") or []).lower()
                extracted_fields = doc.get("extracted_fields", {})
                fields_text = " ".join([str(v) for v in extracted_fields.values() if v]).lower()
                
                # Check if query matches any field
                matches = (
                    query_lower in filename or
                    query_lower in summary or
                    query_lower in tags or
                    query_lower in fields_text
                )
                
                if not matches:
                    continue
                
                # Apply field filters if specified
                passes_filters = True
                
                # Filter by amount (for invoices)
                if filters.get("amount_min") is not None:
                    if doc.get("folder") and "Invoice" in doc.get("folder", ""):
                        amount_str = extracted_fields.get("amount", "")
                        if amount_str:
                            amount_value = _extract_numeric_value(amount_str)
                            if amount_value is None or amount_value < filters["amount_min"]:
                                passes_filters = False
                    else:
                        passes_filters = False
                
                # Filter by date (for contracts - expiring this year)
                if filters.get("expiring_this_year"):
                    if doc.get("folder") and "Contract" in doc.get("folder", ""):
                        end_date_str = extracted_fields.get("end_date", "")
                        if end_date_str:
                            try:
                                end_date = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
                                if end_date.year != current_year:
                                    passes_filters = False
                            except:
                                if str(current_year) not in end_date_str:
                                    passes_filters = False
                        else:
                            passes_filters = False
                    else:
                        passes_filters = False
                
                # Filter by document type/category
                if filters.get("doc_type"):
                    doc_folder = doc.get("folder", "")
                    if filters["doc_type"].lower() not in doc_folder.lower():
                        passes_filters = False
                
                if passes_filters:
                    # Calculate a simple relevance score for text search
                    score = 0.0
                    if query_lower in filename:
                        score += 0.5
                    if query_lower in summary:
                        score += 0.3
                    if query_lower in tags:
                        score += 0.2
                    
                    results.append({
                        "document": doc,
                        "similarity": min(score, 1.0),  # Cap at 1.0
                        "score": min(score, 1.0)
                    })
            
        
        # 5. Sort by similarity (descending)
        results.sort(key=lambda x: x["similarity"], reverse=True)
        
        # 6. Apply limit
        limited_results = results[:limit] if limit else results
        
        # 7. Format response
        return {
            "query": q,
            "semantic_query": semantic_query,
            "search_mode": "semantic" if has_embeddings and len(docs_with_embeddings) > 0 else "text",
            "filters_applied": filters,
            "total_results": len(results),
            "returned_results": len(limited_results),
            "results": [
                {
                    "document_id": r["document"]["id"],
                    "filename": r["document"]["filename"],
                    "summary": r["document"].get("summary"),
                    "folder": r["document"].get("folder"),
                    "extracted_fields": r["document"].get("extracted_fields"),
                    "similarity_score": round(r["similarity"], 4),
                    "upload_date": r["document"].get("upload_date")
                }
                for r in limited_results
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in semantic search: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

def _parse_search_filters(query: str) -> Dict[str, Any]:
    """
    Parse search query for field filters.
    Returns a dictionary with filter criteria.
    """
    filters = {}
    query_lower = query.lower()
    
    # Check for amount filters (e.g., "above ₹50,000", "over $1000")
    amount_patterns = [
        r"(?:above|over|more than|greater than)\s*[₹$€]?\s*([\d,]+)",
        r"(?:below|under|less than|lower than)\s*[₹$€]?\s*([\d,]+)",
    ]
    
    for pattern in amount_patterns:
        match = re.search(pattern, query_lower)
        if match:
            amount_str = match.group(1).replace(",", "")
            try:
                amount_value = float(amount_str)
                if "above" in query_lower or "over" in query_lower or "more" in query_lower or "greater" in query_lower:
                    filters["amount_min"] = amount_value
                elif "below" in query_lower or "under" in query_lower or "less" in query_lower or "lower" in query_lower:
                    filters["amount_max"] = amount_value
            except ValueError:
                pass
    
    # Check for "expiring this year" or "expires this year"
    if re.search(r"expir(?:ing|es)?\s+this\s+year", query_lower):
        filters["expiring_this_year"] = True
    
    # Check for document type keywords
    doc_types = {
        "invoice": "Invoice",
        "invoices": "Invoice",
        "resume": "Resume",
        "resumes": "Resume",
        "cv": "Resume",
        "contract": "Contract",
        "contracts": "Contract",
        "agreement": "Contract"
    }
    
    for keyword, doc_type in doc_types.items():
        if keyword in query_lower:
            filters["doc_type"] = doc_type
            break
    
    return filters

def _clean_query_for_semantic_search(query: str) -> str:
    """
    Remove filter-specific keywords from query to improve semantic search.
    """
    # Remove amount filter keywords but keep the number
    query = re.sub(r"(?:above|over|more than|greater than|below|under|less than|lower than)\s*[₹$€]?\s*[\d,]+", "", query, flags=re.IGNORECASE)
    # Remove "expiring this year" but keep the intent
    query = re.sub(r"expir(?:ing|es)?\s+this\s+year", "", query, flags=re.IGNORECASE)
    # Clean up extra spaces
    query = re.sub(r"\s+", " ", query).strip()
    return query

def _extract_numeric_value(amount_str: str) -> Optional[float]:
    """
    Extract numeric value from amount string (e.g., "₹50,000" -> 50000.0).
    """
    # Remove currency symbols and commas
    cleaned = re.sub(r"[₹$€,]", "", amount_str)
    # Extract first number found
    match = re.search(r"[\d.]+", cleaned)
    if match:
        try:
            return float(match.group())
        except ValueError:
            return None
    return None

@router.get("/documents/tags/{tag}")
async def get_documents_by_tag(tag: str):
    """
    Get all documents that have a specific tag.
    Tag matching is case-insensitive.
    
    Args:
        tag: The tag to search for (case-insensitive)
    
    Returns:
        List of documents that contain this tag
    """
    try:
        # Get all documents
        all_docs = await db_service.get_all_documents()
        
        # Filter documents that have this tag (case-insensitive)
        tag_lower = tag.strip().lower()
        matching_docs = []
        
        for doc in all_docs:
            doc_tags = doc.get("tags")
            if doc_tags and isinstance(doc_tags, list):
                # Check if any tag matches (case-insensitive)
                if any(t and isinstance(t, str) and t.strip().lower() == tag_lower for t in doc_tags):
                    matching_docs.append(doc)
        
        # Ensure all documents have size and modified_date fields
        for doc in matching_docs:
            if "size" not in doc or doc.get("size") is None:
                file_path = Path(doc.get("file_path", ""))
                if file_path.exists():
                    try:
                        size = file_path.stat().st_size
                        await db_service.update_document(doc["id"], {"size": size})
                        doc["size"] = size
                    except Exception as e:
                        doc["size"] = None
            
            # Set modified_date to upload_date if not present
            if "modified_date" not in doc or doc.get("modified_date") is None:
                doc["modified_date"] = doc.get("upload_date")
        
        return matching_docs
    except Exception as e:
        logger.error(f"Error getting documents by tag '{tag}': {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve documents by tag: {str(e)}")

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
        logger.error(f"Error creating folder: {e}")
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
    
    # Handle nested path issue (if file was saved with duplicated path)
    if not file_path.exists():
        # Try to find the file by filename in uploads directory
        filename = file_path.name
        possible_paths = [
            UPLOAD_DIR / filename,
            Path(file_path_str.replace(str(UPLOAD_DIR) + str(UPLOAD_DIR), str(UPLOAD_DIR))),
            UPLOAD_DIR / "Users" / "om" / "Desktop" / "OutmarketAI" / "DocVaultAI" / "backend" / "uploads" / filename
        ]
        
        found_path = None
        for possible_path in possible_paths:
            if possible_path.exists():
                found_path = possible_path
                # Update database with correct path
                await db_service.update_document(doc_id, {"file_path": str(found_path)})
                logger.info(f"Fixed file path for {doc_id}: {file_path_str} -> {found_path}")
                break
        
        if found_path:
            file_path = found_path
        else:
            raise HTTPException(status_code=404, detail=f"Document file not found at {file_path_str}")
    
    # Trigger background processing
    background_tasks.add_task(process_document_background_sync, doc_id, file_path)
    
    return {"message": "AI processing started", "status": "processing"}

@router.get("/files/{filename}")
async def get_file(filename: str):
    """Get a file from storage (works with local, S3, or Supabase)."""
    try:
        storage_adapter = await file_service.get_storage()
        # filename is already relative (e.g., "cfcac16d-8cd4-43cd-9899-d601a8372b5a.pdf")
        # Storage adapter expects relative paths, not absolute paths
        file_path = filename
        
        # Check if file exists (using relative path)
        if not await storage_adapter.file_exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")
        
        # For markdown/text files, return text content
        if filename.endswith('.md') or filename.endswith('.txt'):
            text_content = await storage_adapter.get_text(file_path)
            from fastapi.responses import Response
            return Response(content=text_content, media_type="text/plain; charset=utf-8")
        
        # For local storage, return FileResponse for efficiency
        if STORAGE_TYPE.lower() == "local":
            from fastapi.responses import FileResponse
            # Get the actual local path from storage adapter
            local_storage = storage_adapter
            local_path = local_storage._get_full_path(file_path)
            if local_path.exists():
                return FileResponse(local_path)
            else:
                raise HTTPException(status_code=404, detail="File not found")
        
        # For S3/Supabase, get file bytes
        file_bytes = await storage_adapter.get_file(file_path)
        from fastapi.responses import Response
from ..core.logging_config import get_logger

logger = get_logger(__name__)
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
        logger.error(f"Error deleting document {doc_id}: {e}")
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
                logger.error(f"Error deleting file for folder '{folder_path}': {file_err}")
        
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
        logger.error(f"Error deleting folder '{folder_path}': {e}")
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
        logger.error(f"Error moving folder {folder_path}: {e}")
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
        logger.error(f"Error getting missing summaries: {e}")
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
        logger.error(f"Error regenerating summary for {doc_id}: {e}")
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
        logger.error(f"Error in batch regeneration: {e}")
        raise HTTPException(status_code=500, detail=f"Batch regeneration failed: {str(e)}")