"""
Document Processing Service - Handles AI processing of documents.
Extracted from documents router to follow Single Responsibility Principle.
"""
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
from fastapi import HTTPException, status

from .ai_service import AIService
from .file_service import FileService
from ..utils.tag_extractor import extract_tags_from_text
from ..core.config import UPLOAD_DIR
from ..core.logging_config import get_logger

logger = get_logger(__name__)


class DocumentProcessingService:
    """
    Service for processing documents with AI.
    Handles text extraction, summary generation, tag extraction, and embedding generation.
    """
    
    def __init__(self, ai_service: AIService, file_service: FileService, db_service):
        """
        Initialize document processing service.
        
        Args:
            ai_service: AIService instance
            file_service: FileService instance
            db_service: Database service instance
        """
        self.ai_service = ai_service
        self.file_service = file_service
        self.db_service = db_service
    
    async def process_document(self, doc_id: str, file_path: Path) -> None:
        """
        Process a document with AI (async version).
        Uses AI to generate summary, markdown, and tags.
        Falls back to rule-based tag extraction if AI fails.
        
        Args:
            doc_id: Document ID
            file_path: Path to document file
        """
        try:
            # Update status to processing
            await self.db_service.update_document(doc_id, {"status": "processing"})
            
            # 1. Extract Text
            file_ext = file_path.suffix.lower()
            filename = file_path.name
            logger.info(f"Extracting text from {filename} (format: {file_ext})")
            
            try:
                text_content = await self.file_service.extract_text(file_path)
            except HTTPException as http_err:
                # Re-raise HTTP exceptions (they already have proper error messages)
                error_detail = http_err.detail
                logger.error(
                    f"Text extraction failed for {filename} ({file_ext}): {error_detail}",
                    exc_info=False
                )
                # Mark document as failed with error message
                await self.db_service.update_document(doc_id, {
                    "status": "failed",
                    "error": error_detail
                })
                raise
            except Exception as extract_err:
                error_msg = str(extract_err)
                logger.error(
                    f"Unexpected error extracting text from {filename} ({file_ext}): {error_msg}",
                    exc_info=True
                )
                # Mark document as failed
                await self.db_service.update_document(doc_id, {
                    "status": "failed",
                    "error": f"Error extracting text: {error_msg}"
                })
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Error extracting text from file '{filename}': {error_msg}"
                )
            
            # 2. Generate Summary and Markdown (handle AI service errors gracefully)
            summary = None
            markdown_content = None
            ai_error_details = []
            
            try:
                summary = self.ai_service.generate_summary(text_content)
                if summary is None:
                    ai_error_details.append("Summary generation failed")
            except Exception as ai_error:
                error_msg = str(ai_error)
                ai_error_details.append(f"Summary generation error: {error_msg}")
                logger.error(f"AI Service Error generating summary for {doc_id}: {error_msg}", exc_info=True)
            
            try:
                markdown_content = self.ai_service.generate_markdown(text_content)
                if markdown_content is None:
                    ai_error_details.append("Markdown generation failed")
            except Exception as ai_error:
                error_msg = str(ai_error)
                ai_error_details.append(f"Markdown generation error: {error_msg}")
                logger.error(f"AI Service Error generating markdown for {doc_id}: {error_msg}", exc_info=True)
            
            # 3. Generate Tags using AI (with summary for better context if available)
            tags = await self._generate_tags(text_content, summary, doc_id)
            
            # 4. Extract structured fields (currently disabled)
            document_category = None
            extracted_fields = {}
            
            # 5. Generate embedding for semantic search
            embedding = await self._generate_embedding(
                text_content, summary, tags, extracted_fields, doc_id
            )
            
            # Determine if AI processing failed critically
            ai_failed = len(ai_error_details) > 0 or (summary is None and markdown_content is None)
            ai_unavailable = any("insufficient credits" in err.lower() or "api key" in err.lower() or "402" in err 
                                 for err in ai_error_details)
            
            # Check if AI processing failed (returns None)
            if ai_failed:
                error_message = "; ".join(ai_error_details) if ai_error_details else "AI processing failed"
                
                if ai_unavailable:
                    # AI service unavailable (credits/API key) - mark as ready (can retry later)
                    logger.warning(f"AI Service unavailable for {doc_id} - marking as ready (can retry)")
                    update_data = {
                        "status": "ready",
                        "summary": None,
                        "markdown_path": None,
                        "tags": tags,
                        "extracted_fields": extracted_fields if extracted_fields else None,
                        "embedding": embedding if embedding else None,
                        "ai_error": error_message,  # Store error for reference
                        "ai_processing_failed": True  # Flag to indicate AI failed
                    }
                else:
                    # Critical AI failure - mark as failed
                    logger.error(f"AI processing failed for {doc_id}: {error_message}")
                    update_data = {
                        "status": "failed",
                        "error": f"AI processing failed: {error_message}",
                        "summary": summary,  # Keep partial results if available
                        "markdown_path": None,
                        "tags": tags,
                        "extracted_fields": extracted_fields if extracted_fields else None,
                        "embedding": embedding if embedding else None,
                        "ai_error": error_message,
                        "ai_processing_failed": True
                    }
                
                await self.db_service.update_document(doc_id, update_data)
                
                # If critical failure, raise exception to trigger retry mechanism
                if not ai_unavailable:
                    raise Exception(f"AI processing failed: {error_message}")
                
                return  # Exit early for unavailable AI (document still usable)
            
            # 6. Save Markdown
            md_filename = f"{doc_id}_processed.md"
            md_path = UPLOAD_DIR / md_filename
            await self.file_service.save_markdown(markdown_content, md_path)
            
            # 7. Update DB with AI-generated content
            update_data = {
                "summary": summary,
                "markdown_path": md_filename,  # Store relative path
                "tags": tags,
                "extracted_fields": extracted_fields if extracted_fields else None,
                "embedding": embedding if embedding else None,
                "status": "completed",
                "modified_date": datetime.now().isoformat()
            }
            
            # Preserve existing folder assignment
            current_doc = await self.db_service.get_document(doc_id)
            existing_folder_before = current_doc.get("folder") if current_doc else None
            if existing_folder_before:
                logger.info(f"Document {doc_id} already in folder '{existing_folder_before}', preserving folder assignment")
            
            # 8. Attempt database write with retry logic
            db_write_success = False
            max_db_retries = 3
            db_retry_count = 0
            
            while not db_write_success and db_retry_count < max_db_retries:
                try:
                    await self.db_service.update_document(doc_id, update_data)
                    db_write_success = True
                    logger.info(f"Successfully completed AI processing and DB write for {doc_id}")
                except Exception as db_error:
                    db_retry_count += 1
                    error_msg = str(db_error)
                    logger.error(
                        f"Database write failed for {doc_id} (attempt {db_retry_count}/{max_db_retries}): {error_msg}",
                        exc_info=True
                    )
                    
                    if db_retry_count >= max_db_retries:
                        # Max retries reached - store AI results for manual recovery
                        logger.error(f"Database write failed after {max_db_retries} attempts for {doc_id}. Storing AI results for recovery.")
                        
                        # Store AI results in a temporary field for recovery
                        await self._store_ai_results_for_recovery(
                            doc_id,
                            summary,
                            markdown_content,
                            md_filename,
                            tags,
                            extracted_fields,
                            embedding,
                            error_msg
                        )
                        
                        # Mark as failed with specific DB error flag
                        try:
                            await self.db_service.update_document(doc_id, {
                                "status": "failed",
                                "error": f"Database write failed: {error_msg}",
                                "db_write_failed": True,
                                "ai_processing_succeeded": True,  # Flag indicating AI succeeded
                                "ai_results_pending": True  # Flag indicating results are stored for recovery
                            })
                        except Exception as final_error:
                            # Even the error update failed - log and continue
                            logger.critical(
                                f"CRITICAL: Cannot update document {doc_id} even with error status. "
                                f"AI results may be lost. Error: {final_error}",
                                exc_info=True
                            )
                        
                        raise Exception(f"Database write failed after {max_db_retries} retries: {error_msg}")
                    else:
                        # Wait before retry (exponential backoff)
                        import asyncio
                        retry_delay = 2 ** db_retry_count  # 2s, 4s, 8s
                        logger.info(f"Retrying database write for {doc_id} in {retry_delay} seconds...")
                        await asyncio.sleep(retry_delay)
            
        except HTTPException:
            # HTTP exceptions are already handled above, re-raise
            raise
        except Exception as e:
            error_msg = str(e)
            error_str = error_msg.lower()
            logger.error(f"Fatal error processing {doc_id}: {error_msg}", exc_info=True)
            
            # Check if it's a database write failure (AI succeeded but DB failed)
            if "database write failed" in error_str:
                # AI processing succeeded but DB write failed
                # Results are stored for recovery - don't overwrite them
                logger.warning(f"Database write failed for {doc_id} but AI results are stored for recovery")
                # Status already set in the retry logic above
                return  # Exit early, recovery can be done via recovery endpoint
            
            # Check if it's an AI service unavailable error
            elif "insufficient credits" in error_str or "api key" in error_str or "402" in error_str:
                # AI service unavailable - mark as ready (can retry later)
                try:
                    await self.db_service.update_document(doc_id, {
                        "status": "ready",
                        "ai_error": error_msg,
                        "ai_processing_failed": True
                    })
                except Exception as db_err:
                    logger.critical(f"Cannot update document {doc_id} status: {db_err}")
            
            elif "ai processing failed" in error_str:
                # AI processing failed but document is still valid
                # Status already set above, just ensure error is stored
                try:
                    current_doc = await self.db_service.get_document(doc_id)
                    if current_doc and current_doc.get("status") != "failed":
                        await self.db_service.update_document(doc_id, {
                            "status": "failed",
                            "error": error_msg,
                            "ai_processing_failed": True
                        })
                except Exception as db_err:
                    logger.critical(f"Cannot update document {doc_id} status: {db_err}")
            
            else:
                # Other fatal errors - mark as failed
                try:
                    await self.db_service.update_document(doc_id, {
                        "status": "failed",
                        "error": f"Processing failed: {error_msg}",
                        "ai_processing_failed": False  # Not an AI-specific failure
                    })
                except Exception as db_err:
                    logger.critical(f"Cannot update document {doc_id} status: {db_err}")
    
    async def _generate_tags(
        self,
        text_content: str,
        summary: Optional[str],
        doc_id: str
    ) -> List[str]:
        """
        Generate tags using AI with fallback to rule-based extraction.
        
        Args:
            text_content: Document text content
            summary: Optional summary for better context
            doc_id: Document ID for logging
            
        Returns:
            List of tags
        """
        tags = []
        try:
            # Try AI-generated tags first (preferred method)
            tags = self.ai_service.generate_tags(text_content, summary)
            if tags and len(tags) > 0:
                logger.info(f"AI-generated {len(tags)} tags for {doc_id}")
            else:
                # Fallback to rule-based extraction if AI returns empty
                logger.info(f"AI tags empty for {doc_id}, falling back to rule-based extraction")
                tags = extract_tags_from_text(text_content, summary)
        except Exception as tag_error:
            logger.error(f"AI tag generation failed for {doc_id}: {tag_error}, using rule-based extraction")
            # Fallback to rule-based tag extraction
            tags = extract_tags_from_text(text_content, summary)
        
        return tags
    
    async def _generate_embedding(
        self,
        text_content: str,
        summary: Optional[str],
        tags: List[str],
        extracted_fields: Dict[str, Any],
        doc_id: str
    ) -> Optional[List[float]]:
        """
        Generate embedding for semantic search.
        
        Args:
            text_content: Document text content
            summary: Optional summary
            tags: List of tags
            extracted_fields: Extracted structured fields
            doc_id: Document ID for logging
            
        Returns:
            Embedding vector or None if generation fails
        """
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
            
            embedding = self.ai_service.generate_embedding(searchable_text)
            if embedding and len(embedding) > 0:
                logger.info(f"Generated embedding for {doc_id} (dimension: {len(embedding)})")
            else:
                logger.error(f"Failed to generate embedding for {doc_id}")
        except Exception as embedding_error:
            logger.error(f"Embedding generation failed for {doc_id}: {embedding_error}")
        
        return embedding
    
    async def _store_ai_results_for_recovery(
        self,
        doc_id: str,
        summary: Optional[str],
        markdown_content: Optional[str],
        md_filename: str,
        tags: List[str],
        extracted_fields: Dict[str, Any],
        embedding: Optional[List[float]],
        error_msg: str
    ):
        """
        Store AI processing results temporarily for recovery when DB write fails.
        
        This allows retrying the DB write without re-running expensive AI processing.
        
        Args:
            doc_id: Document ID
            summary: Generated summary
            markdown_content: Generated markdown content
            md_filename: Markdown filename
            tags: Generated tags
            extracted_fields: Extracted structured fields
            embedding: Generated embedding
            error_msg: Database error message
        """
        try:
            # Try to store in a recovery field (if DB supports it)
            # Fallback: Store in a separate recovery file
            recovery_data = {
                "summary": summary,
                "markdown_content": markdown_content,
                "markdown_filename": md_filename,
                "tags": tags,
                "extracted_fields": extracted_fields,
                "embedding": embedding,
                "stored_at": datetime.now().isoformat(),
                "db_error": error_msg
            }
            
            # Try to store in document metadata (if possible)
            try:
                await self.db_service.update_document(doc_id, {
                    "ai_results_recovery": recovery_data
                })
                logger.info(f"Stored AI results for recovery in document metadata for {doc_id}")
            except Exception:
                # If that fails, try to store in a recovery file
                recovery_file = UPLOAD_DIR / f"{doc_id}_ai_results_recovery.json"
                import json
                try:
                    with open(recovery_file, 'w') as f:
                        json.dump(recovery_data, f, indent=2)
                    logger.info(f"Stored AI results for recovery in file: {recovery_file}")
                except Exception as file_err:
                    logger.error(f"Failed to store AI results for recovery: {file_err}")
        except Exception as e:
            logger.error(f"Error storing AI results for recovery for {doc_id}: {e}", exc_info=True)
    
    async def recover_ai_results(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Recover stored AI results for a document that had DB write failure.
        
        Args:
            doc_id: Document ID
            
        Returns:
            Dictionary with AI results if found, None otherwise
        """
        try:
            # Try to get from document metadata first
            doc = await self.db_service.get_document(doc_id)
            if doc and doc.get("ai_results_recovery"):
                return doc.get("ai_results_recovery")
            
            # Try to get from recovery file
            recovery_file = UPLOAD_DIR / f"{doc_id}_ai_results_recovery.json"
            if recovery_file.exists():
                import json
                with open(recovery_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error recovering AI results for {doc_id}: {e}", exc_info=True)
        
        return None
    
    async def retry_db_write(self, doc_id: str) -> bool:
        """
        Retry database write for a document that had DB write failure after AI success.
        
        Args:
            doc_id: Document ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Recover AI results
            recovery_data = await self.recover_ai_results(doc_id)
            if not recovery_data:
                logger.error(f"No recovery data found for {doc_id}")
                return False
            
            # Prepare update data from recovered results
            update_data = {
                "summary": recovery_data.get("summary"),
                "markdown_path": recovery_data.get("markdown_filename"),
                "tags": recovery_data.get("tags", []),
                "extracted_fields": recovery_data.get("extracted_fields"),
                "embedding": recovery_data.get("embedding"),
                "status": "completed",
                "modified_date": datetime.now().isoformat(),
                "error": None,
                "ai_error": None,
                "ai_processing_failed": False,
                "db_write_failed": False,
                "ai_processing_succeeded": False,
                "ai_results_pending": False,
                "ai_results_recovery": None  # Clear recovery data after successful write
            }
            
            # Attempt database write
            await self.db_service.update_document(doc_id, update_data)
            
            # Clean up recovery file if exists
            recovery_file = UPLOAD_DIR / f"{doc_id}_ai_results_recovery.json"
            if recovery_file.exists():
                try:
                    recovery_file.unlink()
                    logger.info(f"Cleaned up recovery file for {doc_id}")
                except Exception as cleanup_err:
                    logger.warning(f"Failed to clean up recovery file: {cleanup_err}")
            
            logger.info(f"Successfully recovered and wrote AI results to DB for {doc_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to retry DB write for {doc_id}: {e}", exc_info=True)
            return False
    
    def process_document_sync(self, doc_id: str, file_path: Path) -> None:
        """
        Wrapper for background task processing (sync wrapper for async function).
        FastAPI BackgroundTasks requires sync functions, so we run async code in event loop.
        
        Args:
            doc_id: Document ID
            file_path: Path to document file
        """
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        loop.run_until_complete(self.process_document(doc_id, file_path))

