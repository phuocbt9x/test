from typing import Any, Dict, List, Optional
from pathlib import Path
from dataclasses import dataclass, field
from fastapi import APIRouter, FastAPI
from pydantic import BaseModel, Field
import importlib
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.core.loggings import get_logger
from fastapi.routing import APIRoute

logger = get_logger(__name__)

class RouterMetadata(BaseModel):
    module_path: str
    file_path: str
    prefix: str
    tags: List[str] = Field(default_factory=list)
    route_count: int = 0
    class Config:
        frozen = True

class LoaderConfig(BaseModel):
    modules_dir: str = "modules"
    controller_pattern: str = "controller.py"  # Changed from controllers.py to controller.py
    router_attribute: str = "router"
    prefix: str = ""
    exclude_patterns: List[str] = Field(default_factory=lambda: ["__pycache__", "tests", ".pytest_cache"])
    parallel_loading: bool = False
    max_workers: int = 4
    cache_modules: bool = True
    validate_before_load: bool = True
    class Config:
        frozen = True

class RouterValidator:
    @staticmethod
    def validate(router: APIRouter, module_path: str) -> List[str]:
        errors = []
        if not router.routes:
            errors.append("Router has no routes")
        # Check for duplicate path + method combinations
        route_signatures = set()
        for route in router.routes:
            if not isinstance(route, APIRoute):
                continue
            # Check each method for this route
            for method in route.methods:
                signature = (route.path, method)
                if signature in route_signatures:
                    errors.append(f"Duplicate route: {method} {route.path}")
                route_signatures.add(signature)
            # Validate endpoint is callable
            if not callable(route.endpoint):
                errors.append(f"Route '{route.name}' endpoint is not callable")
        return errors

class ModuleCache:
    def __init__(self) -> None:
        self._cache: Dict[str, Any] = {}
        self._lock = None
    def get(self, module_path: str) -> Optional[Any]:
        return self._cache.get(module_path)
    def set(self, module_path: str, module: Any) -> None:
        self._cache[module_path] = module
    def clear(self) -> None:
        self._cache.clear()
    def has(self, module_path: str) -> bool:
        return module_path in self._cache

