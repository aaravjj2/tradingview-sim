"""
Redis Caching Layer
High-performance caching for option chains and Greeks calculations
"""

import json
import hashlib
from typing import Optional, Any, Dict
from datetime import datetime, timedelta
from functools import wraps
import asyncio


# In-memory cache fallback when Redis is not available
_memory_cache: Dict[str, Dict] = {}


class CacheConfig:
    """Cache configuration constants"""
    PRICE_TTL = 5  # seconds - prices change rapidly
    CANDLE_TTL = 60  # seconds
    CHAIN_TTL = 30  # seconds - option chain
    GREEKS_TTL = 10  # seconds
    GEX_TTL = 60  # seconds - gamma exposure
    IV_TTL = 30  # seconds


class RedisCache:
    """
    Redis-like cache interface with in-memory fallback
    
    In production, replace with actual Redis using:
    - redis-py for sync operations
    - aioredis for async operations
    """
    
    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0):
        self.host = host
        self.port = port
        self.db = db
        self.connected = False
        self.redis_client = None
        
        # Try to connect to Redis (optional)
        self._try_connect()
    
    def _try_connect(self):
        """Attempt to connect to Redis, fallback to memory cache if unavailable"""
        try:
            # In production, uncomment:
            # import redis
            # self.redis_client = redis.Redis(host=self.host, port=self.port, db=self.db)
            # self.redis_client.ping()
            # self.connected = True
            pass
        except Exception as e:
            print(f"Redis not available, using in-memory cache: {e}")
            self.connected = False
    
    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate a cache key from prefix and arguments"""
        key_parts = [prefix] + [str(a) for a in args]
        if kwargs:
            key_parts.append(hashlib.md5(json.dumps(kwargs, sort_keys=True).encode()).hexdigest()[:8])
        return ":".join(key_parts)
    
    async def get(self, key: str) -> Optional[str]:
        """Get value from cache"""
        if self.connected and self.redis_client:
            return self.redis_client.get(key)
        
        # Memory cache fallback
        entry = _memory_cache.get(key)
        if entry:
            if datetime.now() < entry["expires"]:
                return entry["value"]
            else:
                del _memory_cache[key]
        return None
    
    async def set(self, key: str, value: Any, ttl: int = 60) -> bool:
        """Set value in cache with TTL (seconds)"""
        if self.connected and self.redis_client:
            return self.redis_client.setex(key, ttl, json.dumps(value))
        
        # Memory cache fallback
        _memory_cache[key] = {
            "value": json.dumps(value),
            "expires": datetime.now() + timedelta(seconds=ttl)
        }
        return True
    
    async def get_json(self, key: str) -> Optional[Dict]:
        """Get and parse JSON value from cache"""
        value = await self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return None
        return None
    
    async def delete(self, key: str) -> bool:
        """Delete a key from cache"""
        if self.connected and self.redis_client:
            return self.redis_client.delete(key) > 0
        
        if key in _memory_cache:
            del _memory_cache[key]
            return True
        return False
    
    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching a pattern"""
        count = 0
        
        if self.connected and self.redis_client:
            keys = self.redis_client.keys(pattern)
            if keys:
                count = self.redis_client.delete(*keys)
        else:
            # Memory cache - simple pattern matching
            keys_to_delete = [k for k in _memory_cache.keys() if pattern.replace("*", "") in k]
            for key in keys_to_delete:
                del _memory_cache[key]
                count += 1
        
        return count
    
    def get_stats(self) -> Dict:
        """Get cache statistics"""
        if self.connected and self.redis_client:
            info = self.redis_client.info()
            return {
                "type": "redis",
                "connected": True,
                "used_memory": info.get("used_memory_human", "unknown"),
                "keys": self.redis_client.dbsize()
            }
        
        # Memory cache stats
        total_size = sum(len(v.get("value", "")) for v in _memory_cache.values())
        return {
            "type": "memory",
            "connected": False,
            "entries": len(_memory_cache),
            "estimated_size_bytes": total_size
        }


# Global cache instance
cache = RedisCache()


def cached(prefix: str, ttl: int = 60):
    """
    Decorator for caching function results
    
    Usage:
        @cached("price", ttl=5)
        async def get_price(ticker: str):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            key = cache._generate_key(prefix, *args, **kwargs)
            
            # Try to get from cache
            cached_result = await cache.get_json(key)
            if cached_result is not None:
                return cached_result
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Store in cache
            if result is not None:
                await cache.set(key, result, ttl)
            
            return result
        
        return wrapper
    return decorator


# Cached versions of common operations
@cached("price", ttl=CacheConfig.PRICE_TTL)
async def cached_get_price(ticker: str, fetch_func) -> Optional[Dict]:
    """Get price with caching"""
    return await fetch_func(ticker)


@cached("candles", ttl=CacheConfig.CANDLE_TTL)
async def cached_get_candles(ticker: str, limit: int, fetch_func) -> Optional[list]:
    """Get candles with caching"""
    return await fetch_func(ticker, limit)


@cached("chain", ttl=CacheConfig.CHAIN_TTL)
async def cached_get_chain(ticker: str, fetch_func) -> Optional[Dict]:
    """Get options chain with caching"""
    return await fetch_func(ticker)


@cached("greeks", ttl=CacheConfig.GREEKS_TTL)
async def cached_get_greeks(ticker: str, strike: float, expiry: str, fetch_func) -> Optional[Dict]:
    """Get Greeks with caching"""
    return await fetch_func(ticker, strike, expiry)


async def get_cache_stats() -> Dict:
    """Get cache statistics"""
    return cache.get_stats()


async def clear_ticker_cache(ticker: str) -> int:
    """Clear all cache entries for a specific ticker"""
    patterns = [
        f"price:{ticker}*",
        f"candles:{ticker}*",
        f"chain:{ticker}*",
        f"greeks:{ticker}*",
        f"gex:{ticker}*"
    ]
    
    total_cleared = 0
    for pattern in patterns:
        total_cleared += await cache.clear_pattern(pattern)
    
    return total_cleared


async def clear_all_cache() -> int:
    """Clear entire cache"""
    return await cache.clear_pattern("*")
