import logging
import os
import sys
import json

from typing import Any, Dict
from pathlib import Path
from src.core.utils.timezone import utcnow
from .context import LoggingContext
from logging.handlers import TimedRotatingFileHandler
from src.core.configs import logging_settings
from .masking import DataMasker
import re


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        if request_id := LoggingContext.get_request_id():
            log_data["request_id"] = request_id
        
        if correlation_id := LoggingContext.get_correlation_id():
            log_data["correlation_id"] = correlation_id
        
        if user_id := LoggingContext.get_user_id():
            log_data["user_id"] = user_id
        
        if hasattr(record, "duration"):
            log_data["duration"] = record.duration
        
        if hasattr(record, "status_code"):
            log_data["status_code"] = record.status_code
        
        if hasattr(record, "method"):
            log_data["method"] = record.method
        
        if hasattr(record, "path"):
            log_data["path"] = record.path
        
        if hasattr(record, "client"):
            log_data["client"] = record.client
        
        for key, value in record.__dict__.items():
            if key not in [
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "message",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "thread",
                "threadName",
                "exc_info",
                "exc_text",
                "stack_info",
            ] and not key.startswith("_"):
                if key not in log_data:
                    log_data[key] = value
        
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info),
            }
        
        return json.dumps(log_data, default=str)


class ColoredFormatter(logging.Formatter):
    COLORS = {
        "DEBUG": "\033[36m",      # Cyan
        "INFO": "\033[32m",       # Green
        "WARNING": "\033[33m",    # Yellow
        "ERROR": "\033[31m",      # Red
        "CRITICAL": "\033[35m",   # Magenta
    }
    RESET = "\033[0m"
    
    def format(self, record: logging.LogRecord) -> str:
        def is_colored(text):
            return any(code in text for code in self.COLORS.values())

        raw_level = record.levelname.strip()
        color = self.COLORS.get(raw_level.replace(self.RESET, ''), self.RESET)
        if not is_colored(raw_level):
            colored_level = f"{color}{raw_level}{self.RESET}"
        else:
            colored_level = raw_level

        pad_len = 8 - len(raw_level)
        if pad_len > 0:
            colored_level = colored_level + ' ' * pad_len
        record.levelname = colored_level

        context_parts = []
        if request_id := LoggingContext.get_request_id():
            context_parts.append(f"req_id={request_id[:8]}")
        if user_id := LoggingContext.get_user_id():
            context_parts.append(f"user={user_id}")
        context_str = f" [{', '.join(context_parts)}]" if context_parts else ""

        original_msg = record.getMessage()
        record.msg = f"{original_msg}{context_str}"
        record.args = ()
        return super().format(record)

def setup_logging(json_format: bool = False, level: str = "INFO") -> None:
    log_level = getattr(logging, level.upper(), logging.INFO)
    log_dir = Path("logs")
    backup_days = logging_settings.LOGGING_BACKUP_DAYS
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()

    class RequestIdFilter(logging.Filter):
        def filter(self, record):
            record.request_id = LoggingContext.get_request_id() or "-"
            record.correlation_id = LoggingContext.get_correlation_id() or "-"
            record.user_id = LoggingContext.get_user_id() or "-"
            return True

    request_filter = RequestIdFilter()
    DataMasker(
        sensitive_headers=logging_settings.LOGGING_SENSITIVE_HEADERS,
        sensitive_fields=logging_settings.LOGGING_SENSITIVE_BODY_FIELDS,
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.addFilter(request_filter)
    console_formatter: logging.Formatter
    if json_format:
        console_formatter = JSONFormatter()
    else:
        console_formatter = ColoredFormatter(
            fmt="%(asctime)s | %(levelname)-8s | %(request_id)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    log_dir.mkdir(parents=True, exist_ok=True)
    file_fmt = "%(asctime)s | %(levelname)-8s | %(request_id)s | %(name)s:%(funcName)s:%(lineno)d | %(message)s"
    file_formatter = logging.Formatter(
        fmt=file_fmt,
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    class MaxLevelFilter(logging.Filter):
        def __init__(self, max_level):
            super().__init__()
            self.max_level = max_level
        def filter(self, record) -> bool:
            return record.levelno < self.max_level


    class CustomTimedRotatingFileHandler(TimedRotatingFileHandler):
        def rotation_filename(self, default_name: str) -> str:
            match = re.match(r"(.+)/(app|error)\.log\.(\d{4}_\d{2}_\d{2})", default_name)
            if match:
                folder, base, date = match.groups()
                return f"{folder}/{base}-{date}.log"
            return default_name
        def doRollover(self):
            if self.stream:
                self.stream.close()
                self.stream = None
            if self.backupCount > 0:
                for s in self.getFilesToDelete():
                    try:
                        os.remove(s)
                    except Exception:
                        pass
            if os.path.exists(self.baseFilename) and os.path.getsize(self.baseFilename) == 0:
                os.remove(self.baseFilename)
                self.mode = 'a'
                self.stream = self._open()
                return
            super().doRollover()

    app_log_path = log_dir / "app.log"
    app_handler = CustomTimedRotatingFileHandler(
        filename=str(app_log_path),
        when="midnight",
        interval=1,
        backupCount=backup_days,
        encoding="utf-8",
        utc=True,
    )
    app_handler.suffix = "-%Y_%m_%d.log"
    app_handler.setLevel(log_level)
    app_handler.addFilter(request_filter)
    app_handler.addFilter(MaxLevelFilter(logging.ERROR))
    app_handler.setFormatter(file_formatter)
    root_logger.addHandler(app_handler)

    error_log_path = log_dir / "error.log"
    error_handler = CustomTimedRotatingFileHandler(
        filename=str(error_log_path),
        when="midnight",
        interval=1,
        backupCount=backup_days,
        encoding="utf-8",
        utc=True,
    )
    error_handler.suffix = "-%Y_%m_%d.log"
    error_handler.setLevel(logging.ERROR)
    error_handler.addFilter(request_filter)
    error_handler.setFormatter(file_formatter)
    root_logger.addHandler(error_handler)

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)