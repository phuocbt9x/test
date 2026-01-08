from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from src.core.i18n import get_language_from_request


class LanguageMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        await get_language_from_request(request)
        response = await call_next(request)
        return response
