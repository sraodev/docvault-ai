"""
Upload Service - Handles all file upload operations.

This service encapsulates all upload-related business logic:
- Single file uploads (regular files and ZIP archives)
- Bulk file uploads with queue-based processing
- Duplicate detection via checksum comparison
- File storage coordination
- Database record creation

Architecture:
- Follows Single Responsibility Principle
- Uses dependency injection for file_service and db_service
- Handles ZIP extraction internally
- Coordinates with UploadQueueManager for bulk operations

Example Usage:
    service = UploadService(file_service, db_service)
    result = await service.upload_single_file(file, folder="Invoices")
"""
import uuid
import hashlib
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from io import BytesIO
from fastapi import UploadFile, BackgroundTasks

from .file_service import FileService
from .upload_processor import UploadProcessor
from .upload_queue import UploadQueueManager, UploadTask, UploadStatus
from ..utils.document_utils import create_document_metadata, normalize_folder_name
from ..core.config import UPLOAD_DIR


class UploadService:
    """
    Service for handling file uploads.
    
    This service coordinates the complete upload workflow:
    1. File validation and type detection
    2. Checksum calculation and duplicate checking
    3. File storage (local/S3/Supabase)
    4. Database record creation
    5. ZIP file extraction (if applicable)
    
    The service handles both single and bulk uploads, with special
    optimization for large batches using adaptive chunking.
    
    Attributes:
        file_service: FileService instance for file operations
        db_service: Database service instance for data persistence
        processor: UploadProcessor for individual file processing
    """
    
    def __init__(self, file_service: FileService, db_service):
        """
        Initialize upload service.
        
        Args:
            file_service: FileService instance
            db_service: Database service instance
        """
        self.file_service = file_service
        self.db_service = db_service
        self.processor = UploadProcessor(file_service, db_service)
    
    @property
    def db(self):
        """Expose db_service for external access."""
        return self.db_service
    
    async def check_duplicate(self, checksum: str) -> Optional[Dict[str, Any]]:
        """
        Check if a file with the given checksum already exists.
        
        Args:
            checksum: SHA-256 checksum
            
        Returns:
            Existing document dict if duplicate found, None otherwise
        """
        return await self.db_service.find_document_by_checksum(checksum)
    
    async def upload_single_file(
        self,
        file: UploadFile,
        folder: Optional[str] = None,
        checksum: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upload a single file.
        
        This method handles the complete upload workflow for a single file:
        1. Detects if file is a ZIP archive
        2. For ZIP files: Extracts and processes all files
        3. For regular files: Processes directly
        4. Calculates checksum (or uses provided)
        5. Checks for duplicates
        6. Saves file to storage
        7. Creates database record
        
        Args:
            file: FastAPI UploadFile object containing the file to upload
            folder: Optional folder path for organization
                   Example: "Invoices/2024" or None for root
            checksum: Optional pre-calculated SHA-256 checksum
                     If provided, skips checksum calculation (faster)
        
        Returns:
            Dict with status and result:
            - status: "success", "duplicate", "error", or "zip_extracted"
            - document: Document metadata (if success)
            - error: Error message (if error)
            - documents: List of documents (if zip_extracted)
        
        Example:
            result = await service.upload_single_file(file, folder="Invoices")
            if result["status"] == "success":
                doc = result["document"]
                print(f"Uploaded: {doc['filename']}")
        
        Note:
            - ZIP files are NOT saved - only extracted files are processed
            - Duplicate files return status "duplicate" with existing document info
            - All file operations are async for performance
        """
        try:
            # Check if file is a ZIP archive
            file_ext = Path(file.filename).suffix.lower()
            if file_ext == '.zip':
                return await self._handle_zip_file(file, folder)
            
            # Process regular file
            return await self._process_regular_file(file, folder, checksum)
        except Exception as e:
            return {
                "status": "error",
                "filename": file.filename if file else "unknown",
                "error": str(e)
            }
    
    async def _process_regular_file(
        self,
        file: UploadFile,
        folder: Optional[str],
        checksum: Optional[str]
    ) -> Dict[str, Any]:
        """Process a regular (non-ZIP) file upload."""
        doc_id = str(uuid.uuid4())
        file_ext = Path(file.filename).suffix
        save_filename = f"{doc_id}{file_ext}"
        save_path_relative = save_filename
        save_path_full = UPLOAD_DIR / save_filename
        
        # Save file
        await self.file_service.save_upload(file, Path(save_path_relative))
        
        # Get file size and calculate checksum
        storage_adapter = await self.file_service.get_storage()
        file_bytes = await storage_adapter.get_file(save_path_relative)
        file_size = len(file_bytes)
        
        if checksum:
            file_checksum = checksum
        else:
            file_checksum = hashlib.sha256(file_bytes).hexdigest()
        
        # Check for duplicate
        duplicate_doc = await self.check_duplicate(file_checksum)
        if duplicate_doc:
            await self.file_service.delete_file(Path(save_path_relative))
            return {
                "status": "duplicate",
                "filename": Path(file.filename).name,
                "existing_filename": duplicate_doc.get("filename"),
                "document_id": duplicate_doc.get("id")
            }
        
        # Create document metadata
        clean_filename = Path(file.filename).name
        doc_meta = create_document_metadata(
            doc_id=doc_id,
            filename=clean_filename,
            file_path=str(save_path_full),
            file_size=file_size,
            checksum=file_checksum,
            folder=folder,
            status="ready"
        )
        
        # Save to database
        doc_meta = await self.db_service.create_document(doc_meta)
        
        return {
            "status": "success",
            "document": doc_meta
        }
    
    async def _handle_zip_file(
        self,
        zip_file: UploadFile,
        base_folder: Optional[str]
    ) -> Dict[str, Any]:
        """
        Handle ZIP file upload by extracting and processing all files.
        
        Args:
            zip_file: ZIP file to extract
            base_folder: Optional base folder path
            
        Returns:
            Dict with extraction results
        """
        try:
            # Read ZIP content
            zip_content = await zip_file.read()
            
            # Create temporary UploadFile for extraction
            zip_file_obj = BytesIO(zip_content)
            zip_file_obj.seek(0)
            from fastapi import UploadFile as FastAPIUploadFile
            temp_zip_file = FastAPIUploadFile(
                filename=zip_file.filename,
                file=zip_file_obj
            )
            
            # Extract files
            extracted_files, folder_paths = await self.file_service.extract_zip_files(
                temp_zip_file,
                base_folder
            )
            
            # Create folder records
            await self._create_folders_from_paths(folder_paths)
            
            # Process extracted files
            created_documents = []
            skipped_files = []
            errors = []
            
            for file_bytes, filename, folder_path in extracted_files:
                try:
                    result = await self._process_extracted_file(
                        file_bytes,
                        filename,
                        folder_path
                    )
                    
                    if result.get("status") == "success":
                        created_documents.append(result.get("document"))
                    elif result.get("status") == "duplicate":
                        skipped_files.append({
                            "filename": filename,
                            "reason": f"Duplicate of '{result.get('existing_filename')}'"
                        })
                    else:
                        errors.append({
                            "filename": filename,
                            "error": result.get("error", "Unknown error")
                        })
                except Exception as e:
                    errors.append({
                        "filename": filename,
                        "error": str(e)
                    })
            
            return {
                "status": "zip_extracted",
                "filename": zip_file.filename,
                "extracted_count": len(created_documents),
                "documents": created_documents,
                "message": f"ZIP file extracted: {len(created_documents)} files processed. ZIP file was not saved.",
                "total_files": len(extracted_files),
                "created": len(created_documents),
                "skipped": len(skipped_files),
                "errors": len(errors),
                "skipped_files": skipped_files,
                "error_details": errors,
                "folders_created": len(folder_paths)
            }
        except Exception as e:
            return {
                "status": "error",
                "filename": zip_file.filename,
                "error": f"ZIP extraction failed: {str(e)}"
            }
    
    async def _create_folders_from_paths(self, folder_paths: List[str]) -> None:
        """Create folder records for all folder paths."""
        for folder_path in folder_paths:
            if folder_path:
                try:
                    existing_folder = await self.db_service.get_folder(folder_path)
                    if not existing_folder:
                        folder_parts = folder_path.split('/')
                        folder_name = folder_parts[-1]
                        parent_folder = '/'.join(folder_parts[:-1]) if len(folder_parts) > 1 else None
                        
                        folder_data = {
                            "name": folder_name,
                            "folder_path": folder_path,
                            "parent_folder": normalize_folder_name(parent_folder),
                            "created_date": datetime.now().isoformat()
                        }
                        await self.db_service.create_folder(folder_data)
                except Exception:
                    pass  # Folder might already exist
    
    async def _process_extracted_file(
        self,
        file_bytes: bytes,
        filename: str,
        folder_path: Optional[str]
    ) -> Dict[str, Any]:
        """Process a single extracted file from ZIP."""
        doc_id = str(uuid.uuid4())
        file_ext = Path(filename).suffix
        save_filename = f"{doc_id}{file_ext}"
        save_path = UPLOAD_DIR / save_filename
        
        # Calculate checksum
        file_checksum = hashlib.sha256(file_bytes).hexdigest()
        file_size = len(file_bytes)
        
        # Check for duplicate
        duplicate_doc = await self.check_duplicate(file_checksum)
        if duplicate_doc:
            return {
                "status": "duplicate",
                "filename": filename,
                "existing_filename": duplicate_doc.get("filename"),
                "document_id": duplicate_doc.get("id")
            }
        
        # Save file
        from fastapi import UploadFile as FastAPIUploadFile
        file_obj = BytesIO(file_bytes)
        file_obj.seek(0)
        upload_file_obj = FastAPIUploadFile(filename=filename, file=file_obj)
        
        storage_adapter = await self.file_service.get_storage()
        await storage_adapter.save_file(upload_file_obj, str(save_path))
        
        # Create document metadata
        doc_meta = create_document_metadata(
            doc_id=doc_id,
            filename=filename,
            file_path=str(save_path),
            file_size=file_size,
            checksum=file_checksum,
            folder=folder_path,
            status="ready"
        )
        
        # Save to database
        doc_meta = await self.db_service.create_document(doc_meta)
        
        return {
            "status": "success",
            "document": doc_meta
        }
    
    async def upload_bulk_files(
        self,
        files: List[UploadFile],
        folders: Optional[List[str]],
        checksums: Optional[List[str]],
        background_tasks: BackgroundTasks,
        concurrency: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Upload multiple files using queue-based worker pool.
        
        Args:
            files: List of files to upload
            folders: Optional list of folder paths
            checksums: Optional list of pre-calculated checksums
            background_tasks: FastAPI background tasks
            concurrency: Optional concurrency hint
            
        Returns:
            BulkUploadResponse with summary statistics
        """
        total_files = len(files)
        
        # Normalize lists
        folders_list = folders if folders else [None] * total_files
        checksums_list = checksums if checksums else [None] * total_files
        
        while len(folders_list) < total_files:
            folders_list.append(None)
        while len(checksums_list) < total_files:
            checksums_list.append(None)
        
        # For very large batches, use adaptive chunking
        if total_files > 1000:
            chunk_size = self._calculate_chunk_size(total_files)
            return await self._process_large_batch(
                files, folders_list, checksums_list, background_tasks, chunk_size
            )
        
        # For smaller batches, use queue-based processing
        return await self._process_with_queue(
            files, folders_list, checksums_list, background_tasks, concurrency
        )
    
    def _calculate_chunk_size(self, total_files: int) -> int:
        """Calculate optimal chunk size based on batch size."""
        import math
        if total_files < 100000:
            return 500
        elif total_files < 1000000:
            return 5000
        else:
            return 50000
    
    async def _process_with_queue(
        self,
        files: List[UploadFile],
        folders_list: List[Optional[str]],
        checksums_list: List[Optional[str]],
        background_tasks: BackgroundTasks,
        concurrency_hint: Optional[int]
    ) -> Dict[str, Any]:
        """Process uploads using queue-based worker pool."""
        total_files = len(files)
        
        # Calculate concurrency
        if concurrency_hint:
            base_concurrency = concurrency_hint
        else:
            import math
            if total_files < 1000:
                base_concurrency = max(10, total_files // 5)
            else:
                base_concurrency = max(20, int(math.log10(total_files) * 10))
        
        # Create queue manager
        queue_manager = UploadQueueManager(
            min_workers=5,
            max_workers=None,
            base_concurrency=base_concurrency
        )
        
        # Add tasks to queue
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
        
        # Process tasks
        async def process_task(task: UploadTask):
            file_ext = Path(task.filename).suffix.lower() if task.filename else ""
            if file_ext == '.zip':
                result = await self.upload_single_file(
                    task.file,
                    task.folder,
                    task.checksum
                )
            else:
                result = await self.processor.process(task)
            
            # Trigger background AI processing for successful uploads
            result_status = result.get("status", "")
            if result_status == "success":
                doc_id = result.get("document_id") or result.get("document", {}).get("id")
                file_path = result.get("document", {}).get("file_path")
                if doc_id and file_path:
                    background_tasks.add_task(
                        self._trigger_ai_processing,
                        doc_id,
                        Path(file_path)
                    )
            elif result_status == "zip_extracted":
                extracted_docs = result.get("documents", [])
                for doc in extracted_docs:
                    if isinstance(doc, dict):
                        doc_id = doc.get("id")
                        file_path = doc.get("file_path")
                        if doc_id and file_path:
                            background_tasks.add_task(
                                self._trigger_ai_processing,
                                doc_id,
                                Path(file_path)
                            )
            return result
        
        await queue_manager.start_workers(process_task)
        
        # Wait for completion
        timeout = self._calculate_timeout(total_files)
        await queue_manager.wait_for_completion(timeout=timeout)
        
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
                
                if result_status == "zip_extracted":
                    successful += 1
                    extracted_docs = result.get("documents", [])
                    for doc in extracted_docs:
                        if isinstance(doc, dict) and doc.get("id"):
                            document_ids.append(doc["id"])
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
        
        await queue_manager.stop()
        
        return {
            "total_files": total_files,
            "successful": successful,
            "failed": failed,
            "duplicates": duplicates,
            "document_ids": document_ids,
            "errors": errors
        }
    
    async def _process_large_batch(
        self,
        files: List[UploadFile],
        folders_list: List[Optional[str]],
        checksums_list: List[Optional[str]],
        background_tasks: BackgroundTasks,
        chunk_size: int
    ) -> Dict[str, Any]:
        """Process very large batches in adaptive chunks."""
        total_files = len(files)
        all_document_ids = []
        all_errors = []
        total_successful = 0
        total_failed = 0
        total_duplicates = 0
        
        # Process in chunks
        for chunk_start in range(0, total_files, chunk_size):
            chunk_end = min(chunk_start + chunk_size, total_files)
            chunk_files = files[chunk_start:chunk_end]
            chunk_folders = folders_list[chunk_start:chunk_end]
            chunk_checksums = checksums_list[chunk_start:chunk_end]
            
            chunk_result = await self._process_with_queue(
                chunk_files, chunk_folders, chunk_checksums, background_tasks, None
            )
            
            total_successful += chunk_result["successful"]
            total_failed += chunk_result["failed"]
            total_duplicates += chunk_result["duplicates"]
            all_document_ids.extend(chunk_result["document_ids"])
            all_errors.extend(chunk_result["errors"])
        
        return {
            "total_files": total_files,
            "successful": total_successful,
            "failed": total_failed,
            "duplicates": total_duplicates,
            "document_ids": all_document_ids,
            "errors": all_errors
        }
    
    def _calculate_timeout(self, total_files: int) -> Optional[int]:
        """Calculate timeout based on batch size."""
        import math
        if total_files < 1000:
            return 600  # 10 minutes
        elif total_files < 100000:
            return 3600  # 1 hour
        elif total_files < 1000000:
            return 7200  # 2 hours
        else:
            estimated_seconds = (total_files / 50) * 1.5
            return min(int(estimated_seconds), 86400)  # Max 24 hours
    
    def _trigger_ai_processing(self, doc_id: str, file_path: Path) -> None:
        """
        Trigger AI processing for a document (sync wrapper).
        This should be called from the router with the processing service.
        """
        # This method is a placeholder - actual processing should be triggered
        # from the router using DocumentProcessingService
        pass

