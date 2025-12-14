from contextvars import ContextVar
from typing import Optional

request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
correlation_id_var: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar("user_id", default=None)


class LoggingContext:
    
    @staticmethod
    def set_request_id(request_id: str) -> None:
        request_id_var.set(request_id)
    
    @staticmethod
    def get_request_id() -> Optional[str]:
        return request_id_var.get()
    
    @staticmethod
    def set_correlation_id(correlation_id: str) -> None:
        correlation_id_var.set(correlation_id)
    
    @staticmethod
    def get_correlation_id() -> Optional[str]:
        return correlation_id_var.get()
    
    @staticmethod
    def set_user_id(user_id: str) -> None:
        user_id_var.set(user_id)
    
    @staticmethod
    def get_user_id() -> Optional[str]:
        return user_id_var.get()
    
    @staticmethod
    def clear() -> None:
        request_id_var.set(None)
        correlation_id_var.set(None)
        user_id_var.set(None)