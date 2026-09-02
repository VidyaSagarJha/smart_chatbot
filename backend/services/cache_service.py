"""
Simple query response caching service.
Uses Redis with in-memory fallback for demo/development.
"""

import json
import hashlib
from typing import Optional
from config.settings import settings
import logging

logger = logging.getLogger(__name__)

# Try to import Redis
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not installed. Using in-memory cache.")

# In-memory fallback cache
_memory_cache = {}
CACHE_VERSION = "v3"


class QueryCache:
    """Simple caching for query responses."""
    
    def __init__(self):
        self.redis_client = None
        self.use_redis = False
        
        if REDIS_AVAILABLE and settings.REDIS_ENABLED:
            try:
                self.redis_client = redis.from_url(
                    settings.REDIS_URL,
                    decode_responses=True,
                    socket_connect_timeout=5
                )
                # Test connection
                self.redis_client.ping()
                self.use_redis = True
                logger.info("✅ Redis cache connected")
            except Exception as e:
                logger.warning(f"⚠️ Redis connection failed: {e}. Using in-memory cache.")
                self.use_redis = False
    
    def _make_key(self, query: str, doc_id: str, context: str = "") -> str:
        """Generate a key that distinguishes identical queries by conversation."""
        # Bump CACHE_VERSION whenever answer-generation behavior changes so a
        # stale response is not served after retrieval or prompt improvements.
        data = f"{CACHE_VERSION}:{query}:{doc_id}:{context}"
        return "query:" + hashlib.md5(data.encode()).hexdigest()
    
    def get(self, query: str, doc_id: str, context: str = "") -> Optional[str]:
        """Get cached response."""
        key = self._make_key(query, doc_id, context)
        try:
            if self.use_redis:
                cached = self.redis_client.get(key)
                if cached:
                    logger.info(f"✅ Cache HIT for query: {query[:50]}...")
                    return cached
            else:
                if key in _memory_cache:
                    logger.info(f"✅ Cache HIT for query: {query[:50]}...")
                    return _memory_cache[key]
        except Exception as e:
            logger.error(f"Cache get error: {e}")
        
        return None
    
    def set(self, query: str, doc_id: str, response: str, context: str = "") -> None:
        """Cache response."""
        key = self._make_key(query, doc_id, context)
        try:
            if self.use_redis:
                self.redis_client.setex(key, settings.CACHE_TTL_QUERIES, response)
            else:
                _memory_cache[key] = response
            logger.info(f"✅ Cached response for query: {query[:50]}...")
        except Exception as e:
            logger.error(f"Cache set error: {e}")
    
    def clear(self) -> None:
        """Clear all cache."""
        try:
            if self.use_redis:
                self.redis_client.flushdb()
            else:
                _memory_cache.clear()
            logger.info("✅ Cache cleared")
        except Exception as e:
            logger.error(f"Cache clear error: {e}")


# Singleton instance
_cache = None


def get_query_cache() -> QueryCache:
    """Get cache instance."""
    global _cache
    if _cache is None:
        _cache = QueryCache()
    return _cache


def cache_query_response(query: str, doc_id: str, context: str = "") -> Optional[str]:
    """Try to get cached response."""
    return get_query_cache().get(query, doc_id, context)


def set_query_cache(query: str, doc_id: str, response: str, context: str = "") -> None:
    """Cache query response."""
    get_query_cache().set(query, doc_id, response, context)
