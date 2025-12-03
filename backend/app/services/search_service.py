"""
Search Service - Handles semantic and text-based search operations.
Extracted from documents router to follow Single Responsibility Principle.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime

from .ai_service import AIService
from ..utils.search_utils import (
    parse_search_filters,
    clean_query_for_semantic_search,
    apply_filters,
    extract_numeric_value
)
from ..core.logging_config import get_logger

logger = get_logger(__name__)


class SearchService:
    """
    Service for document search operations.
    Handles semantic search with embeddings and fallback to text search.
    """
    
    def __init__(self, ai_service: AIService, db_service):
        """
        Initialize search service.
        
        Args:
            ai_service: AIService instance
            db_service: Database service instance
        """
        self.ai_service = ai_service
        self.db_service = db_service
    
    async def semantic_search(
        self,
        query: str,
        limit: Optional[int] = 10,
        min_similarity: Optional[float] = 0.3
    ) -> Dict[str, Any]:
        """
        AI-Based Semantic Search across all documents.
        
        Uses embeddings + cosine similarity to find relevant documents.
        Supports natural language queries like:
        - "Find invoices above ₹50,000"
        - "Resume containing Python senior engineer"
        - "Contracts expiring this year"
        
        Args:
            query: Search query string
            limit: Maximum number of results to return
            min_similarity: Minimum cosine similarity score (0.0 to 1.0)
            
        Returns:
            Dict with search results and metadata
        """
        # 1. Parse query for field filters
        query_text = query.strip()
        filters = parse_search_filters(query_text)
        
        # Remove filter keywords from query text for semantic search
        semantic_query = clean_query_for_semantic_search(query_text)
        
        # 2. Generate embedding for query
        query_embedding = self.ai_service.generate_embedding(semantic_query)
        
        # 3. Get all documents
        all_docs = await self.db_service.get_all_documents(folder=None)
        
        # 4. Calculate similarity scores or fallback to text search
        results = []
        current_year = datetime.now().year
        
        # Check if we have embeddings available
        has_embeddings = query_embedding and len(query_embedding) > 0
        docs_with_embeddings = [
            doc for doc in all_docs
            if doc.get("embedding") and len(doc.get("embedding", [])) > 0
        ]
        
        if has_embeddings and len(docs_with_embeddings) > 0:
            # Use semantic search with embeddings
            results = await self._semantic_search_with_embeddings(
                all_docs, query_embedding, filters, min_similarity, current_year
            )
        else:
            # Fallback to text-based search when embeddings are not available
            results = await self._text_based_search(
                all_docs, semantic_query, filters, current_year
            )
        
        # 5. Sort by similarity (descending)
        results.sort(key=lambda x: x["similarity"], reverse=True)
        
        # 6. Apply limit
        limited_results = results[:limit] if limit else results
        
        # 7. Format response
        return {
            "query": query,
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
    
    async def _semantic_search_with_embeddings(
        self,
        all_docs: List[Dict[str, Any]],
        query_embedding: List[float],
        filters: Dict[str, Any],
        min_similarity: float,
        current_year: int
    ) -> List[Dict[str, Any]]:
        """Perform semantic search using embeddings."""
        results = []
        
        for doc in all_docs:
            doc_embedding = doc.get("embedding")
            if not doc_embedding or len(doc_embedding) == 0:
                continue  # Skip documents without embeddings
            
            # Calculate cosine similarity
            similarity = self.ai_service.cosine_similarity(query_embedding, doc_embedding)
            
            if similarity < min_similarity:
                continue  # Skip low similarity results
            
            # Apply field filters if specified
            if not apply_filters(doc, filters, current_year):
                continue
            
            results.append({
                "document": doc,
                "similarity": similarity,
                "score": similarity
            })
        
        return results
    
    async def _text_based_search(
        self,
        all_docs: List[Dict[str, Any]],
        semantic_query: str,
        filters: Dict[str, Any],
        current_year: int
    ) -> List[Dict[str, Any]]:
        """Perform text-based search when embeddings are not available."""
        results = []
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
            if not apply_filters(doc, filters, current_year):
                continue
            
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
        
        return results

