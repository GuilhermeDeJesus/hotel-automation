"""
Redis implementation of CacheRepository.

Connects to a hosted Redis instance (e.g., Redis Cloud) and provides
cache operations for conversation history and temporary data.
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
        self.host = host or os.getenv("REDIS_HOST", "redis-10759.c11.us-east-1-3.ec2.cloud.redislabs.com")
        self.port = port or int(os.getenv("REDIS_PORT", 10759))
        self.username = username or os.getenv("REDIS_USERNAME", "default")
        self.password = password or os.getenv("REDIS_PASSWORD", "REDIS_PASSWORD")
        
        try:
            self.client = redis.Redis(
                host=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                decode_responses=decode_responses
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
        
        
#### Eu vou usar o Redis hospedado mesmo, então me ajuda a configurar a conexão com o Redis hospedado no meu projeto ?
# Para configurar a conexão com o Redis hospedado no seu projeto, você precisará seguir os seguintes passos:
# 1. Crie uma conta em um serviço de Redis hospedado, como o Redis Cloud ou Heroku Redis, e configure uma instância de Redis, anotando as credenciais de acesso (host, porta, senha).
# 2. No seu projeto, modifique a classe `RedisConversationRepository` no arquivo `redis_repository.py` para aceitar as credenciais de conexão do Redis hospedado:
# class RedisConversationRepository(ConversationCacheRepository):   
#     def __init__(self, host='seu_host_redis', port=6379, password='sua_senha_redis', db=0):
#         self.client = redis.Redis(host=host, port=port, password=password, db=db)
# 3. Substitua os valores padrão de `host`, `port` e `password` pelos valores fornecidos pelo serviço de Redis hospedado.
# 4. Certifique-se de que a instância do Redis hospedado esteja acessível a partir do ambiente onde seu projeto está rodando, e teste a conexão para garantir que tudo esteja configurado corretamente.


#### o db fica zerado ?
# O parâmetro `db` na configuração do Redis é usado para especificar qual banco de dados dentro do Redis você deseja usar. O Redis suporta múltiplos bancos de dados, numerados de 0 a 15 por padrão. Se você definir `db=0`, isso significa que você estará usando o banco de dados número 0, que é o banco de dados padrão. Se você quiser usar um banco de dados diferente, basta alterar o valor do `db` para o número correspondente ao banco de dados que deseja utilizar.

#### Lá no Redis o nome do meu banco é database-MLQRKK6L
# Se o nome do seu banco de dados no Redis é `database-MLQRKK6L`, isso significa que você está usando um serviço de Redis hospedado que pode ter uma configuração diferente dos bancos de dados tradicionais do Redis.
# Nesse caso, você deve verificar a documentação do serviço de Redis que está utilizando para entender como configurar a conexão corretamente, pois pode ser necessário usar um endpoint específico ou fornecer credenciais adicionais para acessar esse banco de dados específico. Certifique-se de seguir as instruções fornecidas pelo serviço de Redis para garantir que sua aplicação possa se conectar ao banco de dados `database-MLQRKK6L` corretamente.