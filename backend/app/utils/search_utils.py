"""
Search utility functions for parsing queries and applying filters.
Extracted from documents router to follow Single Responsibility Principle.
"""
import re
from typing import Dict, Any, Optional
from datetime import datetime
from ..core.logging_config import get_logger

logger = get_logger(__name__)


def parse_search_filters(query: str) -> Dict[str, Any]:
    """
    Parse search query for field filters.
    Returns a dictionary with filter criteria.
    
    Args:
        query: Search query string
        
    Returns:
        Dictionary with filter criteria (amount_min, amount_max, expiring_this_year, doc_type)
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


def clean_query_for_semantic_search(query: str) -> str:
    """
    Remove filter-specific keywords from query to improve semantic search.
    
    Args:
        query: Original search query
        
    Returns:
        Cleaned query string for semantic search
    """
    # Remove amount filter keywords but keep the number
    query = re.sub(
        r"(?:above|over|more than|greater than|below|under|less than|lower than)\s*[₹$€]?\s*[\d,]+",
        "",
        query,
        flags=re.IGNORECASE
    )
    # Remove "expiring this year" but keep the intent
    query = re.sub(r"expir(?:ing|es)?\s+this\s+year", "", query, flags=re.IGNORECASE)
    # Clean up extra spaces
    query = re.sub(r"\s+", " ", query).strip()
    return query


def extract_numeric_value(amount_str: str) -> Optional[float]:
    """
    Extract numeric value from amount string (e.g., "₹50,000" -> 50000.0).
    
    Args:
        amount_str: Amount string with currency symbols
        
    Returns:
        Numeric value or None if extraction fails
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


def apply_filters(
    doc: Dict[str, Any],
    filters: Dict[str, Any],
    current_year: Optional[int] = None
) -> bool:
    """
    Apply search filters to a document.
    
    Args:
        doc: Document dictionary
        filters: Filter criteria from parse_search_filters()
        current_year: Current year for date filtering (defaults to datetime.now().year)
        
    Returns:
        True if document passes all filters, False otherwise
    """
    if current_year is None:
        current_year = datetime.now().year
    
    extracted_fields = doc.get("extracted_fields", {})
    passes_filters = True
    
    # Filter by amount (for invoices)
    if filters.get("amount_min") is not None:
        if doc.get("folder") and "Invoice" in doc.get("folder", ""):
            amount_str = extracted_fields.get("amount", "")
            if amount_str:
                amount_value = extract_numeric_value(amount_str)
                if amount_value is None or amount_value < filters["amount_min"]:
                    passes_filters = False
            else:
                passes_filters = False
        else:
            passes_filters = False
    
    if filters.get("amount_max") is not None:
        if doc.get("folder") and "Invoice" in doc.get("folder", ""):
            amount_str = extracted_fields.get("amount", "")
            if amount_str:
                amount_value = extract_numeric_value(amount_str)
                if amount_value is None or amount_value > filters["amount_max"]:
                    passes_filters = False
            else:
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
                except Exception:
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
    
    return passes_filters

