from slowapi.util import get_remote_address
from fastapi import FastAPI
from src.core.configs import settings
from slowapi import Limiter
from typing import Union


class DummyLimiter:
    def limit(self, *args, **kwargs):
        def decorator(func):
            return func

        return decorator

    def exempt(self, func):
        return func


limiter: Union[Limiter, DummyLimiter]

if settings.RATE_LIMIT_ENABLED:
    limiter = Limiter(
        key_func=get_remote_address, default_limits=[settings.RATE_LIMIT_PER_MINUTE]
    )
else:
    limiter = DummyLimiter()


def setup_rate_limit(app: FastAPI):
    if settings.RATE_LIMIT_ENABLED:
        app.state.limiter = limiter


__all__ = ["limiter", "setup_rate_limit"]
