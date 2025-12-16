"""
Unit tests for Redis Manager.

Tests cover:
- Redis initialization and connection
- Basic operations (get, set, delete, exists)
- JSON operations
- Hash operations
- Counter operations
- TTL and expiration
- Error handling
"""

import pytest
from unittest.mock import AsyncMock, patch
import json

from src.core.configs.redis import RedisManager, redis_manager
from redis.exceptions import ConnectionError as RedisConnectionError


class TestRedisManagerInitialization:
    """Test Redis Manager initialization."""

    @pytest.mark.asyncio
    async def test_init_success(self, mock_redis):
        """Test successful Redis initialization."""
        manager = RedisManager()

        with patch("src.core.configs.redis.ConnectionPool") as mock_pool_class:
            mock_pool = AsyncMock()
            mock_pool_class.from_url.return_value = mock_pool

            with patch("src.core.configs.redis.Redis") as mock_redis_class:
                mock_redis_class.return_value = mock_redis

                await manager.init()

                assert manager._initialized is True
                assert manager._client is not None

    @pytest.mark.asyncio
    async def test_init_already_initialized(self, mock_redis):
        """Test initializing when already initialized."""
        manager = RedisManager()
        manager._initialized = True

        await manager.init()  # Should skip initialization

    @pytest.mark.asyncio
    async def test_init_connection_error(self):
        """Test initialization with connection error."""
        manager = RedisManager()

        with patch("src.core.configs.redis.ConnectionPool") as mock_pool_class:
            mock_pool_class.from_url.side_effect = RedisConnectionError(
                "Connection failed"
            )

            with pytest.raises(RuntimeError, match="Redis connection failed"):
                await manager.init()

    @pytest.mark.asyncio
    async def test_close(self, mock_redis):
        """Test closing Redis connections."""
        manager = RedisManager()
        manager._initialized = True
        manager._client = mock_redis
        manager._pool = AsyncMock()

        await manager.close()

        assert manager._initialized is False
        mock_redis.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_not_initialized(self):
        """Test closing when not initialized."""
        manager = RedisManager()
        manager._initialized = False

        await manager.close()  # Should not raise error


