import re
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import unquote, urlparse


def parse_size(size: str | int) -> int:
    if isinstance(size, int):
        return size

    size = size.strip().upper()

    match = re.fullmatch(r"(\d+)\s*(B|KB|MB|GB)?", size)
    if not match:
        raise ValueError("Invalid file size format")

    value, unit = match.groups()
    value = int(value)

    return (
        value
        * {
            None: 1,
            "B": 1,
            "KB": 1024,
            "MB": 1024**2,
            "GB": 1024**3,
        }[unit]
    )


def timestamp_to_datetime(timestamp: float) -> datetime:
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)


def extract_path_from_url(url: str, base_path: str = "/") -> Optional[str]:
    if not url:
        return None

    try:
        parsed = urlparse(url)
        path = unquote(parsed.path)

        if base_path and path.startswith(base_path):
            path = path[len(base_path) :]
        elif path.startswith("/"):
            path = path[1:]

        if not path or ".." in path or path.startswith("/"):
            return None

        path = path.strip("/")

        if not re.match(r"^[a-zA-Z0-9_\-/\.]+$", path):
            return None

        return path if path else None
    except Exception:
        return None


def sanitize_filename(filename: str) -> str:
    filename = filename.split("/")[-1].split("\\")[-1]
    filename = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", filename)

    if len(filename) > 255:
        name, ext = filename.rsplit(".", 1) if "." in filename else (filename, "")
        filename = name[:250] + ("." + ext if ext else "")

    return filename


def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt
