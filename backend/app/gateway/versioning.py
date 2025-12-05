"""
API Versioning Module

Handles API versioning strategy and version-based routing.
Supports URL-based versioning (e.g., /v1/documents) and header-based versioning.
"""
from enum import Enum
from typing import Optional, Dict, Any
from fastapi import APIRouter, Request
from ..core.logging_config import get_logger

logger = get_logger(__name__)


class APIVersion(str, Enum):
    """Supported API versions."""
    V1 = "v1"
    V2 = "v2"  # Future version
    
    @classmethod
    def latest(cls) -> "APIVersion":
        """Get the latest API version."""
        return cls.V1
    
    @classmethod
    def default(cls) -> "APIVersion":
        """Get the default API version."""
        return cls.V1


class VersionRouter:
    """
    Router that handles version-specific routing.
    
    Usage:
        version_router = VersionRouter()
        version_router.register(APIVersion.V1, v1_router)
        version_router.register(APIVersion.V2, v2_router)
    """
    
    def __init__(self):
        self._routers: Dict[APIVersion, APIRouter] = {}
        self._default_version = APIVersion.default()
    
    def register(self, version: APIVersion, router: APIRouter, prefix: str = ""):
        """
        Register a router for a specific API version.
        
        Args:
            version: API version to register
            router: FastAPI router instance
            prefix: Optional prefix for the router (e.g., "/api")
        """
        if version in self._routers:
            logger.warning(f"Overriding existing router for version {version.value}")
        
        self._routers[version] = router
        logger.debug(f"Registered router for API version {version.value} with prefix '{prefix}'")
    
    def get_router(self, version: Optional[APIVersion] = None) -> APIRouter:
        """
        Get router for a specific version.
        
        Args:
            version: API version. If None, returns default version router.
        
        Returns:
            FastAPI router for the specified version
        """
        if version is None:
            version = self._default_version
        
        if version not in self._routers:
            logger.warning(f"No router registered for version {version.value}, using default")
            version = self._default_version
        
        return self._routers.get(version)
    
    def get_version_from_request(self, request: Request) -> APIVersion:
        """
        Extract API version from request.
        
        Checks in order:
        1. URL path (e.g., /v1/documents)
        2. X-API-Version header
        3. Accept header (e.g., application/vnd.api.v1+json)
        4. Default version
        
        Args:
            request: FastAPI request object
        
        Returns:
            Detected API version
        """
        # Check URL path
        path = request.url.path
        if path.startswith("/v1/"):
            return APIVersion.V1
        elif path.startswith("/v2/"):
            return APIVersion.V2
        
        # Check X-API-Version header
        api_version_header = request.headers.get("X-API-Version")
        if api_version_header:
            try:
                return APIVersion(api_version_header.lower())
            except ValueError:
                logger.debug(f"Invalid API version in header: {api_version_header}")
        
        # Check Accept header for versioned media type
        accept_header = request.headers.get("Accept", "")
        if "vnd.api.v1" in accept_header:
            return APIVersion.V1
        elif "vnd.api.v2" in accept_header:
            return APIVersion.V2
        
        # Default to latest version
        return self._default_version
    
    def get_all_versions(self) -> list[APIVersion]:
        """Get all registered API versions."""
        return list(self._routers.keys())
    
    def set_default_version(self, version: APIVersion):
        """Set the default API version."""
        self._default_version = version
        logger.info(f"Default API version set to {version.value}")

