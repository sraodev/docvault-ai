"""
Request Logging Middleware

Logs all incoming requests and responses with timing information.
"""
import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from typing import Callable
from ...core.logging_config import get_logger

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that logs all HTTP requests and responses.
    
    Logs:
    - Request method, path, and query parameters
    - Request ID (if available)
    - Response status code
    - Request duration in milliseconds
    - Client IP address
    
    Skips logging for health check endpoints to reduce noise.
    """
    
    def __init__(self, app, skip_paths: list[str] = None):
        """
        Initialize request logging middleware.
        
        Args:
            app: ASGI application
            skip_paths: List of paths to skip logging (e.g., ["/health", "/ready"])
        """
        super().__init__(app)
        self.skip_paths = skip_paths or ["/health", "/ready", "/docs", "/redoc", "/openapi.json"]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip logging for certain paths
        if any(request.url.path.startswith(path) for path in self.skip_paths):
            return await call_next(request)
        
        # Get request ID if available
        request_id = getattr(request.state, "request_id", None)
        request_id_str = f" [{request_id}]" if request_id else ""
        
        # Log request
        start_time = time.time()
        method = request.method
        path = request.url.path
        query_params = str(request.query_params) if request.query_params else ""
        
        logger.info(
            f"→ {method} {path}{'?' + query_params if query_params else ''}{request_id_str}",
            context="Gateway"
        )
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Log response
            status_code = response.status_code
            status_emoji = "✅" if 200 <= status_code < 300 else "⚠️" if 400 <= status_code < 500 else "❌"
            
            logger.info(
                f"{status_emoji} {method} {path} → {status_code} ({duration_ms:.2f}ms){request_id_str}",
                context="Gateway"
            )
            
            return response
            
        except Exception as e:
            # Log error
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                f"❌ {method} {path} → Exception after {duration_ms:.2f}ms{request_id_str}: {e}",
                context="Gateway",
                error=e
            )
            raise

