"""
API Gateway

Main gateway class that orchestrates routing, middleware, and API versioning.
Acts as the single entry point for all API requests.
"""
import os
from typing import Optional, List
from fastapi import FastAPI, APIRouter, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from ..core.config import (
    RATE_LIMIT_ENABLED,
    RATE_LIMIT_PER_MINUTE,
    RATE_LIMIT_PER_HOUR
)
from ..core.logging_config import get_logger
from .versioning import VersionRouter, APIVersion
from .routing import RouteRegistry
from .middleware import (
    RequestIDMiddleware,
    RequestLoggingMiddleware,
    ErrorHandlingMiddleware,
    IdempotencyMiddleware
)

logger = get_logger(__name__)


class APIGateway:
    """
    API Gateway that manages routing, middleware, and API versioning.
    
    Responsibilities:
    - Initialize FastAPI application
    - Register middleware (CORS, rate limiting, logging, error handling)
    - Manage API versioning
    - Register routes and routers
    - Provide health check endpoints
    """
    
    def __init__(
        self,
        title: str = "DocVault AI API",
        description: str = "Document management system with AI processing",
        version: str = "1.0.0",
        enable_docs: Optional[bool] = None
    ):
        """
        Initialize API Gateway.
        
        Args:
            title: API title
            description: API description
            version: API version
            enable_docs: Enable API docs (auto-detected from ENVIRONMENT if None)
        """
        self.title = title
        self.description = description
        self.version = version
        self.enable_docs = enable_docs if enable_docs is not None else (
            os.getenv("ENVIRONMENT") != "production"
        )
        
        # Initialize FastAPI app
        self.app = FastAPI(
            title=self.title,
            description=self.description,
            version=self.version,
            docs_url="/docs" if self.enable_docs else None,
            redoc_url="/redoc" if self.enable_docs else None
        )
        
        # Initialize components
        self.version_router = VersionRouter()
        self.route_registry = RouteRegistry()
        
        # Initialize rate limiter
        self.limiter = Limiter(
            key_func=get_remote_address,
            enabled=RATE_LIMIT_ENABLED
        )
        self.app.state.limiter = self.limiter
        self.app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
        
        logger.info("API Gateway initialized")
    
    def setup_middleware(self):
        """Configure all middleware."""
        logger.info("Setting up middleware...")
        
        # Error handling (must be first to catch all errors)
        self.app.add_middleware(ErrorHandlingMiddleware)
        logger.debug("  → Error handling middleware added")
        
        # Idempotency (should be early to intercept duplicate requests)
        self.app.add_middleware(IdempotencyMiddleware)
        logger.debug("  → Idempotency middleware added")
        
        # Request ID (for tracing)
        self.app.add_middleware(RequestIDMiddleware)
        logger.debug("  → Request ID middleware added")
        
        # Request logging
        self.app.add_middleware(
            RequestLoggingMiddleware,
            skip_paths=["/health", "/ready", "/docs", "/redoc", "/openapi.json"]
        )
        logger.debug("  → Request logging middleware added")
        
        # CORS
        cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        logger.debug(f"  → CORS middleware added (origins: {', '.join(cors_origins)})")
        
        logger.info("✅ All middleware configured")
    
    def register_router(
        self,
        router: APIRouter,
        prefix: str = "",
        tags: Optional[List[str]] = None,
        version: Optional[APIVersion] = None
    ):
        """
        Register a router with the gateway.
        
        Args:
            router: FastAPI router instance
            prefix: URL prefix for the router (e.g., "/api/v1")
            tags: OpenAPI tags for documentation
            version: API version (if None, uses default)
        """
        if version:
            # Register with version router
            version_prefix = f"/{version.value}" if prefix else f"/{version.value}"
            full_prefix = f"{version_prefix}{prefix}" if prefix else version_prefix
            self.app.include_router(router, prefix=full_prefix, tags=tags or [])
            self.version_router.register(version, router, prefix=full_prefix)
            logger.info(f"Registered router with version {version.value} at prefix '{full_prefix}'")
        else:
            # Register without versioning
            self.app.include_router(router, prefix=prefix, tags=tags or [])
            logger.info(f"Registered router at prefix '{prefix}'")
        
        self.route_registry.register_router(router, prefix=prefix)
    
    def register_health_endpoints(self):
        """Register health check endpoints."""
        
        @self.app.get("/")
        async def root():
            """Root endpoint - API information."""
            logger.debug("Root endpoint accessed")
            return {
                "message": f"{self.title} is running",
                "version": self.version,
                "status": "healthy",
                "api_versions": [v.value for v in self.version_router.get_all_versions()]
            }
        
        @self.app.get("/health")
        async def health_check():
            """
            Health check endpoint for container orchestration.
            
            Used by Docker/Kubernetes for liveness probes.
            Returns 200 if healthy, 503 if unhealthy.
            """
            logger.debug("Health check requested")
            try:
                # Check database connectivity
                from ..routers.dependencies import db_service
                if db_service is None:
                    logger.warning("Health check failed: Database not initialized")
                    from fastapi import Response
                    return Response(
                        content='{"status": "unhealthy", "reason": "Database not initialized"}',
                        media_type="application/json",
                        status_code=503
                    )
                
                # Check if services are initialized
                from ..routers.dependencies import upload_service, search_service
                if upload_service is None or search_service is None:
                    logger.warning("Health check failed: Services not initialized")
                    from fastapi import Response
                    return Response(
                        content='{"status": "unhealthy", "reason": "Services not initialized"}',
                        media_type="application/json",
                        status_code=503
                    )
                
                logger.debug("Health check passed")
                return {
                    "status": "healthy",
                    "database": "connected",
                    "services": "initialized"
                }
            except Exception as e:
                logger.error(f"Health check failed with exception: {e}", exc_info=True)
                from fastapi import Response
                return Response(
                    content=f'{{"status": "unhealthy", "reason": "{str(e)}"}}',
                    media_type="application/json",
                    status_code=503
                )
        
        @self.app.get("/ready")
        async def readiness_check():
            """
            Readiness check endpoint for Kubernetes.
            
            Used by Kubernetes for readiness probes.
            Verifies the application can handle traffic.
            """
            logger.debug("Readiness check requested")
            try:
                from ..routers.dependencies import db_service
                if db_service is None:
                    logger.warning("Readiness check failed: Database not initialized")
                    from fastapi import Response
                    return Response(
                        content='{"ready": false, "reason": "Database not initialized"}',
                        media_type="application/json",
                        status_code=503
                    )
                
                # Try a simple database operation to verify connectivity
                await db_service.get_all_documents(limit=1)
                
                logger.debug("Readiness check passed")
                return {"ready": True}
            except Exception as e:
                logger.error(f"Readiness check failed: {e}", exc_info=True)
                from fastapi import Response
                return Response(
                    content=f'{{"ready": false, "reason": "{str(e)}"}}',
                    media_type="application/json",
                    status_code=503
                )
        
        logger.info("Health check endpoints registered")
    
    def get_app(self) -> FastAPI:
        """Get the FastAPI application instance."""
        return self.app
    
    def get_route_summary(self) -> dict:
        """Get a summary of all registered routes."""
        return self.route_registry.get_route_summary()

