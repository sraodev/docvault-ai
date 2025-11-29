from typing import Optional, List, Dict, Any
from .providers import AIProviderFactory
from .interfaces import IAIService
import numpy as np

class AIService(IAIService):
    """
    AI service implementation.
    Handles AI operations - summary generation, markdown generation, tag generation.
    Follows Single Responsibility Principle.
    """
    def __init__(self):
        self.provider = AIProviderFactory.get_provider()
        self._fallback_provider = None  # Lazy-loaded MockProvider for fallback

    def _get_fallback_provider(self):
        """Get MockProvider as fallback when API calls fail."""
        if self._fallback_provider is None:
            from .providers import MockProvider
            self._fallback_provider = MockProvider()
        return self._fallback_provider
    
    def generate_summary(self, text: str) -> Optional[str]:
        try:
            result = self.provider.generate_summary(text)
            # Check if the result contains error messages and return None instead
            if result and ("Error generating summary" in result or "Error code:" in result):
                print(f"AI Service Error: Summary contains error message, using fallback")
                return self._get_fallback_provider().generate_summary(text)
            return result
        except Exception as e:
            error_str = str(e)
            print(f"AI Service Error: {error_str}")
            # Check if it's a credit/API key error - use fallback
            if "402" in error_str or "insufficient credits" in error_str.lower() or "api key" in error_str.lower():
                print("⚠️  API credits/key issue detected, using MockProvider fallback")
                try:
                    return self._get_fallback_provider().generate_summary(text)
                except:
                    pass
            # Return None instead of error message - let the frontend handle the display
            return None

    def generate_markdown(self, text: str) -> Optional[str]:
        try:
            result = self.provider.generate_markdown(text)
            # Check if the result contains error messages
            if result and ("Error" in result and "Error code:" in result):
                print(f"AI Service Error: Markdown contains error message, using fallback")
                return self._get_fallback_provider().generate_markdown(text)
            return result
        except Exception as e:
            error_str = str(e)
            print(f"AI Service Error: {error_str}")
            # Check if it's a credit/API key error - use fallback
            if "402" in error_str or "insufficient credits" in error_str.lower() or "api key" in error_str.lower():
                print("⚠️  API credits/key issue detected, using MockProvider fallback")
                try:
                    return self._get_fallback_provider().generate_markdown(text)
                except:
                    pass
            # Return None instead of error message
            return None

    def generate_tags(self, text: str, summary: Optional[str] = None) -> List[str]:
        """
        Generate tags using AI, with fallback to MockProvider if AI fails.
        
        Args:
            text: Document text content
            summary: Optional AI-generated summary for better context
            
        Returns:
            List of generated tags (empty list if AI fails)
        """
        try:
            result = self.provider.generate_tags(text, summary)
            # Validate result is a list
            if isinstance(result, list):
                # Filter out empty tags and limit to 8
                tags = [tag.strip() for tag in result if tag and isinstance(tag, str) and tag.strip()]
                return tags[:8]
            return []
        except Exception as e:
            error_str = str(e)
            print(f"AI Service Error generating tags: {error_str}")
            # Check if it's a credit/API key error - use fallback
            if "402" in error_str or "insufficient credits" in error_str.lower() or "api key" in error_str.lower():
                print("⚠️  API credits/key issue detected, using MockProvider fallback")
                try:
                    fallback_tags = self._get_fallback_provider().generate_tags(text, summary)
                    if isinstance(fallback_tags, list) and len(fallback_tags) > 0:
                        return fallback_tags[:8]
                except:
                    pass
            # Return empty list instead of raising - allows fallback to rule-based extraction
            return []
    
    def classify_document(self, text: str, summary: Optional[str] = None) -> Optional[str]:
        """
        Classify document into predefined category using AI.
        
        Args:
            text: Document text content
            summary: Optional AI-generated summary for better context
            
        Returns:
            Category name (Invoice, Medical Record, Resume, etc.) or None if classification fails
        """
        try:
            result = self.provider.classify_document(text, summary)
            if result and isinstance(result, str) and result.strip():
                return result.strip()
            # If result is None or empty, try fallback
            print("⚠️  Classification returned None, using MockProvider fallback")
            return self._get_fallback_provider().classify_document(text, summary)
        except Exception as e:
            error_str = str(e)
            print(f"AI Service Error classifying document: {error_str}")
            # Check if it's a credit/API key error - use fallback
            if "402" in error_str or "insufficient credits" in error_str.lower() or "api key" in error_str.lower() or "not configured" in error_str.lower():
                print("⚠️  API credits/key issue detected, using MockProvider fallback")
                try:
                    return self._get_fallback_provider().classify_document(text, summary)
                except Exception as fallback_err:
                    print(f"Fallback classification also failed: {fallback_err}")
            return None
    
    def extract_fields(self, text: str, document_category: Optional[str] = None, summary: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract structured key fields from document based on document type.
        
        Args:
            text: Document text content
            document_category: Document category (Invoice, Resume, Agreement/Contract, etc.)
            summary: Optional AI-generated summary for better context
            
        Returns:
            Dictionary with extracted fields (empty dict if extraction fails)
        """
        try:
            result = self.provider.extract_fields(text, document_category, summary)
            if isinstance(result, dict) and len(result) > 0:
                # Filter out None values and empty strings
                filtered = {k: v for k, v in result.items() if v is not None and v != ""}
                if len(filtered) > 0:
                    return filtered
            # If result is empty, try fallback
            print("⚠️  Field extraction returned empty, using MockProvider fallback")
            return self._get_fallback_provider().extract_fields(text, document_category, summary)
        except Exception as e:
            error_str = str(e)
            print(f"AI Service Error extracting fields: {error_str}")
            # Check if it's a credit/API key error - use fallback
            if "402" in error_str or "insufficient credits" in error_str.lower() or "api key" in error_str.lower() or "not configured" in error_str.lower():
                print("⚠️  API credits/key issue detected, using MockProvider fallback")
                try:
                    return self._get_fallback_provider().extract_fields(text, document_category, summary)
                except Exception as fallback_err:
                    print(f"Fallback field extraction also failed: {fallback_err}")
            return {}
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate vector embedding for text using AI.
        
        Args:
            text: Text content to generate embedding for
            
        Returns:
            List of floats representing the embedding vector (empty list if generation fails)
        """
        try:
            result = self.provider.generate_embedding(text)
            if isinstance(result, list) and len(result) > 0:
                return result
            return []
        except Exception as e:
            error_str = str(e)
            print(f"AI Service Error generating embedding: {error_str}")
            return []
    
    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        Calculate cosine similarity between two embedding vectors.
        
        Args:
            vec1: First embedding vector
            vec2: Second embedding vector
            
        Returns:
            Cosine similarity score between -1 and 1 (1 = identical, 0 = orthogonal, -1 = opposite)
        """
        try:
            if len(vec1) != len(vec2):
                return 0.0
            
            vec1_array = np.array(vec1)
            vec2_array = np.array(vec2)
            
            # Calculate cosine similarity
            dot_product = np.dot(vec1_array, vec2_array)
            norm1 = np.linalg.norm(vec1_array)
            norm2 = np.linalg.norm(vec2_array)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            similarity = dot_product / (norm1 * norm2)
            return float(similarity)
        except Exception as e:
            print(f"Error calculating cosine similarity: {e}")
            return 0.0
