import json
import time
import uuid
from typing import Callable

from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.configs import logging_settings
from src.core.loggings import get_logger, LoggingContext, DataMasker


logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Enhanced loggings middleware with:
    - Request/Response tracking
    - Structured loggings (JSON)
    - Sensitive data masking
    - Correlation ID for distributed tracing
    - Performance monitoring
    """
    
    # Paths to exclude from loggings (health checks, metrics, etc.)
    EXCLUDED_PATHS = {"/health", "/metrics", "/favicon.ico"}
    
    def __init__(self, app):
        super().__init__(app)
        self.masker = DataMasker(
            sensitive_headers=logging_settings.LOGGING_SENSITIVE_HEADERS,
            sensitive_fields=logging_settings.LOGGING_SENSITIVE_BODY_FIELDS,
        )
    
    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        """Process request and log details"""
        
        # Skip loggings for excluded paths
        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)
        
        # Generate tracking IDs
        request_id = str(uuid.uuid4())
        correlation_id = request.headers.get(
            "X-Correlation-ID",
            str(uuid.uuid4()),
        )
        
        # Set context for loggings
        LoggingContext.set_request_id(request_id)
        LoggingContext.set_correlation_id(correlation_id)
        
        # Store in request state
        request.state.request_id = request_id
        request.state.correlation_id = correlation_id
        
        # Extract request info
        client_host = request.client.host if request.client else "unknown"
        method = request.method
        path = request.url.path
        query_params = dict(request.query_params) if request.query_params else {}
        
        # Mask headers
        self.masker.mask_headers(dict(request.headers))
        
        # Log request start
        logger.info(
            f"Request started: {method} {path}",
            extra={
                "method": method,
                "path": path,
                "client": client_host,
                "query_params": query_params,
            },
        )
        
        # Log request body if enabled and method is POST/PUT/PATCH
        if logging_settings.LOGGING_REQUEST_BODY and method in ["POST", "PUT", "PATCH"]:
            await self._log_request_body(request)
        
        # Start timer
        start_time = time.time()
        
        try:
            # Call next middleware/endpoint
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            status_code = response.status_code
            
            # Add tracking headers to response
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Correlation-ID"] = correlation_id
            response.headers["X-Process-Time"] = f"{duration:.4f}"
            
            # Determine log level based on status code
            if status_code < status.HTTP_400_BAD_REQUEST:
                log_level = "info"
                status_label = "SUCCESS"
            elif status_code < status.HTTP_500_INTERNAL_SERVER_ERROR:
                log_level = "warning"
                status_label = "CLIENT_ERROR"
            else:
                log_level = "error"
                status_label = "SERVER_ERROR"
            
            # Log slow requests
            if duration > logging_settings.LOGGING_SLOW_REQUEST_THRESHOLD:
                logger.warning(
                    f"Slow request detected: {method} {path}",
                    extra={
                        "method": method,
                        "path": path,
                        "duration": duration,
                        "status_code": status_code,
                    },
                )
            
            # Log request completion
            getattr(logger, log_level)(
                f"Request completed: {status_label} - {method} {path}",
                extra={
                    "method": method,
                    "path": path,
                    "status_code": status_code,
                    "duration": duration,
                },
            )
            
            return response
        
        except Exception as e:
            # Calculate duration even on error
            duration = time.time() - start_time
            
            # Log error with full context
            logger.error(
                f"Request failed: {method} {path}",
                extra={
                    "method": method,
                    "path": path,
                    "duration": duration,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                exc_info=True,
            )
            
            raise
        
        finally:
            # Clear context after request
            LoggingContext.clear()
    
    async def _log_request_body(self, request: Request) -> None:
        """Log request body with sensitive data masking"""
        try:
            # Read request body
            body = await request.body()
            
            # Check size limit
            if len(body) > logging_settings.LOGGING_REQUEST_BODY_MAX_SIZE:
                logger.debug(
                    f"Request body too large to log: {len(body)} bytes",
                    extra={"body_size": len(body)},
                )
                return
            
            # Try to parse as JSON
            try:
                body_json = json.loads(body)
                masked_body = self.masker.mask_dict(body_json)
                logger.debug(
                    "Request body (JSON)",
                    extra={"body": masked_body},
                )
            except json.JSONDecodeError:
                # Log as string with masking
                body_str = body.decode("utf-8", errors="ignore")
                masked_str = self.masker.mask_string(body_str)
                logger.debug(
                    "Request body (text)",
                    extra={"body": masked_str},
                )
            
            # CRITICAL: Reset request body for next middleware/endpoint
            # Without this, FastAPI won't be able to read the body
            async def receive():
                return {"type": "http.request", "body": body}
            
            request._receive = receive
        
        except Exception as e:
            logger.warning(
                f"Failed to log request body: {e}",
                extra={"error": str(e)},
            )