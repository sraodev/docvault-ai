"""
Upload Processor - Handles individual file uploads with error handling.
Used by UploadQueueManager to process tasks.
"""
import uuid
import hashlib
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime
from fastapi import UploadFile

from .upload_queue import UploadTask, UploadStatus
from .file_service import FileService
from ..core.config import UPLOAD_DIR
from ..core.logging_config import get_logger

logger = get_logger(__name__)

class UploadProcessor:
    """
    Processes individual file uploads.
    Handles file saving, checksum calculation, duplicate detection, and database storage.
    """
    
    def __init__(self, file_service: FileService, db_service):
        """
        Initialize upload processor.
        
        Args:
            file_service: FileService instance for file operations
            db_service: Database service instance
        """
        self.file_service = file_service
        self.db_service = db_service
    
    async def process(self, task: UploadTask) -> Dict:
        """
        Process a single upload task.
        
        Args:
            task: UploadTask to process
        
        Returns:
            Dict with status and result/error information
        """
        logger.debug(f"Processing upload task: {task.filename} (task_id: {task.task_id})")
        try:
            # Generate document ID
            doc_id = str(uuid.uuid4())
            file_ext = Path(task.filename).suffix
            save_filename = f"{doc_id}{file_ext}"
            save_path = UPLOAD_DIR / save_filename
            
            # Save file using storage adapter (use relative path)
            save_path_relative = Path(save_filename)
            await self.file_service.save_upload(task.file, save_path_relative)
            
            # Get file from storage and calculate checksum
            storage_adapter = await self.file_service.get_storage()
            file_bytes = await storage_adapter.get_file(str(save_path_relative))
            file_size = len(file_bytes)
            
            # Calculate checksum
            if task.checksum:
                file_checksum = task.checksum
            else:
                file_checksum = hashlib.sha256(file_bytes).hexdigest()
            
            # Check for duplicate
            duplicate_doc = await self.db_service.find_document_by_checksum(file_checksum)
            if duplicate_doc:
                logger.info(f"Duplicate file detected: {task.filename} (existing: {duplicate_doc.get('filename')})")
                # Delete the just uploaded file since it's a duplicate
                await self.file_service.delete_file(save_path_relative)
                return {
                    "status": "duplicate",
                    "filename": task.filename,
                    "existing_document": duplicate_doc,
                    "document_id": duplicate_doc.get("id")
                }
            
            # Normalize folder name
            normalized_folder = task.folder.strip() if task.folder and task.folder.strip() else None
            
            # Create folder records if folder path is provided
            if normalized_folder:
                try:
                    # Check if folder already exists
                    existing_folder = await self.db_service.get_folder(normalized_folder)
                    if not existing_folder:
                        # Create folder structure (handle nested folders)
                        folder_parts = normalized_folder.split('/')
                        # Create all parent folders first
                        for i in range(1, len(folder_parts) + 1):
                            parent_path = '/'.join(folder_parts[:i])
                            parent_existing = await self.db_service.get_folder(parent_path)
                            if not parent_existing:
                                folder_name = folder_parts[i-1]
                                parent_folder = '/'.join(folder_parts[:i-1]) if i > 1 else None
                                
                                folder_data = {
                                    "name": folder_name,
                                    "folder_path": parent_path,
                                    "parent_folder": parent_folder.strip() if parent_folder and parent_folder.strip() else None,
                                    "created_date": datetime.now().isoformat()
                                }
                                await self.db_service.create_folder(folder_data)
                                logger.debug(f"Created folder: {parent_path}")
                except Exception as folder_err:
                    # Don't fail upload if folder creation fails
                    logger.warning(f"Folder creation skipped for '{normalized_folder}': {folder_err}")
            
            # Create document metadata
            upload_time = datetime.now().isoformat()
            doc_meta = {
                "id": doc_id,
                "filename": Path(task.filename).name,  # Clean filename
                "upload_date": upload_time,
                "file_path": str(save_path_relative),  # Store relative path
                "status": "processing",
                "summary": None,
                "markdown_path": None,
                "folder": normalized_folder,
                "checksum": file_checksum,
                "size": file_size,
                "modified_date": upload_time
            }
            
            # Save to database
            doc_meta = await self.db_service.create_document(doc_meta)
            logger.info(f"Successfully uploaded and saved document: {task.filename} (doc_id: {doc_id})")
            
            return {
                "status": "success",
                "document": doc_meta,
                "document_id": doc_id
            }
            
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            logger.error(f"Error processing upload task {task.task_id} ({task.filename}): {error_msg}", exc_info=True)
            return {
                "status": "error",
                "error": error_msg,
                "filename": task.filename
            }

