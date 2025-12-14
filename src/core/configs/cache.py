"""
Redis Cache Utilities - Type-safe implementation.

Provides caching decorators and helper functions with full mypy support.
"""
import asyncio
import functools
import hashlib
import json
import logging
from typing import Any, Callable, Optional, TypeVar, cast, Awaitable

from src.core.configs.redis import redis_manager

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def cache_key(*args: Any, **kwargs: Any) -> str:
    """Generate cache key from function arguments."""
    key_parts = [str(arg) for arg in args]
    key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
    return ":".join(key_parts)


def cache_key_hash(*args: Any, **kwargs: Any) -> str:
    """Generate hashed cache key for long keys."""
    data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True)
    hash_value = hashlib.md5(data.encode()).hexdigest()
    return f"hash:{hash_value}"


def cached(
    ttl: int = 3600,
    key_prefix: str = "cache",
    key_builder: Optional[Callable[..., str]] = None,
) -> Callable[[F], F]:
    """
    Cache decorator for async functions.
    
    Args:
        ttl: Time to live in seconds
        key_prefix: Prefix for cache key
        key_builder: Custom function to build cache key
    
    Usage:
        @cached(ttl=300, key_prefix="user")
        async def get_user(user_id: int) -> dict:
            return await db.query(...)
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Build cache key
            if key_builder:
                key = key_builder(*args, **kwargs)
            else:
                key = cache_key(func.__name__, *args, **kwargs)
            
            full_key = f"{key_prefix}:{key}"
            
            # Try to get from cache
            cached_value = await redis_manager.get_json(full_key)
            if cached_value is not None:
                logger.debug("Cache HIT: %s", full_key)
                return cached_value
            
            # Cache miss - execute function
            logger.debug("Cache MISS: %s", full_key)
            result = await func(*args, **kwargs)
            
            # Store in cache
            await redis_manager.set_json(full_key, result, ttl=ttl)
            
            return result
        
        return cast(F, wrapper)
    return decorator


def cache_invalidate(key_pattern: str) -> Callable[[F], F]:
    """
    Cache invalidation decorator.
    
    Usage:
        @cache_invalidate("user:*")
        async def update_user(user_id: int, data: dict) -> None:
            await db.update(...)
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            result = await func(*args, **kwargs)
            
            # Invalidate cache
            keys = await redis_manager.keys(key_pattern)
            if keys:
                await redis_manager.delete(*keys)
                logger.debug("Cache invalidated: %d keys matching '%s'", len(keys), key_pattern)
            
            return result
        
        return cast(F, wrapper)
    return decorator


class RateLimiter:
    """
    Rate limiter using Redis.
    
    Usage:
        limiter = RateLimiter(key="api:user:123", limit=100, window=60)
        if await limiter.is_allowed():
            # Process request
            pass
    """
    
    def __init__(
        self,
        key: str,
        limit: int,
        window: int = 60,
    ) -> None:
        self.key = f"ratelimit:{key}"
        self.limit = limit
        self.window = window
    
    async def is_allowed(self) -> bool:
        """Check if request is allowed."""
        try:
            count = await redis_manager.incr(self.key)
            
            if count == 1:
                await redis_manager.expire(self.key, self.window)
            
            return count <= self.limit
            
        except Exception as e:
            logger.error("Rate limiter error: %s", e)
            # Fail open on error
            return True
    
    async def get_remaining(self) -> int:
        """Get remaining requests."""
        value = await redis_manager.get(self.key)
        if not value:
            return self.limit
        
        count = int(value)
        return max(0, self.limit - count)
    
    async def get_reset_time(self) -> int:
        """Get time until reset (seconds)."""
        ttl = await redis_manager.ttl(self.key)
        return max(0, ttl)


