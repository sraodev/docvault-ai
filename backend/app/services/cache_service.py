"""
Cache Service - Redis-based caching for high-performance operations.

This service provides distributed caching for:
- Document metadata
- Search results
- Tag lists
- Frequently accessed data

Designed for million+ user scale with Redis cluster support.
"""
import json
from typing import Optional, Any, List, Dict
from datetime import timedelta
import aioredis
from ..core.config import REDIS_URL, REDIS_HOST, REDIS_PORT, REDIS_PASSWORD, REDIS_DB


class CacheService:
    """
    Redis-based cache service for high-performance operations.
    
    Provides distributed caching across multiple application instances,
    essential for scaling to millions of users.
    """
    
    def __init__(self):
        """Initialize cache service."""
        self._redis: Optional[aioredis.Redis] = None
        self._redis_url = REDIS_URL
        self._redis_host = REDIS_HOST or "localhost"
        self._redis_port = REDIS_PORT or 6379
        self._redis_password = REDIS_PASSWORD
        self._redis_db = REDIS_DB or 0
    
    async def connect(self):
        """Connect to Redis."""
        if self._redis is None:
            if self._redis_url:
                self._redis = await aioredis.from_url(
                    self._redis_url,
                    encoding="utf-8",
                    decode_responses=True
                )
            else:
                self._redis = await aioredis.Redis(
                    host=self._redis_host,
                    port=self._redis_port,
                    password=self._redis_password,
                    db=self._redis_db,
                    encoding="utf-8",
                    decode_responses=True
                )
    
    async def disconnect(self):
        """Disconnect from Redis."""
        if self._redis:
            await self._redis.close()
            self._redis = None
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        await self.connect()
        try:
            value = await self._redis.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            print(f"Cache get error for key '{key}': {e}")
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache (must be JSON serializable)
            ttl: Time to live in seconds (default: 1 hour)
            
        Returns:
            True if successful
        """
        await self.connect()
        try:
            if ttl is None:
                ttl = 3600  # Default 1 hour
            
            serialized = json.dumps(value)
            await self._redis.setex(key, ttl, serialized)
            return True
        except Exception as e:
            print(f"Cache set error for key '{key}': {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        await self.connect()
        try:
            await self._redis.delete(key)
            return True
        except Exception as e:
            print(f"Cache delete error for key '{key}': {e}")
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching pattern.
        
        Args:
            pattern: Redis pattern (e.g., "doc:*")
            
        Returns:
            Number of keys deleted
        """
        await self.connect()
        try:
            keys = []
            async for key in self._redis.scan_iter(match=pattern):
                keys.append(key)
            
            if keys:
                return await self._redis.delete(*keys)
            return 0
        except Exception as e:
            print(f"Cache delete_pattern error for pattern '{pattern}': {e}")
            return 0
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        await self.connect()
        try:
            return await self._redis.exists(key) > 0
        except Exception as e:
            print(f"Cache exists error for key '{key}': {e}")
            return False
    
    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment counter in cache."""
        await self.connect()
        try:
            return await self._redis.incrby(key, amount)
        except Exception as e:
            print(f"Cache increment error for key '{key}': {e}")
            return 0
    
    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """
        Get multiple values from cache.
        
        Args:
            keys: List of cache keys
            
        Returns:
            Dictionary mapping keys to values (only includes found keys)
        """
        await self.connect()
        try:
            values = await self._redis.mget(keys)
            result = {}
            for key, value in zip(keys, values):
                if value:
                    result[key] = json.loads(value)
            return result
        except Exception as e:
            print(f"Cache get_many error: {e}")
            return {}
    
    async def set_many(
        self,
        mapping: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """
        Set multiple values in cache.
        
        Args:
            mapping: Dictionary of key-value pairs
            ttl: Time to live in seconds
            
        Returns:
            True if successful
        """
        await self.connect()
        try:
            if ttl is None:
                ttl = 3600
            
            pipe = self._redis.pipeline()
            for key, value in mapping.items():
                serialized = json.dumps(value)
                pipe.setex(key, ttl, serialized)
            await pipe.execute()
            return True
        except Exception as e:
            print(f"Cache set_many error: {e}")
            return False


# Global cache service instance
cache_service = CacheService()

