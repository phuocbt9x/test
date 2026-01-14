import re
from typing import Optional
from urllib.parse import urlparse, unquote


def get_file_url(file_path: Optional[str]) -> Optional[str]:
    if not file_path:
        return None
    try:
        from .manager import storage_manager

        storage = storage_manager.get_instance()
        return storage.get_url(file_path)
    except (RuntimeError, AttributeError):
        try:
            from src.core.configs import settings
            from .local_storage import LocalStorageProvider

            if settings.STORAGE_PROVIDER == "local":
                return LocalStorageProvider.url_for(file_path)
        except Exception:
            pass
        return None
    except Exception:
        return None


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
