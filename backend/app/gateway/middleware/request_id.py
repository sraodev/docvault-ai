"""
Request ID Middleware

Adds a unique request ID to each request for tracing and debugging.
"""
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from ...core.logging_config import get_logger

logger = get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds a unique request ID to each request.
    
    The request ID is:
    - Added to request headers as X-Request-ID
    - Added to response headers as X-Request-ID
    - Available in request.state.request_id for logging
    
    This enables request tracing across distributed systems.
    """
    
    async def dispatch(self, request: Request, call_next):
        # Check if request ID already exists (from upstream proxy)
        request_id = request.headers.get("X-Request-ID")
        
        if not request_id:
            # Generate new request ID
            request_id = str(uuid.uuid4())
        
        # Store in request state for access in handlers
        request.state.request_id = request_id
        
        # Add to response headers
        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        
        return response

