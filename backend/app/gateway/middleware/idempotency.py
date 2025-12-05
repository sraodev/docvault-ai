"""
Idempotency Key Middleware

Handles idempotency keys for API requests to prevent duplicate operations.
Stores request results and returns cached responses for duplicate requests.

Features:
- Validates idempotency keys from request headers
- Stores request results in cache (Redis or in-memory fallback)
- Returns cached responses for duplicate requests
- Supports configurable TTL for cached results
"""
import json
import hashlib
from typing import Optional, Dict, Any
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from datetime import datetime, timedelta
from ...core.logging_config import get_logger
from ...core.config import REDIS_HOST, REDIS_PORT

logger = get_logger(__name__)

# Idempotency key header name
IDEMPOTENCY_KEY_HEADER = "Idempotency-Key"
IDEMPOTENCY_KEY_HEADER_LOWER = "idempotency-key"

# Default TTL for cached responses (24 hours)
DEFAULT_IDEMPOTENCY_TTL = 86400  # 24 hours in seconds

# Methods that should support idempotency
IDEMPOTENT_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class IdempotencyStorage:
    """Storage backend for idempotency keys."""
    
    def __init__(self):
        self._redis = None
        self._memory_cache: Dict[str, Dict[str, Any]] = {}
        self._use_redis = False
        
    async def _get_redis(self):
        """Lazy initialization of Redis connection."""
        if self._redis is None:
            try:
                import aioredis
                self._redis = await aioredis.from_url(
                    f"redis://{REDIS_HOST}:{REDIS_PORT}/3",  # Use DB 3 for idempotency
                    encoding="utf-8",
                    decode_responses=True
                )
                self._use_redis = True
                logger.info("Idempotency: Using Redis storage")
            except Exception as e:
                logger.warning(f"Idempotency: Redis not available, using in-memory cache: {e}")
                self._use_redis = False
        return self._redis
    
    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached response for idempotency key."""
        try:
            if self._use_redis:
                redis = await self._get_redis()
                if redis:
                    cached = await redis.get(f"idempotency:{key}")
                    if cached:
                        return json.loads(cached)
            else:
                # In-memory cache
                if key in self._memory_cache:
                    cached = self._memory_cache[key]
                    # Check if expired
                    if datetime.fromisoformat(cached["expires_at"]) > datetime.now():
                        return cached["data"]
                    else:
                        # Remove expired entry
                        del self._memory_cache[key]
        except Exception as e:
            logger.error(f"Error getting idempotency key {key}: {e}")
        return None
    
    async def set(self, key: str, data: Dict[str, Any], ttl: int = DEFAULT_IDEMPOTENCY_TTL):
        """Store response for idempotency key."""
        try:
            expires_at = (datetime.now() + timedelta(seconds=ttl)).isoformat()
            cache_data = {
                "data": data,
                "expires_at": expires_at,
                "created_at": datetime.now().isoformat()
            }
            
            if self._use_redis:
                redis = await self._get_redis()
                if redis:
                    await redis.setex(
                        f"idempotency:{key}",
                        ttl,
                        json.dumps(cache_data)
                    )
                    return
            else:
                # In-memory cache
                self._memory_cache[key] = cache_data
                # Limit cache size (remove oldest entries if > 10000)
                if len(self._memory_cache) > 10000:
                    # Remove 10% oldest entries
                    sorted_items = sorted(
                        self._memory_cache.items(),
                        key=lambda x: x[1]["created_at"]
                    )
                    for i in range(len(sorted_items) // 10):
                        del self._memory_cache[sorted_items[i][0]]
        except Exception as e:
            logger.error(f"Error setting idempotency key {key}: {e}")
    
    async def delete(self, key: str):
        """Delete idempotency key from cache."""
        try:
            if self._use_redis:
                redis = await self._get_redis()
                if redis:
                    await redis.delete(f"idempotency:{key}")
            else:
                self._memory_cache.pop(key, None)
        except Exception as e:
            logger.error(f"Error deleting idempotency key {key}: {e}")


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """
    Middleware that handles idempotency keys for API requests.
    
    When a request includes an Idempotency-Key header:
    1. Checks if a cached response exists for that key
    2. If found, returns cached response immediately
    3. If not found, processes request and caches the response
    4. Returns the response with Idempotency-Key header
    
    This ensures that duplicate requests with the same idempotency key
    return the same result without re-executing the operation.
    """
    
    def __init__(self, app, ttl: int = DEFAULT_IDEMPOTENCY_TTL):
        super().__init__(app)
        self.storage = IdempotencyStorage()
        self.ttl = ttl
    
    async def dispatch(self, request: Request, call_next):
        # Only process idempotency for methods that modify state
        if request.method not in IDEMPOTENT_METHODS:
            return await call_next(request)
        
        # Get idempotency key from header
        idempotency_key = request.headers.get(IDEMPOTENCY_KEY_HEADER) or \
                         request.headers.get(IDEMPOTENCY_KEY_HEADER_LOWER)
        
        # If no idempotency key, proceed normally
        if not idempotency_key:
            return await call_next(request)
        
        # Validate idempotency key format (should be UUID or similar)
        if len(idempotency_key) > 128:  # Reasonable limit
            return JSONResponse(
                status_code=400,
                content={"detail": "Idempotency-Key header too long (max 128 characters)"}
            )
        
        # Generate cache key from idempotency key + method + path
        # This ensures different endpoints have different caches
        cache_key = self._generate_cache_key(idempotency_key, request.method, str(request.url.path))
        
        # Check for cached response
        cached_response = await self.storage.get(cache_key)
        
        if cached_response:
            logger.info(f"Idempotency: Returning cached response for key {idempotency_key[:8]}...")
            
            # Return cached response
            response = JSONResponse(
                content=cached_response["body"],
                status_code=cached_response["status_code"]
            )
            
            # Add idempotency key to response headers
            response.headers[IDEMPOTENCY_KEY_HEADER] = idempotency_key
            response.headers["X-Idempotency-Cached"] = "true"
            
            # Copy original response headers if present
            if "headers" in cached_response:
                for header_name, header_value in cached_response["headers"].items():
                    if header_name.lower() not in ["content-length", "content-encoding"]:
                        response.headers[header_name] = header_value
            
            return response
        
        # No cached response, process request
        logger.debug(f"Idempotency: Processing new request with key {idempotency_key[:8]}...")
        
        # Call the actual endpoint
        response = await call_next(request)
        
        # Cache successful responses (2xx status codes)
        if 200 <= response.status_code < 300:
            try:
                # Read response body
                response_body = b""
                if hasattr(response, 'body_iterator'):
                    async for chunk in response.body_iterator:
                        response_body += chunk
                elif hasattr(response, 'body'):
                    response_body = response.body
                
                # Parse JSON if possible
                try:
                    body_json = json.loads(response_body.decode('utf-8'))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    # If not JSON, store as string
                    body_json = response_body.decode('utf-8', errors='replace')
                
                # Store in cache
                await self.storage.set(cache_key, {
                    "status_code": response.status_code,
                    "body": body_json,
                    "headers": {k: v for k, v in response.headers.items()}
                }, ttl=self.ttl)
                
                # Create new response with body
                if isinstance(body_json, dict):
                    cached_response = JSONResponse(
                        content=body_json,
                        status_code=response.status_code,
                        headers={k: v for k, v in response.headers.items()}
                    )
                else:
                    from starlette.responses import Response
                    cached_response = Response(
                        content=body_json,
                        status_code=response.status_code,
                        headers={k: v for k, v in response.headers.items()},
                        media_type=response.media_type or "application/json"
                    )
                
                # Add idempotency headers
                cached_response.headers[IDEMPOTENCY_KEY_HEADER] = idempotency_key
                cached_response.headers["X-Idempotency-Cached"] = "false"
                
                return cached_response
            except Exception as e:
                logger.error(f"Error caching idempotency response: {e}", exc_info=True)
                # Return original response if caching fails
                response.headers[IDEMPOTENCY_KEY_HEADER] = idempotency_key
                return response
        else:
            # Don't cache error responses, but add header
            response.headers[IDEMPOTENCY_KEY_HEADER] = idempotency_key
            return response
    
    def _generate_cache_key(self, idempotency_key: str, method: str, path: str) -> str:
        """Generate cache key from idempotency key, method, and path."""
        # Include method and path to ensure different endpoints don't collide
        key_string = f"{method}:{path}:{idempotency_key}"
        # Hash to ensure consistent length
        return hashlib.sha256(key_string.encode()).hexdigest()

