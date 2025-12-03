"""
Search Router - Handles search and tag operations.

This router provides search functionality:
- Semantic search using AI embeddings
- Text-based search fallback
- Tag-based document filtering
- Natural language query parsing

Architecture:
- Router handles HTTP request/response only
- SearchService handles all search logic
- Supports natural language queries with field filtering

Example Usage:
    GET /documents/search?q="invoices above ₹50,000"
    GET /documents/tags - Get all tags
    GET /documents/tags/{tag} - Get documents by tag
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict, Any, List

from .dependencies import get_search_service, get_db_service
from ..utils.document_utils import ensure_document_fields
from ..core.logging_config import get_logger

logger = get_logger(__name__)

# Create router instance
router = APIRouter()


@router.get("/documents/search")
async def semantic_search(
    q: str = Query(..., description="Search query"),
    limit: Optional[int] = Query(10, description="Maximum number of results"),
    min_similarity: Optional[float] = Query(0.3, description="Minimum cosine similarity score")
):
    """
    AI-Based Semantic Search across all documents.
    
    This endpoint performs intelligent search using:
    - Vector embeddings for semantic understanding
    - Cosine similarity for relevance scoring
    - Natural language query parsing
    - Field-based filtering (amount, date, document type)
    
    Search Modes:
    1. Semantic Search (preferred): Uses AI embeddings when available
    2. Text Search (fallback): Keyword matching when embeddings unavailable
    
    Query Examples:
    - "invoices above ₹50,000" → Finds invoices with amount > 50000
    - "resume containing Python senior engineer" → Finds resumes with those keywords
    - "contracts expiring this year" → Finds contracts ending in current year
    - "medical records from 2023" → Finds medical records from 2023
    
    Args:
        q: Search query string (required)
           Supports natural language with filters
        limit: Maximum number of results to return (default: 10)
        min_similarity: Minimum similarity score 0.0-1.0 (default: 0.3)
                       Higher = more strict matching
    
    Returns:
        dict: Search results with metadata
        
    Example Request:
        GET /documents/search?q=invoices%20above%20₹50000&limit=20
    
    Example Response:
        {
            "query": "invoices above ₹50000",
            "semantic_query": "invoices",
            "search_mode": "semantic",
            "filters_applied": {"amount_min": 50000, "doc_type": "Invoice"},
            "total_results": 5,
            "returned_results": 5,
            "results": [
                {
                    "document_id": "abc-123",
                    "filename": "invoice1.pdf",
                    "similarity_score": 0.95,
                    ...
                }
            ]
        }
    
    Note:
        - Falls back to text search if embeddings unavailable
        - Filters are applied after similarity calculation
        - Results sorted by relevance (highest similarity first)
    """
    try:
        # Get search service via dependency injection
        search_service = get_search_service()
        
        # Delegate search to service layer
        # Service handles: query parsing, embedding generation, filtering, ranking
        return await search_service.semantic_search(q, limit, min_similarity)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )


@router.get("/documents/tags")
async def get_all_tags():
    """
    Get all unique AI tags across all documents.
    Returns tags with counts.
    """
    try:
        db_service = get_db_service()
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
        
        # Build mapping of lowercase to original case
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
        tag_counts_with_case = {
            original_case_map.get(tag, tag): count
            for tag, count in tag_counts.items()
        }
        
        return {
            "tags": tags_with_case,
            "tag_counts": tag_counts_with_case,
            "total_tags": len(tags_with_case)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve tags: {str(e)}")


@router.get("/documents/tags/{tag}")
async def get_documents_by_tag(tag: str):
    """
    Get all documents that have a specific tag.
    Tag matching is case-insensitive.
    """
    try:
        db_service = get_db_service()
        all_docs = await db_service.get_all_documents()
        
        # Filter documents that have this tag (case-insensitive)
        tag_lower = tag.strip().lower()
        matching_docs = []
        
        for doc in all_docs:
            doc_tags = doc.get("tags")
            if doc_tags and isinstance(doc_tags, list):
                if any(
                    t and isinstance(t, str) and t.strip().lower() == tag_lower
                    for t in doc_tags
                ):
                    matching_docs.append(doc)
        
        # Ensure all documents have required fields
        for doc in matching_docs:
            await ensure_document_fields(doc, db_service)
        
        return matching_docs
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve documents by tag: {str(e)}"
        )