@dataclass
class RouterLoader:
    app: FastAPI
    config: LoaderConfig = field(default_factory=LoaderConfig)
    _cache: ModuleCache = field(default_factory=ModuleCache, init=False)
    _loaded: Dict[str, RouterMetadata] = field(default_factory=dict, init=False)
    _errors: List[Dict[str, Any]] = field(default_factory=list, init=False)
    _validator: RouterValidator = field(default_factory=RouterValidator, init=False)
    def __post_init__(self):
        self.config = LoaderConfig(
            **{**self.config.model_dump(), "prefix": self.config.prefix.rstrip("/")}
        )
    def load_all(self) -> Dict[str, RouterMetadata]:
        start_time = self._get_time()
        controller_files = self._find_controller_files()
        if not controller_files:
            logger.warning(f"No controller files found in '{self.config.modules_dir}'")
            return {}
        logger.info(f"Found {len(controller_files)} controller files")
        if self.config.parallel_loading and len(controller_files) > 3:
            self._load_parallel(controller_files)
        else:
            self._load_sequential(controller_files)
        duration = self._get_time() - start_time
        self._log_summary(duration)
        return self._loaded
    def _find_controller_files(self) -> List[Path]:
        modules_path = Path(self.config.modules_dir)
        if not modules_path.exists():
            raise FileNotFoundError(f"Modules directory '{self.config.modules_dir}' not found")
        controller_files = []
        for file_path in modules_path.rglob(self.config.controller_pattern):
            if self._should_exclude(file_path):
                continue
            controller_files.append(file_path)
        return sorted(controller_files)
    def _should_exclude(self, file_path: Path) -> bool:
        file_str = str(file_path)
        return any(pattern in file_str for pattern in self.config.exclude_patterns)
    def _load_sequential(self, files: List[Path]) -> None:
        for file_path in files:
            self._load_single_router(file_path)
    def _load_parallel(self, files: List[Path]) -> None:
        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            futures = {executor.submit(self._load_single_router, f): f for f in files}
            for future in as_completed(futures):
                file_path = futures[future]
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Parallel loading failed for {file_path}: {e}")
    def _load_single_router(self, file_path: Path) -> Optional[RouterMetadata]:
        try:
            module_path = self._build_module_path(file_path)
            module = self._import_module(module_path)
            if not hasattr(module, self.config.router_attribute):
                logger.warning(f"No '{self.config.router_attribute}' in {module_path}")
                return None
            router = getattr(module, self.config.router_attribute)
            if not isinstance(router, APIRouter):
                logger.error(f"'{module_path}.{self.config.router_attribute}' is not APIRouter")
                return None
            if self.config.validate_before_load:
                errors = self._validator.validate(router, module_path)
                if errors:
                    logger.error(f"Router validation failed: {module_path} - {errors}")
                    return None
            metadata = self._process_router(router, module_path, str(file_path))
            self.app.include_router(router)
            self._loaded[module_path] = metadata
            logger.info(f"✓ Loaded: {module_path} -> {router.prefix} ({len(router.routes)} routes)")
            return metadata
        except Exception as e:
            self._handle_error(file_path, e)
            return None
    def _build_module_path(self, file_path: Path) -> str:
        # file_path from rglob is already relative to cwd, so use it directly
        # Convert path to module notation (e.g., "src/modules/user/controller.py" -> "src.modules.user.controller")
        return str(file_path.with_suffix("")).replace("/", ".").replace("\\", ".")
    def _import_module(self, module_path: str) -> Any:
        if self.config.cache_modules and self._cache.has(module_path):
            return self._cache.get(module_path)
        module = importlib.import_module(module_path)
        if self.config.cache_modules:
            self._cache.set(module_path, module)
        return module
    def _process_router(
        self, 
        router: APIRouter, 
        module_path: str, 
        file_path: str
    ) -> RouterMetadata:
        if self.config.prefix and not router.prefix.startswith(self.config.prefix):
            router.prefix = self.config.prefix + router.prefix
        if not router.tags:
            tag = self._generate_tag(module_path)
            router.tags = [tag]
        # Ensure tags is List[str] for mypy
        tags: List[str] = [str(tag) for tag in router.tags] if hasattr(router, "tags") else []
        return RouterMetadata(
            module_path=module_path,
            file_path=file_path,
            prefix=router.prefix,
            tags=tags,
            route_count=len(router.routes),
        )
    def _generate_tag(self, module_path: str) -> str:
        parts = module_path.split(".")
        if len(parts) >= 2:
            return parts[-2].replace("_", " ").title()
        return "API"
    def _handle_error(self, file_path: Path, error: Exception) -> None:
        error_info = {
            "file": str(file_path),
            "error": str(error),
            "type": type(error).__name__,
        }
        self._errors.append(error_info)
        logger.error(f"Failed to load {file_path}: {error}", exc_info=True)
    def _log_summary(self, duration: float) -> None:
        total = len(self._loaded) + len(self._errors)
        logger.info("=" * 70)
        logger.info("Router Loading Summary")
        logger.info(f"  Total files: {total}")
        logger.info(f"  Loaded: {len(self._loaded)}")
        logger.info(f"  Failed: {len(self._errors)}")
        logger.info(f"  Duration: {duration:.2f}s")
        logger.info("=" * 70)
        if self._errors:
            logger.warning(f"Failed to load {len(self._errors)} routers:")
            for error in self._errors:
                logger.warning(f"  - {error['file']}: {error['error']}")
    @staticmethod
    def _get_time() -> float:
        import time
        return time.perf_counter()
    def get_loaded_routers(self) -> Dict[str, RouterMetadata]:
        return self._loaded.copy()
    def get_errors(self) -> List[Dict[str, Any]]:
        return self._errors.copy()
    def clear_cache(self) -> None:
        self._cache.clear()
        logger.info("Module cache cleared")
    def reload_router(self, module_path: str) -> bool:
        try:
            if self._cache.has(module_path):
                self._cache._cache.pop(module_path)
            if module_path in sys.modules:
                module = importlib.reload(sys.modules[module_path])
            else:
                module = importlib.import_module(module_path)
            if self.config.cache_modules:
                self._cache.set(module_path, module)
            logger.info(f"Reloaded: {module_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to reload {module_path}: {e}")
            return False
