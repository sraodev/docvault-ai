"""
Mock AI Provider.

Provides mock implementations for testing and fallback scenarios.
Does not make actual API calls, returns simulated responses.
"""
from typing import Optional, List, Dict, Any
import random
import math
import hashlib
from ...core.logging_config import get_logger
from .base import AIProvider

logger = get_logger(__name__)


class MockProvider(AIProvider):
    """
    Mock AI Provider for testing and fallback scenarios.
    
    Provides simulated AI responses without making actual API calls.
    Useful for:
    - Development and testing
    - Fallback when API keys are not configured
    - Offline development
    """
    
    def generate_summary(self, text: str) -> str:
        """Generate a mock summary for testing."""
        return "This is a MOCK summary. The document appears to contain information about..." + text[:100] + "..."

    def generate_markdown(self, text: str) -> str:
        """Generate mock markdown for testing."""
        return f"# Mock Markdown\n\nThis is a generated markdown representation.\n\n## Extracted Content\n{text[:500]}..."
    
    def generate_tags(self, text: str, summary: Optional[str] = None) -> List[str]:
        """Generate mock tags for testing."""
        # Extract some basic keywords from text as mock tags
        words = text.lower().split()
        # Simple keyword extraction (first few unique words)
        unique_words = []
        for word in words:
            if len(word) > 4 and word not in unique_words and word.isalpha():
                unique_words.append(word)
                if len(unique_words) >= 5:
                    break
        return unique_words[:5] if unique_words else ["document", "content", "text"]
    
    def classify_document(self, text: str, summary: Optional[str] = None) -> Optional[str]:
        """Generate mock classification for testing."""
        text_lower = text.lower()
        
        # Simple keyword-based classification
        if any(word in text_lower for word in ["invoice", "bill", "payment", "due", "amount"]):
            return "Invoice"
        elif any(word in text_lower for word in ["medical", "patient", "diagnosis", "prescription", "doctor"]):
            return "Medical Record"
        elif any(word in text_lower for word in ["resume", "cv", "curriculum vitae", "experience", "skills", "education"]):
            return "Resume"
        elif any(word in text_lower for word in ["agreement", "contract", "terms", "signature", "party"]):
            return "Agreement/Contract"
        elif any(word in text_lower for word in ["research", "study", "paper", "abstract", "methodology", "conclusion"]):
            return "Research Paper"
        elif any(word in text_lower for word in ["bank", "statement", "account", "balance", "transaction", "deposit"]):
            return "Bank Statement"
        else:
            return "Other"
    
    def extract_fields(self, text: str, document_category: Optional[str] = None, summary: Optional[str] = None) -> Dict[str, Any]:
        """Generate mock extracted fields for testing."""
        # Mock field extraction based on category
        if document_category == "Invoice":
            return {
                "vendor": "Mock Vendor Inc.",
                "amount": "1000.00 USD",
                "date": "2024-01-15",
                "invoice_number": "INV-MOCK-001"
            }
        elif document_category == "Resume":
            return {
                "name": "John Doe",
                "skills": "Python, JavaScript, React, Node.js",
                "experience_years": "5",
                "email": "john.doe@example.com"
            }
        elif document_category == "Agreement/Contract":
            return {
                "parties_involved": "Party A, Party B",
                "start_date": "2024-01-01",
                "end_date": "2024-12-31"
            }
        else:
            return {
                "key_information": "Mock extracted information"
            }
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate mock embedding for testing (returns a fixed-size vector).
        
        Returns a 1536-dimensional vector (same as text-embedding-ada-002).
        Uses text hash as seed for deterministic mock embeddings.
        """
        # Return a mock 1536-dimensional vector (same as text-embedding-ada-002)
        # Generate a simple mock embedding based on text hash
        hash_obj = hashlib.md5(text.encode())
        seed = int(hash_obj.hexdigest(), 16) % (2**32)
        random.seed(seed)
        # Generate 1536 random floats between -1 and 1, normalized
        mock_embedding = [random.uniform(-1, 1) for _ in range(1536)]
        # Normalize the vector
        norm = math.sqrt(sum(x*x for x in mock_embedding))
        if norm > 0:
            mock_embedding = [x / norm for x in mock_embedding]
        return mock_embedding

