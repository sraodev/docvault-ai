"""
AI Retry Handler

Handles automatic retry logic for failed AI processing.
Provides exponential backoff and retry limits for AI operations.
"""
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from ..core.logging_config import get_logger

logger = get_logger(__name__)


class AIRetryHandler:
    """
    Handles retry logic for AI processing failures.
    
    Features:
    - Exponential backoff for retries
    - Maximum retry attempts
    - Retry delay calculation
    - Failure tracking
    """
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: int = 60,  # 1 minute
        max_delay: int = 3600,  # 1 hour
        backoff_multiplier: float = 2.0
    ):
        """
        Initialize AI retry handler.
        
        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Base delay in seconds before first retry
            max_delay: Maximum delay in seconds between retries
            backoff_multiplier: Multiplier for exponential backoff
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_multiplier = backoff_multiplier
    
    def should_retry(
        self,
        doc: Dict[str, Any],
        error: Optional[str] = None
    ) -> bool:
        """
        Determine if a document should be retried.
        
        Args:
            doc: Document dictionary
            error: Optional error message
            
        Returns:
            True if document should be retried, False otherwise
        """
        status = doc.get("status", "ready")
        
        # Only retry failed documents
        if status != "failed":
            return False
        
        # Check if it's an AI-specific failure
        ai_failed = doc.get("ai_processing_failed", False)
        if not ai_failed:
            # Not an AI failure, don't retry automatically
            return False
        
        # Check retry count
        retry_count = doc.get("ai_retry_count", 0)
        if retry_count >= self.max_retries:
            logger.info(f"Document {doc.get('id')} exceeded max retries ({self.max_retries})")
            return False
        
        # Check if error is retryable
        error_str = (error or doc.get("error") or doc.get("ai_error") or "").lower()
        
        # Don't retry for non-retryable errors
        non_retryable_errors = [
            "format not supported",
            "file not found",
            "permission denied",
            "invalid file"
        ]
        
        if any(err in error_str for err in non_retryable_errors):
            logger.info(f"Document {doc.get('id')} has non-retryable error: {error_str}")
            return False
        
        return True
    
    def calculate_retry_delay(self, retry_count: int) -> int:
        """
        Calculate delay before next retry using exponential backoff.
        
        Args:
            retry_count: Current retry attempt number (0-indexed)
            
        Returns:
            Delay in seconds
        """
        delay = int(self.base_delay * (self.backoff_multiplier ** retry_count))
        return min(delay, self.max_delay)
    
    def get_next_retry_time(self, retry_count: int) -> datetime:
        """
        Get the next retry time based on retry count.
        
        Args:
            retry_count: Current retry attempt number
            
        Returns:
            Datetime when next retry should occur
        """
        delay = self.calculate_retry_delay(retry_count)
        return datetime.now() + timedelta(seconds=delay)
    
    def increment_retry_count(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """
        Increment retry count for a document.
        
        Args:
            doc: Document dictionary
            
        Returns:
            Updated document dictionary with incremented retry count
        """
        retry_count = doc.get("ai_retry_count", 0) + 1
        next_retry_time = self.get_next_retry_time(retry_count - 1)
        
        return {
            "ai_retry_count": retry_count,
            "ai_next_retry_time": next_retry_time.isoformat(),
            "status": "ready"  # Reset to ready for retry
        }
    
    def mark_permanent_failure(self, doc: Dict[str, Any], reason: str) -> Dict[str, Any]:
        """
        Mark a document as permanently failed (no more retries).
        
        Args:
            doc: Document dictionary
            reason: Reason for permanent failure
            
        Returns:
            Updated document dictionary
        """
        return {
            "status": "failed",
            "ai_retry_count": self.max_retries,
            "ai_permanent_failure": True,
            "ai_permanent_failure_reason": reason
        }


# Global instance
ai_retry_handler = AIRetryHandler()

