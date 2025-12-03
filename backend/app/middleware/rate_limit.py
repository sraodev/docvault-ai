"""
Rate Limiting Middleware - Protect API from abuse.

Essential for million+ user scale to prevent:
- API abuse
- DDoS attacks
- Resource exhaustion
"""
from fastapi import Request, HTTPException
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from ..core.config import RATE_LIMIT_ENABLED, RATE_LIMIT_PER_MINUTE, RATE_LIMIT_PER_HOUR
from ..core.logging_config import get_logger

logger = get_logger(__name__)

# Initialize rate limiter
limiter = Limiter(
    key_func=get_remote_address,
    enabled=RATE_LIMIT_ENABLED
)


def get_rate_limit_key(request: Request) -> str:
    """
    Get rate limit key for request.
    
    Uses IP address by default, but can be extended to use
    API keys or user IDs for more granular control.
    """
    # Check for API key in headers
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return f"api_key:{api_key}"
    
    # Fall back to IP address
    return get_remote_address(request)


# Rate limit decorators
rate_limit_per_minute = limiter.limit(f"{RATE_LIMIT_PER_MINUTE}/minute")
rate_limit_per_hour = limiter.limit(f"{RATE_LIMIT_PER_HOUR}/hour")

