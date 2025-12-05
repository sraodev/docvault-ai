"""
Error Handling Middleware

Centralized error handling and response formatting.
"""
import traceback
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from fastapi import HTTPException, status
from fastapi.exceptions import RequestValidationError
from ...core.logging_config import get_logger
from ...api.exceptions import handle_business_exception

logger = get_logger(__name__)


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that provides centralized error handling.
    
    Converts exceptions to standardized JSON error responses:
    - HTTPException → JSON response with status code
    - ValidationError → 422 with validation details
    - Business exceptions → Appropriate HTTP status codes
    - Unexpected exceptions → 500 with error details (in development)
    """
    
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
            
        except RequestValidationError as e:
            # Handle request validation errors
            logger.warning(
                f"Validation error for {request.method} {request.url.path}: {e.errors()}",
                context="Gateway"
            )
            
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={
                    "error": "Validation Error",
                    "detail": e.errors(),
                    "path": request.url.path,
                    "request_id": getattr(request.state, "request_id", None)
                }
            )
            
        except HTTPException as e:
            # Handle HTTP exceptions
            logger.debug(
                f"HTTP exception for {request.method} {request.url.path}: {e.status_code} - {e.detail}",
                context="Gateway"
            )
            
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "error": e.detail,
                    "status_code": e.status_code,
                    "path": request.url.path,
                    "request_id": getattr(request.state, "request_id", None)
                }
            )
            
        except Exception as e:
            # Handle business exceptions
            try:
                http_exception = handle_business_exception(e)
                logger.warning(
                    f"Business exception for {request.method} {request.url.path}: {http_exception.detail}",
                    context="Gateway",
                    error=e
                )
                
                return JSONResponse(
                    status_code=http_exception.status_code,
                    content={
                        "error": http_exception.detail,
                        "status_code": http_exception.status_code,
                        "path": request.url.path,
                        "request_id": getattr(request.state, "request_id", None)
                    }
                )
            except:
                # Not a business exception, handle as unexpected error
                pass
            
            # Handle unexpected exceptions
            import os
            is_development = os.getenv("ENVIRONMENT", "development") != "production"
            
            error_detail = str(e) if is_development else "Internal server error"
            error_traceback = traceback.format_exc() if is_development else None
            
            logger.error(
                f"Unexpected error for {request.method} {request.url.path}: {e}",
                context="Gateway",
                error=e
            )
            
            if error_traceback:
                logger.debug(f"Traceback:\n{error_traceback}", context="Gateway")
            
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": error_detail,
                    "status_code": 500,
                    "path": request.url.path,
                    "request_id": getattr(request.state, "request_id", None),
                    "traceback": error_traceback if is_development else None
                }
            )

