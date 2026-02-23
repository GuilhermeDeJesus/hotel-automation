"""
Cache Repository Interface - contract for any cache implementation.

This interface defines how the Application layer interacts with any caching system
(Redis, Memcached, in-memory, etc.) without knowing implementation details.
"""
from abc import ABC, abstractmethod
from typing import Any, Optional


class CacheRepository(ABC):
    """
    Interface for cache operations.
    
    Implementations can use Redis, Memcached, in-memory dict, etc.
    """
    
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve value from cache.
        
        Args:
            key: The cache key
            
        Returns:
            The cached value, or None if not found
        """
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any, ttl_seconds: int = 3600) -> None:
        """
        Store value in cache.
        
        Args:
            key: The cache key
            value: The value to cache (typically dict)
            ttl_seconds: Time to live in seconds (default 1 hour)
        """
        pass
    
    @abstractmethod
    def delete(self, key: str) -> None:
        """
        Delete value from cache.
        
        Args:
            key: The cache key to delete
        """
        pass
    
    @abstractmethod
    def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.
        
        Args:
            key: The cache key
            
        Returns:
            True if key exists, False otherwise
        """
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """Clear all cache entries."""
        pass
