from typing import Any, Dict, List, Optional
from fastapi import FastAPI
from src.core.configs import settings
from .loader import RouterLoader, LoaderConfig
from fastapi.routing import APIRoute


def auto_load_routers(
    app: FastAPI,
    modules_dir: str = "modules",
    prefix: Optional[str] = None,
    parallel: bool = False,
    **kwargs,
) -> RouterLoader:
    prefix = prefix or settings.APP_ROUTER_PREFIX

    config = LoaderConfig(
        modules_dir=modules_dir, prefix=prefix, parallel_loading=parallel, **kwargs
    )

    loader = RouterLoader(app=app, config=config)
    loader.load_all()

    return loader


def get_all_routes(app: FastAPI, include_openapi: bool = False) -> List[Dict[str, Any]]:
    routes = []
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        if not include_openapi:
            if route.path in {"/openapi.json", "/docs", "/redoc"}:
                continue
        route_info = {
            "path": route.path,
            "methods": sorted(list(route.methods)),
            "name": route.name,
            "tags": [str(tag) for tag in getattr(route, "tags", [])],
        }
        routes.append(route_info)
    return sorted(routes, key=lambda x: x["path"])


def print_routes_table(app: FastAPI) -> None:
    routes = get_all_routes(app)
    print("\n" + "=" * 100)
    print(f"{'PATH':<45} {'METHODS':<20} {'NAME':<25} {'TAGS':<10}")
    print("=" * 100)
    for route in routes:
        methods = ", ".join(route["methods"])
        tags = ", ".join(route["tags"]) if route["tags"] else "-"
        print(f"{route['path']:<45} {methods:<20} {route['name']:<25} {tags:<10}")
    print("=" * 100)
    print(f"Total: {len(routes)} routes\n")
