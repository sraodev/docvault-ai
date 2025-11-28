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
        try:
            # Generate document ID
            doc_id = str(uuid.uuid4())
            file_ext = Path(task.filename).suffix
            save_filename = f"{doc_id}{file_ext}"
            save_path = UPLOAD_DIR / save_filename
            
            # Save file using storage adapter
            await self.file_service.save_upload(task.file, save_path)
            
            # Get file from storage and calculate checksum
            storage_adapter = await self.file_service.get_storage()
            file_bytes = await storage_adapter.get_file(str(save_path))
            file_size = len(file_bytes)
            
            # Calculate checksum
            if task.checksum:
                file_checksum = task.checksum
            else:
                file_checksum = hashlib.sha256(file_bytes).hexdigest()
            
            # Check for duplicate
            duplicate_doc = await self.db_service.find_document_by_checksum(file_checksum)
            if duplicate_doc:
                # Delete the just uploaded file since it's a duplicate
                await self.file_service.delete_file(save_path)
                return {
                    "status": "duplicate",
                    "filename": task.filename,
                    "existing_document": duplicate_doc,
                    "document_id": duplicate_doc.get("id")
                }
            
            # Normalize folder name
            normalized_folder = task.folder.strip() if task.folder and task.folder.strip() else None
            
            # Create document metadata
            upload_time = datetime.now().isoformat()
            doc_meta = {
                "id": doc_id,
                "filename": Path(task.filename).name,  # Clean filename
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
            
            # Save to database
            doc_meta = await self.db_service.create_document(doc_meta)
            
            return {
                "status": "success",
                "document": doc_meta,
                "document_id": doc_id
            }
            
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            return {
                "status": "error",
                "error": error_msg,
                "filename": task.filename
            }

