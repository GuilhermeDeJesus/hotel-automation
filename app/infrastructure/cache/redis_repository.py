"""
Redis implementation of CacheRepository.

Connects to Redis and provides cache operations for conversation history
and temporary data.
"""
import os
import redis
import json
from typing import Any, Optional

from app.domain.repositories.cache_repository import CacheRepository
from app.application.exceptions import CacheError


class RedisRepository(CacheRepository):
    """
    Redis-based cache repository implementation.
    
    Reads connection details from environment variables:
    - REDIS_HOST
    - REDIS_PORT
    - REDIS_USERNAME
    - REDIS_PASSWORD
    """
    
    def __init__(
        self,
        host: str = None,
        port: int = None,
        username: str = None,
        password: str = None,
        decode_responses: bool = True
    ):
        """
        Initialize Redis connection.
        
        Args:
            host: Redis host (from REDIS_HOST env var if not provided)
            port: Redis port (from REDIS_PORT env var if not provided)
            username: Redis username (from REDIS_USERNAME env var if not provided)
            password: Redis password (from REDIS_PASSWORD env var if not provided)
            decode_responses: Whether to decode responses to strings
        """
        self.host = host or os.getenv("REDIS_HOST", "localhost")
        self.port = int(port or os.getenv("REDIS_PORT", 6379))
        self.username = username if username is not None else os.getenv("REDIS_USERNAME")
        self.password = password if password is not None else os.getenv("REDIS_PASSWORD")
        
        try:
            connection_kwargs = {
                "host": self.host,
                "port": self.port,
                "decode_responses": decode_responses,
            }

            if self.username:
                connection_kwargs["username"] = self.username
            if self.password:
                connection_kwargs["password"] = self.password

            self.client = redis.Redis(
                **connection_kwargs
            )
            # Test connection
            self.client.ping()
        except Exception as e:
            raise CacheError(f"Failed to connect to Redis: {str(e)}")
    
    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve value from cache.
        
        Args:
            key: The cache key
            
        Returns:
            Parsed JSON value, or None if not found
        """
        try:
            data = self.client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            raise CacheError(f"Failed to get key '{key}': {str(e)}")
    
    def set(self, key: str, value: Any, ttl_seconds: int = 3600) -> None:
        """
        Store value in cache.
        
        Args:
            key: The cache key
            value: The value to cache
            ttl_seconds: Time to live in seconds (default 1 hour)
        """
        try:
            self.client.set(key, json.dumps(value), ex=ttl_seconds)
        except Exception as e:
            raise CacheError(f"Failed to set key '{key}': {str(e)}")
    
    def delete(self, key: str) -> None:
        """
        Delete value from cache.
        
        Args:
            key: The cache key to delete
        """
        try:
            self.client.delete(key)
        except Exception as e:
            raise CacheError(f"Failed to delete key '{key}': {str(e)}")
    
    def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.
        
        Args:
            key: The cache key
            
        Returns:
            True if key exists, False otherwise
        """
        try:
            return self.client.exists(key) > 0
        except Exception as e:
            raise CacheError(f"Failed to check existence of key '{key}': {str(e)}")
    
    def clear(self) -> None:
        """Clear all cache entries."""
        try:
            self.client.flushdb()
        except Exception as e:
            raise CacheError(f"Failed to clear cache: {str(e)}")
