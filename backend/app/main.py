from .gateway import APIGateway, APIVersion
from .routers import (
    documents_refactored as documents,
    uploads,
    folders,
    search,
    files
)
from .routers.dependencies import initialize_database, initialize_services
from .core.config import UPLOAD_DIR
from .core.logging_config import setup_logging, get_logger
import os

# Initialize logging
setup_logging()
logger = get_logger(__name__)

# Initialize API Gateway
gateway = APIGateway(
    title="DocVault AI API",
    description="Document management system with AI processing - Scalable to millions of users",
    version="1.0.0"
)

# Setup middleware (CORS, rate limiting, logging, error handling)
gateway.setup_middleware()

# Register routers with API versioning
gateway.register_router(documents.router, prefix="/api/v1", tags=["Documents"], version=APIVersion.V1)
gateway.register_router(uploads.router, prefix="/api/v1", tags=["Uploads"], version=APIVersion.V1)
gateway.register_router(folders.router, prefix="/api/v1", tags=["Folders"], version=APIVersion.V1)
gateway.register_router(search.router, prefix="/api/v1", tags=["Search"], version=APIVersion.V1)
gateway.register_router(files.router, prefix="/api/v1", tags=["Files"], version=APIVersion.V1)

# Also register without version prefix for backward compatibility
gateway.register_router(documents.router, tags=["Documents"])
gateway.register_router(uploads.router, tags=["Uploads"])
gateway.register_router(folders.router, tags=["Folders"])
gateway.register_router(search.router, tags=["Search"])
gateway.register_router(files.router, tags=["Files"])

# Register health check endpoints
gateway.register_health_endpoints()

# Get FastAPI app instance
app = gateway.get_app()

