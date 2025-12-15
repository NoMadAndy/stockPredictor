"""
Simple in-memory cache with TTL for market data.

Used to reduce API calls for intraday data requests.
"""
from typing import Any, Optional
from datetime import datetime, timedelta
import threading


class CacheEntry:
    """Single cache entry with expiration."""
    
    def __init__(self, value: Any, ttl_seconds: int):
        self.value = value
        # Use UTC for consistent timezone-independent behavior
        self.expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)
    
    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at


class SimpleCache:
    """Thread-safe in-memory cache with TTL."""
    
    def __init__(self, default_ttl: int = 60):
        """
        Initialize cache.
        
        Args:
            default_ttl: Default time-to-live in seconds (default: 60s for intraday)
        """
        self._cache = {}
        self._lock = threading.Lock()
        self.default_ttl = default_ttl
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache if it exists and hasn't expired.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found or expired
        """
        with self._lock:
            if key not in self._cache:
                return None
            
            entry = self._cache[key]
            if entry.is_expired():
                del self._cache[key]
                return None
            
            return entry.value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        Set a value in the cache with TTL.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default_ttl if None)
        """
        if ttl is None:
            ttl = self.default_ttl
        
        with self._lock:
            self._cache[key] = CacheEntry(value, ttl)
    
    def clear(self):
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
    
    def cleanup_expired(self):
        """Remove all expired entries (for maintenance)."""
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired()
            ]
            for key in expired_keys:
                del self._cache[key]
    
    def __len__(self) -> int:
        """Return number of cached items (including expired)."""
        return len(self._cache)


# Global cache instance for market data
# TTL of 60 seconds is reasonable for intraday data
# (balances freshness with rate limit reduction)
market_data_cache = SimpleCache(default_ttl=60)


def get_cache_key(provider: str, symbol: str, start: str, end: str, interval: str) -> str:
    """
    Generate a unique cache key for market data requests.
    
    Args:
        provider: Provider name
        symbol: Stock symbol
        start: Start date
        end: End date
        interval: Data interval
        
    Returns:
        Unique cache key string
    """
    return f"{provider}:{symbol}:{start}:{end}:{interval}"
