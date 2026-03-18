from app.domain.repositories.conversation_cache_repository import ConversationCacheRepository
"""
Redis implementation of CacheRepository.

Connects to Redis and provides cache operations for conversation history
and temporary data.
"""
import os
import redis
import json
from typing import Any, Optional, overload

from app.domain.repositories.cache_repository import CacheRepository
from app.application.exceptions import CacheError


class RedisRepository(CacheRepository, ConversationCacheRepository):
    """
    Redis-based cache repository implementation.
    
    Reads connection details from environment variables:
    - REDIS_HOST
    - REDIS_PORT
    - REDIS_USERNAME
    - REDIS_PASSWORD
    """
    
    def _conversation_key(self, hotel_id: str, phone: str) -> str:
        """Generate a unique cache key for a hotel's conversation with a phone."""
        return f"conversation:{hotel_id}:{phone}"
    
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
    
    @overload
    def get(self, key: str) -> Optional[Any]: ...

    @overload
    def get(self, hotel_id: str, phone: str) -> Optional[Any]: ...

    def get(self, key_or_hotel_id: str, phone: str | None = None) -> Optional[Any]:
        """
        Retrieve value from cache.
        
        Args:
            key_or_hotel_id: The cache key (CacheRepository) OR hotel_id (ConversationCacheRepository)
            phone: Optional phone to resolve conversation cache key
            
        Returns:
            Parsed JSON value, or None if not found
        """
        try:
            key = (
                self._conversation_key(key_or_hotel_id, phone)
                if phone is not None
                else key_or_hotel_id
            )
            data = self.client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            raise CacheError(f"Failed to get cache key '{key_or_hotel_id}': {str(e)}")
    
    @overload
    def set(self, key: str, value: Any, ttl_seconds: int = 3600) -> None: ...

    @overload
    def set(
        self, hotel_id: str, phone: str, data: Any, ttl_seconds: int = 3600
    ) -> None: ...

    def set(
        self,
        key_or_hotel_id: str,
        value_or_phone: Any,
        value: Any | None = None,
        ttl_seconds: int = 3600,
    ) -> None:
        """
        Store value in cache.
        
        Args:
            key_or_hotel_id: The cache key (CacheRepository) OR hotel_id (ConversationCacheRepository)
            value_or_phone: The value to cache (CacheRepository) OR phone (ConversationCacheRepository)
            value: The value to cache (only when using ConversationCacheRepository)
            ttl_seconds: Time to live in seconds (default 1 hour)
        """
        try:
            if value is None:
                key = key_or_hotel_id
                payload = value_or_phone
            else:
                key = self._conversation_key(key_or_hotel_id, str(value_or_phone))
                payload = value

            self.client.set(key, json.dumps(payload), ex=ttl_seconds)
        except Exception as e:
            raise CacheError(f"Failed to set cache key '{key_or_hotel_id}': {str(e)}")
    
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