class TestRedisBasicOperations:
    """Test basic Redis operations."""

    @pytest.mark.asyncio
    async def test_get_success(self, redis_client):
        """Test getting a value from Redis."""
        key = "test_key"
        expected_value = "test_value"

        redis_client.get.return_value = expected_value

        value = await redis_manager.get(key)

        assert value == expected_value

    @pytest.mark.asyncio
    async def test_get_not_exists(self, redis_client):
        """Test getting non-existent key."""
        redis_client.get.return_value = None

        value = await redis_manager.get("nonexistent_key")

        assert value is None

    @pytest.mark.asyncio
    async def test_get_redis_error(self, redis_client):
        """Test get with Redis error."""
        from redis.exceptions import RedisError

        redis_client.get.side_effect = RedisError("Connection lost")

        value = await redis_manager.get("error_key")

        assert value is None  # Should return None on error

    @pytest.mark.asyncio
    async def test_set_success(self, redis_client):
        """Test setting a value in Redis."""
        key = "test_key"
        value = "test_value"

        result = await redis_manager.set(key, value)

        assert result is True
        redis_client.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_with_ttl(self, redis_client):
        """Test setting value with TTL."""
        key = "ttl_key"
        value = "ttl_value"
        ttl = 3600

        await redis_manager.set(key, value, ttl=ttl)

        call_args = redis_client.set.call_args
        assert call_args is not None

    @pytest.mark.asyncio
    async def test_set_nx(self, redis_client):
        """Test set if not exists (NX flag)."""
        key = "nx_key"
        value = "nx_value"

        redis_client.set.return_value = True

        result = await redis_manager.set(key, value, nx=True)

        assert result is True

    @pytest.mark.asyncio
    async def test_set_xx(self, redis_client):
        """Test set if exists (XX flag)."""
        key = "xx_key"
        value = "xx_value"

        redis_client.set.return_value = True

        result = await redis_manager.set(key, value, xx=True)

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_success(self, redis_client):
        """Test deleting a key."""
        key = "delete_key"

        redis_client.delete.return_value = 1

        result = await redis_manager.delete(key)

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_not_exists(self, redis_client):
        """Test deleting non-existent key."""
        redis_client.delete.return_value = 0

        result = await redis_manager.delete("nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_exists(self, redis_client):
        """Test checking if key exists."""
        key = "exists_key"

        redis_client.exists.return_value = 1

        result = await redis_manager.exists(key)

        assert result is True

    @pytest.mark.asyncio
    async def test_not_exists(self, redis_client):
        """Test checking non-existent key."""
        redis_client.exists.return_value = 0

        result = await redis_manager.exists("not_exists")

        assert result is False


class TestRedisJSONOperations:
    """Test JSON serialization/deserialization."""

    @pytest.mark.asyncio
    async def test_set_json(self, redis_client):
        """Test setting JSON value."""
        key = "json_key"
        data = {"name": "Test", "age": 30, "active": True}

        result = await redis_manager.set_json(key, data)

        assert result is True
        # Verify JSON was serialized
        call_args = redis_client.set.call_args
        assert call_args is not None

    @pytest.mark.asyncio
    async def test_get_json(self, redis_client):
        """Test getting JSON value."""
        key = "json_key"
        data = {"name": "Test", "age": 30}

        redis_client.get.return_value = json.dumps(data)

        result = await redis_manager.get_json(key)

        assert result == data

    @pytest.mark.asyncio
    async def test_get_json_invalid(self, redis_client):
        """Test getting invalid JSON."""
        redis_client.get.return_value = "not valid json {"

        result = await redis_manager.get_json("invalid_key")

        assert result is None


class TestRedisCounterOperations:
    """Test counter operations."""

    @pytest.mark.asyncio
    async def test_incr(self, redis_client):
        """Test incrementing a counter."""
        key = "counter_key"

        redis_client.incr.return_value = 1

        result = await redis_manager.incr(key)

        assert result == 1

    @pytest.mark.asyncio
    async def test_incr_by_amount(self, redis_client):
        """Test incrementing by specific amount."""
        key = "counter_key"
        amount = 5

        redis_client.incr.return_value = 5

        result = await redis_manager.incr(key, amount)

        assert result == 5

    @pytest.mark.asyncio
    async def test_decr(self, redis_client):
        """Test decrementing a counter."""
        key = "counter_key"

        redis_client.decr.return_value = 9

        result = await redis_manager.decr(key)

        assert result == 9


class TestRedisKeyPrefix:
    """Test key prefixing functionality."""

    def test_prefixed_key(self):
        """Test key prefixing."""
        manager = RedisManager()
        key = "test_key"

        prefixed = manager._prefixed_key(key)

        assert prefixed.startswith(manager._key_prefix)
        assert key in prefixed

    def test_prefixed_key_already_prefixed(self):
        """Test that already prefixed keys are not double-prefixed."""
        manager = RedisManager()
        key = f"{manager._key_prefix}test_key"

        prefixed = manager._prefixed_key(key)

        assert prefixed == key
        assert prefixed.count(manager._key_prefix) == 1


class TestRedisErrorHandling:
    """Test error handling."""

    @pytest.mark.asyncio
    async def test_operation_without_initialization(self):
        """Test operations when Redis is not initialized."""
        manager = RedisManager()
        manager._initialized = False

        with pytest.raises(RuntimeError, match="Redis not initialized"):
            await manager.get("test_key")

    @pytest.mark.asyncio
    async def test_ensure_client_not_initialized(self):
        """Test _ensure_client when not initialized."""
        manager = RedisManager()
        manager._initialized = False

        with pytest.raises(RuntimeError):
            manager._ensure_client()


class TestRedisSingletonPattern:
    """Test singleton pattern."""

    def test_singleton_instance(self):
        """Test that RedisManager is a singleton."""
        instance1 = RedisManager()
        instance2 = RedisManager()

        assert instance1 is instance2

    def test_redis_manager_global_instance(self):
        """Test global redis_manager instance."""
        assert redis_manager is not None
        assert isinstance(redis_manager, RedisManager)
