from typing import Optional, List, Dict, Any
from .providers import AIProviderFactory, MockProvider
from .interfaces import IAIService
import numpy as np
from ..core.logging_config import get_logger

logger = get_logger(__name__)

class AIService(IAIService):
    """
    AI service implementation.
    Handles AI operations - summary generation, markdown generation, tag generation.
    Follows Single Responsibility Principle.
    """
    def __init__(self):
        self.provider = AIProviderFactory.get_provider()
        self._fallback_provider = None  # Lazy-loaded MockProvider for fallback
        logger.info(f"Initialized AIService with provider: {type(self.provider).__name__}")

    def _get_fallback_provider(self):
        """Get MockProvider as fallback when API calls fail."""
        if self._fallback_provider is None:
            self._fallback_provider = MockProvider()
            logger.debug("Initialized fallback MockProvider")
        return self._fallback_provider
    
    def generate_summary(self, text: str) -> Optional[str]:
        logger.debug(f"Generating summary for text (length: {len(text)} chars)")
        try:
            result = self.provider.generate_summary(text)
            # Check if the result contains error messages and return None instead
            if result and ("Error generating summary" in result or "Error code:" in result):
                logger.error("AI Service Error: Summary contains error message, using fallback")
                return self._get_fallback_provider().generate_summary(text)
            logger.debug(f"Summary generated successfully (length: {len(result) if result else 0} chars)")
            return result
        except Exception as e:
            error_str = str(e)
            logger.error(f"AI Service Error generating summary: {error_str}", exc_info=True)
            # Check if it's a credit/API key error - use fallback
            if "402" in error_str or "insufficient credits" in error_str.lower() or "api key" in error_str.lower():
                logger.warning("API credits/key issue detected, using MockProvider fallback")
                try:
                    return self._get_fallback_provider().generate_summary(text)
                except:
                    pass
            # Return None instead of error message - let the frontend handle the display
            return None

    def generate_markdown(self, text: str) -> Optional[str]:
        logger.debug(f"Generating markdown for text (length: {len(text)} chars)")
        try:
            result = self.provider.generate_markdown(text)
            # Check if the result contains error messages
            if result and ("Error" in result and "Error code:" in result):
                logger.error("AI Service Error: Markdown contains error message, using fallback")
                return self._get_fallback_provider().generate_markdown(text)
            logger.debug(f"Markdown generated successfully (length: {len(result) if result else 0} chars)")
            return result
        except Exception as e:
            error_str = str(e)
            logger.error(f"AI Service Error generating markdown: {error_str}", exc_info=True)
            # Check if it's a credit/API key error - use fallback
            if "402" in error_str or "insufficient credits" in error_str.lower() or "api key" in error_str.lower():
                logger.warning("API credits/key issue detected, using MockProvider fallback")
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
        logger.debug(f"Generating tags for text (length: {len(text)} chars, has summary: {summary is not None})")
        try:
            result = self.provider.generate_tags(text, summary)
            # Validate result is a list
            if isinstance(result, list):
                # Filter out empty tags and limit to 8
                tags = [tag.strip() for tag in result if tag and isinstance(tag, str) and tag.strip()]
                logger.debug(f"Generated {len(tags)} tags: {tags[:5]}")
                return tags[:8]
            logger.warning("AI provider returned non-list result for tags")
            return []
        except Exception as e:
            error_str = str(e)
            logger.error(f"AI Service Error generating tags: {error_str}", exc_info=True)
            # Check if it's a credit/API key error - use fallback
            if "402" in error_str or "insufficient credits" in error_str.lower() or "api key" in error_str.lower():
                logger.warning("API credits/key issue detected, using MockProvider fallback")
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
        logger.debug(f"Classifying document (text length: {len(text)} chars, has summary: {summary is not None})")
        try:
            result = self.provider.classify_document(text, summary)
            if result and isinstance(result, str) and result.strip():
                logger.debug(f"Document classified as: {result}")
                return result.strip()
            # If result is None or empty, try fallback
            logger.warning("Classification returned None, using MockProvider fallback")
            return self._get_fallback_provider().classify_document(text, summary)
        except Exception as e:
            error_str = str(e)
            logger.error(f"AI Service Error classifying document: {error_str}", exc_info=True)
            # Check if it's a credit/API key error - use fallback
            if "402" in error_str or "insufficient credits" in error_str.lower() or "api key" in error_str.lower() or "not configured" in error_str.lower():
                logger.warning("API credits/key issue detected, using MockProvider fallback")
                try:
                    return self._get_fallback_provider().classify_document(text, summary)
                except Exception as fallback_err:
                    logger.error(f"Fallback classification also failed: {fallback_err}", exc_info=True)
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
        logger.debug(f"Extracting fields (category: {document_category}, text length: {len(text)} chars)")
        try:
            result = self.provider.extract_fields(text, document_category, summary)
            if isinstance(result, dict) and len(result) > 0:
                # Filter out None values and empty strings
                filtered = {k: v for k, v in result.items() if v is not None and v != ""}
                if len(filtered) > 0:
                    logger.debug(f"Extracted {len(filtered)} fields: {list(filtered.keys())}")
                    return filtered
            # If result is empty, try fallback
            logger.warning("Field extraction returned empty, using MockProvider fallback")
            return self._get_fallback_provider().extract_fields(text, document_category, summary)
        except Exception as e:
            error_str = str(e)
            logger.error(f"AI Service Error extracting fields: {error_str}", exc_info=True)
            # Check if it's a credit/API key error - use fallback
            if "402" in error_str or "insufficient credits" in error_str.lower() or "api key" in error_str.lower() or "not configured" in error_str.lower():
                logger.warning("API credits/key issue detected, using MockProvider fallback")
                try:
                    return self._get_fallback_provider().extract_fields(text, document_category, summary)
                except Exception as fallback_err:
                    logger.error(f"Fallback field extraction also failed: {fallback_err}", exc_info=True)
            return {}
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate vector embedding for text using AI.
        
        Args:
            text: Text content to generate embedding for
            
        Returns:
            List of floats representing the embedding vector (empty list if generation fails)
        """
        logger.debug(f"Generating embedding for text (length: {len(text)} chars)")
        try:
            result = self.provider.generate_embedding(text)
            if isinstance(result, list) and len(result) > 0:
                logger.debug(f"Generated embedding with dimension: {len(result)}")
                return result
            logger.warning("Embedding generation returned empty result")
            return []
        except Exception as e:
            error_str = str(e)
            logger.error(f"AI Service Error generating embedding: {error_str}", exc_info=True)
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
                logger.warning(f"Vector dimension mismatch: {len(vec1)} vs {len(vec2)}")
                return 0.0
            
            vec1_array = np.array(vec1)
            vec2_array = np.array(vec2)
            
            # Calculate cosine similarity
            dot_product = np.dot(vec1_array, vec2_array)
            norm1 = np.linalg.norm(vec1_array)
            norm2 = np.linalg.norm(vec2_array)
            
            if norm1 == 0 or norm2 == 0:
                logger.warning("Zero norm detected in cosine similarity calculation")
                return 0.0
            
            similarity = dot_product / (norm1 * norm2)
            return float(similarity)
        except Exception as e:
            logger.error(f"Error calculating cosine similarity: {e}", exc_info=True)
            return 0.0
