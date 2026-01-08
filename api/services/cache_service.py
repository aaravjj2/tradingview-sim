"""
Redis Caching Layer
Provides caching for expensive operations like regime detection and OI calculations.
"""

import json
from typing import Optional, Dict, Any
from datetime import timedelta
import asyncio

try:
    import redis.asyncio as redis
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False
    print("⚠️ redis not installed. Caching disabled. Install with: pip install redis")


class CacheService:
    """
    Async Redis cache service for API responses.
    
    Caches:
    - Regime detection results (TTL: 60s)
    - Open Interest profiles (TTL: 120s)
    - Ensemble forecasts (TTL: 300s)
    - Market data (TTL: 30s)
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self._client: Optional[redis.Redis] = None
        self._enabled = HAS_REDIS
        
        # TTL settings (in seconds)
        self.ttl = {
            "regime": 60,        # 1 minute
            "oi": 120,           # 2 minutes
            "forecast": 300,     # 5 minutes
            "price": 30,         # 30 seconds
            "sentiment": 180,    # 3 minutes
        }
    
    async def connect(self):
        """Initialize Redis connection."""
        if not self._enabled:
            return
        
        try:
            self._client = await redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            await self._client.ping()
            print("[Cache] Connected to Redis")
        except Exception as e:
            print(f"[Cache] Redis connection failed: {e}. Caching disabled.")
            self._enabled = False
    
    async def disconnect(self):
        """Close Redis connection."""
        if self._client:
            await self._client.close()
    
    async def get(self, key: str) -> Optional[Dict]:
        """Get cached value."""
        if not self._enabled or not self._client:
            return None
        
        try:
            value = await self._client.get(key)
            if value:
                return json.loads(value)
        except Exception as e:
            print(f"[Cache] Get error for {key}: {e}")
        
        return None
    
    async def set(self, key: str, value: Dict, ttl: Optional[int] = None):
        """Set cached value with TTL."""
        if not self._enabled or not self._client:
            return
        
        try:
            await self._client.set(
                key,
                json.dumps(value),
                ex=ttl or 300  # Default 5 minutes
            )
        except Exception as e:
            print(f"[Cache] Set error for {key}: {e}")
    
    async def delete(self, key: str):
        """Delete cached value."""
        if not self._enabled or not self._client:
            return
        
        try:
            await self._client.delete(key)
        except Exception as e:
            print(f"[Cache] Delete error for {key}: {e}")
    
    async def clear_pattern(self, pattern: str):
        """Clear all keys matching pattern."""
        if not self._enabled or not self._client:
            return
        
        try:
            keys = await self._client.keys(pattern)
            if keys:
                await self._client.delete(*keys)
                print(f"[Cache] Cleared {len(keys)} keys matching {pattern}")
        except Exception as e:
            print(f"[Cache] Clear pattern error: {e}")
    
    def make_key(self, prefix: str, *args) -> str:
        """Generate cache key."""
        parts = [prefix] + [str(arg) for arg in args]
        return ":".join(parts)
    
    async def get_or_compute(
        self,
        key: str,
        compute_fn,
        ttl: Optional[int] = None,
        *args,
        **kwargs
    ) -> Any:
        """
        Get from cache or compute and cache result.
        
        Args:
            key: Cache key
            compute_fn: Async function to compute value if not cached
            ttl: Time to live in seconds
            *args, **kwargs: Arguments to pass to compute_fn
        
        Returns:
            Cached or computed value
        """
        # Try cache first
        cached = await self.get(key)
        if cached is not None:
            return cached
        
        # Compute value
        if asyncio.iscoroutinefunction(compute_fn):
            value = await compute_fn(*args, **kwargs)
        else:
            value = compute_fn(*args, **kwargs)
        
        # Cache result
        await self.set(key, value, ttl)
        
        return value


# Singleton
_cache: Optional[CacheService] = None

async def get_cache() -> CacheService:
    """Get or create cache service singleton."""
    global _cache
    if _cache is None:
        _cache = CacheService()
        await _cache.connect()
    return _cache


async def init_cache():
    """Initialize cache on startup."""
    cache = await get_cache()
    return cache
