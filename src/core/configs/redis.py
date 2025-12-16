"""
Redis Manager with Singleton pattern and connection pooling.

Type-safe implementation with full mypy strict mode support.
"""
from __future__ import annotations
import json
import logging
from contextlib import asynccontextmanager
from threading import Lock
from typing import Any, AsyncGenerator, Optional, Union, cast, Awaitable, List, Dict, Set, Tuple

from redis.asyncio import ConnectionPool, Redis
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import RedisError

from src.core.configs import settings, Environment

logger = logging.getLogger(__name__)


class SingletonMeta(type):
    """Thread-safe Singleton metaclass."""
    
    _instances: dict[type, Any] = {}
    _lock: Lock = Lock()

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        if cls not in cls._instances:
            with cls._lock:
                if cls not in cls._instances:
                    instance = super().__call__(*args, **kwargs)
                    cls._instances[cls] = instance
        return cls._instances[cls]


class RedisManager(metaclass=SingletonMeta):
    """
    Singleton Redis Manager with connection pooling.
    
    Features:
    - Connection pooling for performance
    - Auto JSON serialization/deserialization
    - Health check
    - Key prefix support
    - Type-safe operations
    
    Usage:
        await redis_manager.init()
        await redis_manager.set("key", "value", ttl=3600)
        value = await redis_manager.get("key")
        await redis_manager.close()
    """
    
    def __init__(self) -> None:
        self._pool: Optional[ConnectionPool] = None
        self._client: Optional[Redis] = None
        self._initialized: bool = False
        self._key_prefix: str = f"{settings.APP_NAME.lower()}:"
    
    async def init(self) -> None:
        """
        Initialize Redis connection pool.
        Should be called once in app lifespan startup.
        """
        if self._initialized:
            logger.warning("Redis already initialized - skipping")
            return
        
        try:
            # Build Redis URL
            redis_url = self._build_redis_url()
            
            # Create connection pool
            self._pool = ConnectionPool.from_url(
                redis_url,
                max_connections=settings.REDIS_MAX_CONNECTIONS,
                decode_responses=settings.REDIS_DECODE_RESPONSES,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30,
            )
            
            # Create Redis client
            self._client = Redis(connection_pool=self._pool)
            
            # Verify connection
            await cast(Awaitable[bool], self._client.ping())
            
            self._initialized = True
            
            logger.info(
                "Redis initialized: %s:%s (db=%s, max_connections=%s, key_prefix=%s)",
                settings.REDIS_HOST,
                settings.REDIS_PORT,
                settings.REDIS_DB,
                settings.REDIS_MAX_CONNECTIONS,
                self._key_prefix,
            )
            
        except RedisConnectionError as e:
            logger.error("Failed to connect to Redis: %s", e)
            raise RuntimeError("Redis connection failed") from e
        except Exception as e:
            logger.error("Redis initialization error: %s", e)
            raise
    
    def _build_redis_url(self) -> str:
        """Build Redis connection URL from settings."""
        if settings.REDIS_PASSWORD:
            return (
                f"redis://:{settings.REDIS_PASSWORD}@"
                f"{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
            )
        return f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
    
    async def close(self) -> None:
        """
        Close Redis connections.
        Should be called once in app lifespan shutdown.
        """
        if not self._initialized:
            logger.warning("Redis not initialized - nothing to close")
            return
        
        try:
            if self._client:
                await self._client.close()
                logger.info("Redis client closed")
            
            if self._pool:
                await self._pool.disconnect()
                logger.info("Redis connection pool closed")
            
            self._initialized = False
            
        except Exception as e:
            logger.error("Error closing Redis: %s", e)
    
    def _prefixed_key(self, key: str) -> str:
        """Add prefix to key if not already prefixed."""
        if key.startswith(self._key_prefix):
            return key
        return f"{self._key_prefix}{key}"
    
    def _ensure_client(self) -> Redis:
        """Ensure Redis is initialized and return client."""
        if not self._initialized or not self._client:
            raise RuntimeError(
                "Redis not initialized. Call await redis_manager.init() first."
            )
        return self._client
    
    # ==================== BASIC OPERATIONS ====================
    
    async def get(self, key: str) -> Optional[str]:
        """
        Get value by key.
        
        Returns:
            Value as string or None if not exists
        """
        client = self._ensure_client()
        try:
            key = self._prefixed_key(key)
            value = await cast(Awaitable[Optional[str]], client.get(key))
            if settings.REDIS_DECODE_RESPONSES:
                return value  # type: ignore
            return value.decode() if isinstance(value, (bytes, bytearray)) else value if value else None
        except RedisError as e:
            logger.error("Redis GET error for key '%s': %s", key, e)
            return None
    
    async def set(
        self,
        key: str,
        value: Union[str, int, float],
        ttl: Optional[int] = None,
        nx: bool = False,
        xx: bool = False,
    ) -> bool:
        """
        Set key-value.
        
        Args:
            key: Redis key
            value: Value to set
            ttl: Time to live in seconds
            nx: Only set if key does NOT exist
            xx: Only set if key DOES exist
        
        Returns:
            True if successful
        """
        client = self._ensure_client()
        try:
            key = self._prefixed_key(key)
            result = await cast(Awaitable[bool], client.set(key, value, ex=ttl, nx=nx, xx=xx))
            return bool(result)
        except RedisError as e:
            logger.error("Redis SET error for key '%s': %s", key, e)
            return False
    
    async def delete(self, *keys: str) -> int:
        """
        Delete one or more keys.
        
        Returns:
            Number of keys deleted
        """
        client = self._ensure_client()
        try:
            prefixed_keys = [self._prefixed_key(k) for k in keys]
            return await cast(Awaitable[int], client.delete(*prefixed_keys))
        except RedisError as e:
            logger.error("Redis DELETE error: %s", e)
            return 0
    
    async def exists(self, *keys: str) -> int:
        """
        Check if keys exist.
        
        Returns:
            Number of existing keys
        """
        client = self._ensure_client()
        try:
            prefixed_keys = [self._prefixed_key(k) for k in keys]
            return await cast(Awaitable[int], client.exists(*prefixed_keys))
        except RedisError as e:
            logger.error("Redis EXISTS error: %s", e)
            return 0
    
    async def expire(self, key: str, seconds: int) -> bool:
        """Set key expiration time."""
        client = self._ensure_client()
        try:
            key = self._prefixed_key(key)
            return await cast(Awaitable[bool], client.expire(key, seconds))
        except RedisError as e:
            logger.error("Redis EXPIRE error for key '%s': %s", key, e)
            return False
    
    async def ttl(self, key: str) -> int:
        """
        Get remaining time to live.
        
        Returns:
            -2: key does not exist
            -1: key exists but has no expiration
            >0: remaining seconds
        """
        client = self._ensure_client()
        try:
            key = self._prefixed_key(key)
            return await cast(Awaitable[int], client.ttl(key))
        except RedisError as e:
            logger.error("Redis TTL error for key '%s': %s", key, e)
            return -2
    
    # ==================== JSON OPERATIONS ====================
    
    async def get_json(self, key: str) -> Optional[Any]:
        """
        Get JSON value and deserialize.
        
        Returns:
            Deserialized Python object or None
        """
        value = await self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError as e:
                logger.error("JSON decode error for key '%s': %s", key, e)
        return None
    
    async def set_json(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """Serialize and set JSON value."""
        try:
            json_str = json.dumps(value, ensure_ascii=False)
            return await self.set(key, json_str, ttl=ttl)
        except (TypeError, ValueError) as e:
            logger.error("JSON encode error for key '%s': %s", key, e)
            return False
    
    # ==================== COUNTER OPERATIONS ====================
    
    async def incr(self, key: str, amount: int = 1) -> int:
        """
        Increment counter.
        
        Returns:
            New value after increment
        """
        client = self._ensure_client()
        try:
            key = self._prefixed_key(key)
            return await cast(Awaitable[int], client.incrby(key, amount))
        except RedisError as e:
            logger.error("Redis INCR error for key '%s': %s", key, e)
            return 0
    
    async def decr(self, key: str, amount: int = 1) -> int:
        """Decrement counter."""
        client = self._ensure_client()
        try:
            key = self._prefixed_key(key)
            return await cast(Awaitable[int], client.decrby(key, amount))
        except RedisError as e:
            logger.error("Redis DECR error for key '%s': %s", key, e)
            return 0
    
    # ==================== HASH OPERATIONS ====================
    
    async def hset(self, name: str, key: str, value: str) -> int:
        """Set hash field."""
        client = self._ensure_client()
        try:
            name = self._prefixed_key(name)
            return await cast(Awaitable[int], client.hset(name, key, value))
        except RedisError as e:
            logger.error("Redis HSET error: %s", e)
            return 0
    
    async def hget(self, name: str, key: str) -> Optional[str]:
        """Get hash field."""
        client = self._ensure_client()
        try:
            name = self._prefixed_key(name)
            value = await cast(Awaitable[Optional[str]], client.hget(name, key))
            if settings.REDIS_DECODE_RESPONSES:
                return value  # type: ignore
            return value.decode() if isinstance(value, (bytes, bytearray)) else value if value else None
        except RedisError as e:
            logger.error("Redis HGET error: %s", e)
            return None
    
    async def hgetall(self, name: str) -> Dict[str, str]:
        """Get all hash fields."""
        client = self._ensure_client()
        try:
            name = self._prefixed_key(name)
            data = await cast(Awaitable[dict[Any, Any]], client.hgetall(name))
            if settings.REDIS_DECODE_RESPONSES:
                return data  # type: ignore
            return {
                (k.decode() if isinstance(k, (bytes, bytearray)) else k):
                (v.decode() if isinstance(v, (bytes, bytearray)) else v)
                for k, v in data.items()
            }
        except RedisError as e:
            logger.error("Redis HGETALL error: %s", e)
            return {}
    
    async def hdel(self, name: str, *keys: str) -> int:
        """Delete hash fields."""
        client = self._ensure_client()
        try:
            name = self._prefixed_key(name)
            return await cast(Awaitable[int], client.hdel(name, *keys))
        except RedisError as e:
            logger.error("Redis HDEL error: %s", e)
            return 0
    
    # ==================== LIST OPERATIONS ====================
    
    async def lpush(self, key: str, *values: str) -> int:
        """Push values to list head."""
        client = self._ensure_client()
        try:
            key = self._prefixed_key(key)
            return await cast(Awaitable[int], client.lpush(key, *values))
        except RedisError as e:
            logger.error("Redis LPUSH error: %s", e)
            return 0
    
    async def rpush(self, key: str, *values: str) -> int:
        """Push values to list tail."""
        client = self._ensure_client()
        try:
            key = self._prefixed_key(key)
            return await cast(Awaitable[int], client.rpush(key, *values))
        except RedisError as e:
            logger.error("Redis RPUSH error: %s", e)
            return 0
    
    async def lpop(self, key: str) -> Optional[str]:
        """Pop value from list head."""
        client = self._ensure_client()
        try:
            key = self._prefixed_key(key)
            value = await cast(Awaitable[Optional[str]], client.lpop(key))
            if settings.REDIS_DECODE_RESPONSES:
                return value  # type: ignore
            return value.decode() if isinstance(value, (bytes, bytearray)) else value if value else None
        except RedisError as e:
            logger.error("Redis LPOP error: %s", e)
            return None
    
    async def rpop(self, key: str) -> Optional[str]:
        """Pop value from list tail."""
        client = self._ensure_client()
        try:
            key = self._prefixed_key(key)
            value = await cast(Awaitable[Optional[str]], client.rpop(key))
            if settings.REDIS_DECODE_RESPONSES:
                return value  # type: ignore
            return value.decode() if isinstance(value, (bytes, bytearray)) else value if value else None
        except RedisError as e:
            logger.error("Redis RPOP error: %s", e)
            return None
    
    async def lrange(self, key: str, start: int, end: int) -> List[str]:
        """Get list range."""
        client = self._ensure_client()
        try:
            key = self._prefixed_key(key)
            values = await cast(Awaitable[list[Any]], client.lrange(key, start, end))
            if settings.REDIS_DECODE_RESPONSES:
                return values  # type: ignore
            return [v.decode() if isinstance(v, (bytes, bytearray)) else v for v in values]
        except RedisError as e:
            logger.error("Redis LRANGE error: %s", e)
            return []
    
    async def llen(self, key: str) -> int:
        """Get list length."""
        client = self._ensure_client()
        try:
            key = self._prefixed_key(key)
            return await cast(Awaitable[int], client.llen(key))
        except RedisError as e:
            logger.error("Redis LLEN error: %s", e)
            return 0
    
    # ==================== SET OPERATIONS ====================
    
    async def sadd(self, key: str, *values: str) -> int:
        """Add members to set."""
        client = self._ensure_client()
        try:
            key = self._prefixed_key(key)
            return await cast(Awaitable[int], client.sadd(key, *values))
        except RedisError as e:
            logger.error("Redis SADD error: %s", e)
            return 0
    
    async def srem(self, key: str, *values: str) -> int:
        """Remove members from set."""
        client = self._ensure_client()
        try:
            key = self._prefixed_key(key)
            return await cast(Awaitable[int], client.srem(key, *values))
        except RedisError as e:
            logger.error("Redis SREM error: %s", e)
            return 0
    
    async def smembers(self, key: str) -> Set[str]:
        """Get all set members."""
        client = self._ensure_client()
        try:
            key = self._prefixed_key(key)
            values = await cast(Awaitable[set[Any]], client.smembers(key))
            if settings.REDIS_DECODE_RESPONSES:
                return values  # type: ignore
            return {v.decode() if isinstance(v, (bytes, bytearray)) else v for v in values}
        except RedisError as e:
            logger.error("Redis SMEMBERS error: %s", e)
            return set()
    
    async def sismember(self, key: str, value: str) -> bool:
        """Check if member exists in set."""
        client = self._ensure_client()
        try:
            key = self._prefixed_key(key)
            return await cast(Awaitable[bool], client.sismember(key, value))
        except RedisError as e:
            logger.error("Redis SISMEMBER error: %s", e)
            return False
    
    # ==================== SORTED SET OPERATIONS ====================
    
    async def zadd(self, key: str, mapping: dict[str, float]) -> int:
        """Add members to sorted set with scores."""
        client = self._ensure_client()
        try:
            key = self._prefixed_key(key)
            # Ensure mapping values are float (or str/int/bytes if needed)
            safe_mapping: dict[str, float] = {k: float(v) for k, v in mapping.items()}
            return await cast(Awaitable[int], client.zadd(key, safe_mapping))  # type: ignore[arg-type]
        except RedisError as e:
            logger.error("Redis ZADD error: %s", e)
            return 0
    
    async def zrange(
        self,
        key: str,
        start: int,
        end: int,
        desc: bool = False,
        withscores: bool = False,
    ) -> List[Union[str, Tuple[str, float]]]:
        """Get sorted set range."""
        client = self._ensure_client()
        try:
            key = self._prefixed_key(key)
            values = await cast(Awaitable[list[Any]], client.zrange(key, start, end, desc=desc, withscores=withscores))
            if settings.REDIS_DECODE_RESPONSES:
                return values  # type: ignore
            if withscores:
                return [((v.decode() if isinstance(v, (bytes, bytearray)) else v), s) for v, s in values]  # type: ignore
            return [v.decode() if isinstance(v, (bytes, bytearray)) else v for v in values]  # type: ignore
        except RedisError as e:
            logger.error("Redis ZRANGE error: %s", e)
            return []
    
    async def zrem(self, key: str, *values: str) -> int:
        """Remove members from sorted set."""
        client = self._ensure_client()
        try:
            key = self._prefixed_key(key)
            return await cast(Awaitable[int], client.zrem(key, *values))
        except RedisError as e:
            logger.error("Redis ZREM error: %s", e)
            return 0
    
    # ==================== UTILITY OPERATIONS ====================
    
    async def keys(self, pattern: str = "*") -> list[str]:
        """Get keys matching pattern. Use SCAN in production."""
        client = self._ensure_client()
        try:
            pattern = self._prefixed_key(pattern)
            keys = await cast(Awaitable[list[Any]], client.keys(pattern))
            prefix_len = len(self._key_prefix)
            if settings.REDIS_DECODE_RESPONSES:
                return [k[prefix_len:] for k in keys]  # type: ignore
            return [(k.decode()[prefix_len:] if isinstance(k, (bytes, bytearray)) else k[prefix_len:]) for k in keys]
        except RedisError as e:
            logger.error("Redis KEYS error: %s", e)
            return []
    
    async def flushdb(self) -> bool:
        """Delete all keys. Only for development."""
        if settings.APP_ENV == Environment.PRODUCTION:
            logger.error("FLUSHDB is disabled in production!")
            return False
        
        client = self._ensure_client()
        try:
            await cast(Awaitable[Any], client.flushdb())
            logger.warning("Redis database flushed!")
            return True
        except RedisError as e:
            logger.error("Redis FLUSHDB error: %s", e)
            return False
    
    async def ping(self) -> bool:
        """Check if Redis is responsive."""
        client = self._ensure_client()
        try:
            return await cast(Awaitable[bool], client.ping())
        except RedisError:
            return False
    
    async def info(self, section: Optional[str] = None) -> dict[str, Any]:
        """Get Redis server info."""
        client = self._ensure_client()
        try:
            return await cast(Awaitable[dict[str, Any]], client.info(section))  # type: ignore
        except RedisError as e:
            logger.error("Redis INFO error: %s", e)
            return {}
    
    # ==================== PUB/SUB ====================
    
    @asynccontextmanager
    async def pubsub(self) -> AsyncGenerator[Any, None]:
        """Get pub/sub connection."""
        client = self._ensure_client()
        pubsub = client.pubsub()
        try:
            yield pubsub
        finally:
            await pubsub.close()
    
    async def publish(self, channel: str, message: str) -> int:
        """Publish message to channel."""
        client = self._ensure_client()
        try:
            channel = self._prefixed_key(channel)
            return await cast(Awaitable[int], client.publish(channel, message))
        except RedisError as e:
            logger.error("Redis PUBLISH error: %s", e)
            return 0
    
    # ==================== HEALTH CHECK ====================
    
    async def health_check(self) -> dict[str, Any]:
        """Health check for monitoring."""
        status: dict[str, Any] = {
            "status": "unknown",
            "ping": False,
            "info": {},
        }
        
        if not self._initialized:
            status["status"] = "not_initialized"
            return status
        
        try:
            status["ping"] = await self.ping()
            
            info = await self.info("server")
            status["info"] = {
                "redis_version": info.get("redis_version", "unknown"),
                "uptime_seconds": info.get("uptime_in_seconds", 0),
                "connected_clients": info.get("connected_clients", 0),
            }
            
            status["status"] = "healthy" if status["ping"] else "unhealthy"
            
        except Exception as e:
            status["status"] = "unhealthy"
            status["error"] = str(e)
        
        return status
    
    # ==================== PROPERTIES ====================
    
    @property
    def is_initialized(self) -> bool:
        """Check if Redis is initialized."""
        return self._initialized
    
    @property
    def client(self) -> Redis:
        """Get raw Redis client for advanced operations."""
        return self._ensure_client()


# Singleton instance
redis_manager = RedisManager()