class DistributedLock:
    """
    Distributed lock using Redis.
    
    Usage:
        async with DistributedLock("process:import", ttl=30):
            # Do work
            pass
    """
    
    def __init__(
        self,
        key: str,
        ttl: int = 10,
        blocking: bool = False,
        timeout: int = 10,
    ) -> None:
        self.key = f"lock:{key}"
        self.ttl = ttl
        self.blocking = blocking
        self.timeout = timeout
        self._locked = False
    
    async def acquire(self) -> bool:
        """Acquire lock."""
        if self.blocking:
            start = asyncio.get_event_loop().time()
            while True:
                if await redis_manager.set(self.key, "1", ttl=self.ttl, nx=True):
                    self._locked = True
                    return True
                
                elapsed = asyncio.get_event_loop().time() - start
                if elapsed >= self.timeout:
                    return False
                
                await asyncio.sleep(0.1)
        else:
            self._locked = await redis_manager.set(self.key, "1", ttl=self.ttl, nx=True)
            return self._locked
    
    async def release(self) -> bool:
        """Release lock."""
        if self._locked:
            await redis_manager.delete(self.key)
            self._locked = False
            return True
        return False
    
    async def __aenter__(self) -> "DistributedLock":
        acquired = await self.acquire()
        if not acquired:
            raise RuntimeError(f"Failed to acquire lock: {self.key}")
        return self
    
    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.release()


class RedisQueue:
    """
    Simple queue using Redis lists.
    
    Usage:
        queue = RedisQueue("tasks")
        await queue.push({"task": "send_email"})
        task = await queue.pop()
    """
    
    def __init__(self, name: str) -> None:
        self.name = f"queue:{name}"
    
    async def push(self, item: Any) -> int:
        """Push item to queue."""
        data = json.dumps(item, ensure_ascii=False)
        return await redis_manager.rpush(self.name, data)
    
    async def pop(self, timeout: int = 0) -> Optional[Any]:
        """Pop item from queue."""
        if timeout > 0:
            result: list[Any] | None = await cast(Awaitable[list[Any] | None], redis_manager.client.blpop([self.name], timeout=timeout))
            if result:
                _, data = result
                if isinstance(data, bytes):
                    return json.loads(data.decode())
                return json.loads(data)
            return None
        else:
            data = await redis_manager.lpop(self.name)
            return json.loads(data) if data else None
    
    async def size(self) -> int:
        """Get queue size."""
        return await redis_manager.llen(self.name)
    
    async def clear(self) -> bool:
        """Clear queue."""
        return await redis_manager.delete(self.name) > 0


class SessionStore:
    """
    Session store using Redis.
    
    Usage:
        store = SessionStore(session_id="abc123", ttl=3600)
        await store.set("user_id", 123)
        user_id = await store.get("user_id")
    """
    
    def __init__(self, session_id: str, ttl: int = 3600) -> None:
        self.session_id = f"session:{session_id}"
        self.ttl = ttl
    
    async def set(self, key: str, value: Any) -> bool:
        """Set session field."""
        try:
            value_str = json.dumps(value, ensure_ascii=False)
            await redis_manager.hset(self.session_id, key, value_str)
            await redis_manager.expire(self.session_id, self.ttl)
            return True
        except Exception as e:
            logger.error("Session set error: %s", e)
            return False
    
    async def get(self, key: str) -> Optional[Any]:
        """Get session field."""
        value = await redis_manager.hget(self.session_id, key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return None
    
    async def get_all(self) -> dict[str, Any]:
        """Get all session data."""
        data = await redis_manager.hgetall(self.session_id)
        result: dict[str, Any] = {}
        for key, value in data.items():
            try:
                result[key] = json.loads(value)
            except json.JSONDecodeError:
                result[key] = value
        return result
    
    async def delete(self, *keys: str) -> int:
        """Delete session fields."""
        return await redis_manager.hdel(self.session_id, *keys)
    
    async def destroy(self) -> bool:
        """Delete entire session."""
        return await redis_manager.delete(self.session_id) > 0
    
    async def exists(self) -> bool:
        """Check if session exists."""
        return await redis_manager.exists(self.session_id) > 0
    
    async def refresh(self) -> bool:
        """Refresh session TTL."""
        return await redis_manager.expire(self.session_id, self.ttl)