"""
Route Registry Module

Centralized registry for API routes with metadata and documentation.
"""
from typing import Dict, List, Optional, Callable, Any
from fastapi import APIRouter
from ..core.logging_config import get_logger

logger = get_logger(__name__)


class RouteMetadata:
    """Metadata for a registered route."""
    
    def __init__(
        self,
        path: str,
        method: str,
        handler: Callable,
        tags: Optional[List[str]] = None,
        summary: Optional[str] = None,
        description: Optional[str] = None,
        deprecated: bool = False
    ):
        self.path = path
        self.method = method.upper()
        self.handler = handler
        self.tags = tags or []
        self.summary = summary
        self.description = description
        self.deprecated = deprecated


class RouteRegistry:
    """
    Centralized registry for API routes.
    
    Provides a single source of truth for all API routes with metadata,
    making it easier to generate documentation, track changes, and manage routes.
    """
    
    def __init__(self):
        self._routes: Dict[str, RouteMetadata] = {}
        self._routers: List[APIRouter] = []
    
    def register_route(
        self,
        path: str,
        method: str,
        handler: Callable,
        tags: Optional[List[str]] = None,
        summary: Optional[str] = None,
        description: Optional[str] = None,
        deprecated: bool = False
    ):
        """
        Register a route with metadata.
        
        Args:
            path: Route path (e.g., "/documents")
            method: HTTP method (GET, POST, etc.)
            handler: Route handler function
            tags: OpenAPI tags for documentation
            summary: Brief summary of the route
            description: Detailed description
            deprecated: Whether the route is deprecated
        """
        route_key = f"{method.upper()}:{path}"
        
        if route_key in self._routes:
            logger.warning(f"Route {route_key} already registered, overriding")
        
        metadata = RouteMetadata(
            path=path,
            method=method,
            handler=handler,
            tags=tags,
            summary=summary,
            description=description,
            deprecated=deprecated
        )
        
        self._routes[route_key] = metadata
        logger.debug(f"Registered route: {method.upper()} {path}")
    
    def register_router(self, router: APIRouter, prefix: str = ""):
        """
        Register a FastAPI router.
        
        Args:
            router: FastAPI router instance
            prefix: Optional prefix for all routes in the router
        """
        self._routers.append(router)
        logger.debug(f"Registered router with prefix '{prefix}'")
    
    def get_route(self, method: str, path: str) -> Optional[RouteMetadata]:
        """Get route metadata by method and path."""
        route_key = f"{method.upper()}:{path}"
        return self._routes.get(route_key)
    
    def get_all_routes(self) -> List[RouteMetadata]:
        """Get all registered routes."""
        return list(self._routes.values())
    
    def get_routes_by_tag(self, tag: str) -> List[RouteMetadata]:
        """Get all routes with a specific tag."""
        return [route for route in self._routes.values() if tag in route.tags]
    
    def get_deprecated_routes(self) -> List[RouteMetadata]:
        """Get all deprecated routes."""
        return [route for route in self._routes.values() if route.deprecated]
    
    def get_route_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all registered routes.
        
        Returns:
            Dictionary with route statistics and list of routes
        """
        return {
            "total_routes": len(self._routes),
            "total_routers": len(self._routers),
            "routes_by_method": self._get_routes_by_method(),
            "routes_by_tag": self._get_routes_by_tag(),
            "deprecated_count": len(self.get_deprecated_routes()),
            "routes": [
                {
                    "method": route.method,
                    "path": route.path,
                    "tags": route.tags,
                    "summary": route.summary,
                    "deprecated": route.deprecated
                }
                for route in sorted(self._routes.values(), key=lambda r: (r.method, r.path))
            ]
        }
    
    def _get_routes_by_method(self) -> Dict[str, int]:
        """Get count of routes by HTTP method."""
        methods: Dict[str, int] = {}
        for route in self._routes.values():
            methods[route.method] = methods.get(route.method, 0) + 1
        return methods
    
    def _get_routes_by_tag(self) -> Dict[str, int]:
        """Get count of routes by tag."""
        tags: Dict[str, int] = {}
        for route in self._routes.values():
            for tag in route.tags:
                tags[tag] = tags.get(tag, 0) + 1
        return tags

