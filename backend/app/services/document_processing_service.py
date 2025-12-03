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
            
            try:
                summary = self.ai_service.generate_summary(text_content)
                markdown_content = self.ai_service.generate_markdown(text_content)
            except Exception as ai_error:
                logger.error(f"AI Service Error for {doc_id}: {ai_error}")
            
            # 3. Generate Tags using AI (with summary for better context if available)
            tags = await self._generate_tags(text_content, summary, doc_id)
            
            # 4. Extract structured fields (currently disabled)
            document_category = None
            extracted_fields = {}
            
            # 5. Generate embedding for semantic search
            embedding = await self._generate_embedding(
                text_content, summary, tags, extracted_fields, doc_id
            )
            
            # Check if AI processing failed (returns None)
            if summary is None or markdown_content is None:
                logger.info(f"AI Service unavailable for {doc_id} - marking as ready")
                
                update_data = {
                    "status": "ready",
                    "summary": None,
                    "markdown_path": None,
                    "tags": tags,
                    "extracted_fields": extracted_fields if extracted_fields else None,
                    "embedding": embedding if embedding else None
                }
                
                await self.db_service.update_document(doc_id, update_data)
                return  # Exit early, document is still usable without AI processing
            
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
            
            await self.db_service.update_document(doc_id, update_data)
            
        except Exception as e:
            logger.error(f"Fatal error processing {doc_id}: {e}")
            # Don't mark as failed if it's just AI service unavailable - keep as ready
            error_str = str(e).lower()
            if "insufficient credits" in error_str or "api key" in error_str or "402" in error_str:
                await self.db_service.update_document(doc_id, {"status": "ready"})
            else:
                await self.db_service.update_document(doc_id, {"status": "failed"})
    
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