@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    logger.info("=" * 60)
    logger.info("Starting DocVault AI Backend...")
    logger.info("=" * 60)
    
    # Log framework and server information
    import sys
    try:
        import fastapi
        import uvicorn
        logger.info("Framework & Server:")
        logger.info(f"  → FastAPI Version: {fastapi.__version__}")
        logger.info(f"  → Uvicorn Version: {uvicorn.__version__}")
        logger.info(f"  → Python Version: {sys.version.split()[0]}")
        logger.info(f"  → Server: Uvicorn ASGI Server")
    except Exception as e:
        logger.debug(f"Could not get framework versions: {e}")
    
    # Log FastAPI configuration
    logger.info("API Gateway Configuration:")
    logger.info(f"  → API Title: {app.title}")
    logger.info(f"  → API Version: {app.version}")
    logger.info(f"  → Docs URL: {app.docs_url if app.docs_url else 'Disabled (production)'}")
    logger.info(f"  → Environment: {os.getenv('ENVIRONMENT', 'development')}")
    
    # Log rate limiting configuration
    from .core.config import RATE_LIMIT_ENABLED, RATE_LIMIT_PER_MINUTE, RATE_LIMIT_PER_HOUR
    logger.info("Rate Limiting:")
    logger.info(f"  → Enabled: {RATE_LIMIT_ENABLED}")
    if RATE_LIMIT_ENABLED:
        logger.info(f"  → Limit: {RATE_LIMIT_PER_MINUTE} requests/minute, {RATE_LIMIT_PER_HOUR} requests/hour")
    
    # Log CORS configuration
    cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")
    logger.info("CORS Configuration:")
    logger.info(f"  → Allowed Origins: {', '.join(cors_origins)}")
    logger.info(f"  → Allow Credentials: True")
    logger.info(f"  → Allow Methods: *")
    
    # Log worker/queue configuration
    logger.info("Worker & Queue System:")
    logger.info("  → Upload Queue: AsyncIO-based worker pool (in-process)")
    logger.info("  → Worker Type: AsyncIO Tasks (not separate processes)")
    logger.info("  → Scaling: Dynamic (5-1000 workers based on queue size)")
    logger.info("  → Retry Logic: Exponential backoff (3 retries)")
    
    # Check for Celery configuration
    from .core.config import CELERY_BROKER_URL, CELERY_RESULT_BACKEND
    logger.info("Celery Configuration:")
    logger.info(f"  → Broker URL: {CELERY_BROKER_URL}")
    logger.info(f"  → Result Backend: {CELERY_RESULT_BACKEND}")
    try:
        import celery
        logger.info(f"  → Celery Installed: Yes (version: {celery.__version__})")
        logger.info("  → Status: Available but not currently used (using FastAPI BackgroundTasks)")
    except ImportError:
        logger.info("  → Celery Installed: No")
        logger.info("  → Status: Not configured (using FastAPI BackgroundTasks for AI processing)")
    
    # Ensure upload directory exists
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    logger.debug(f"Upload directory: {UPLOAD_DIR}")
    
    # Initialize database and services
    await initialize_database()
    await initialize_services()
    
    # Log router registration
    route_summary = gateway.get_route_summary()
    logger.info("API Routes:")
    logger.info(f"  → Total Routes: {route_summary['total_routes']}")
    logger.info(f"  → Total Routers: {route_summary['total_routers']}")
    logger.info(f"  → Routes by Method: {route_summary['routes_by_method']}")
    logger.info(f"  → Routes by Tag: {route_summary['routes_by_tag']}")
    logger.info("API Endpoints:")
    logger.info("  → Documents: /documents/* and /api/v1/documents/*")
    logger.info("  → Uploads: /upload/* and /api/v1/upload/*")
    logger.info("  → Folders: /documents/folders/* and /api/v1/documents/folders/*")
    logger.info("  → Search: /search/* and /api/v1/search/*")
    logger.info("  → Files: /files/* and /api/v1/files/*")
    logger.info("  ✅ All routers registered with API Gateway")
    
    # Log external service integrations
    logger.info("External Service Integrations:")
    from .core.config import AI_PROVIDER, STORAGE_TYPE, DATABASE_TYPE, REDIS_HOST, REDIS_PORT, S3_BUCKET_NAME, AWS_REGION, SUPABASE_STORAGE_BUCKET
    from .services.providers import AIProviderFactory
    
    # AI Provider
    try:
        provider = AIProviderFactory.get_provider()
        provider_name = type(provider).__name__
        logger.info(f"  → AI Provider: {provider_name}")
        if AI_PROVIDER:
            logger.info(f"  → AI Provider Type: {AI_PROVIDER}")
        if hasattr(provider, 'api_key') and provider.api_key:
            logger.info("  → AI API Key: Configured")
        else:
            logger.warning("  → AI API Key: Not configured (using MockProvider)")
    except Exception as e:
        logger.warning(f"  → AI Provider: Error initializing - {e}")
    
    # Storage Backend
    logger.info(f"  → Storage Backend: {STORAGE_TYPE.upper()}")
    if STORAGE_TYPE.lower() == "s3":
        if S3_BUCKET_NAME:
            logger.info(f"    → S3 Bucket: {S3_BUCKET_NAME}")
            logger.info(f"    → AWS Region: {AWS_REGION}")
        else:
            logger.warning("    → S3 Bucket: Not configured")
    elif STORAGE_TYPE.lower() == "supabase":
        if SUPABASE_STORAGE_BUCKET:
            logger.info(f"    → Supabase Bucket: {SUPABASE_STORAGE_BUCKET}")
        else:
            logger.warning("    → Supabase Bucket: Not configured")
    
    # Database Backend
    logger.info(f"  → Database Backend: {DATABASE_TYPE.upper()}")
    
    # Redis/Cache
    logger.info(f"  → Redis Cache: {REDIS_HOST}:{REDIS_PORT}")
    from .routers.dependencies import cache_service
    if cache_service:
        logger.info("    → Status: Connected")
    else:
        logger.info("    → Status: Not available (optional)")
    
    logger.info("=" * 60)
    logger.info("✅ DocVault AI Backend initialized successfully")
    logger.info("=" * 60)

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down DocVault AI Backend...")
    
    # Disconnect cache service
    try:
        from .services.cache_service import cache_service
        await cache_service.disconnect()
        logger.debug("Cache service disconnected")
    except Exception as e:
        logger.debug(f"Error disconnecting cache service: {e}")
    
    logger.info("DocVault AI Backend shutdown complete")

# Health check endpoints are registered by gateway.register_health_endpoints()
