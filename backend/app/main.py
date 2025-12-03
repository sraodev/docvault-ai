from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from .routers import (
    documents_refactored as documents,
    uploads,
    folders,
    search,
    files
)
from .routers.dependencies import initialize_database, initialize_services
from .core.config import UPLOAD_DIR, RATE_LIMIT_ENABLED
from .core.logging_config import setup_logging, get_logger
import os
import time

# Initialize logging
setup_logging()
logger = get_logger(__name__)

# Initialize rate limiter (for million+ user scale)
limiter = Limiter(key_func=get_remote_address, enabled=RATE_LIMIT_ENABLED)
app = FastAPI(
    title="DocVault AI API",
    description="Document management system with AI processing - Scalable to millions of users",
    version="1.0.0",
    docs_url="/docs" if os.getenv("ENVIRONMENT") != "production" else None,
    redoc_url="/redoc" if os.getenv("ENVIRONMENT") != "production" else None
)

# Add rate limit exception handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS Configuration
# In production, set specific origins instead of "*"
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(documents.router, tags=["Documents"])
app.include_router(uploads.router, tags=["Uploads"])
app.include_router(folders.router, tags=["Folders"])
app.include_router(search.router, tags=["Search"])
app.include_router(files.router, tags=["Files"])

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
    logger.info("FastAPI Configuration:")
    logger.info(f"  → API Title: {app.title}")
    logger.info(f"  → API Version: {app.version}")
    logger.info(f"  → Docs URL: {app.docs_url if app.docs_url else 'Disabled (production)'}")
    logger.info(f"  → Environment: {os.getenv('ENVIRONMENT', 'development')}")
    
    # Log rate limiting configuration
    from .core.config import RATE_LIMIT_PER_MINUTE, RATE_LIMIT_PER_HOUR
    logger.info("Rate Limiting:")
    logger.info(f"  → Enabled: {RATE_LIMIT_ENABLED}")
    if RATE_LIMIT_ENABLED:
        logger.info(f"  → Limit: {RATE_LIMIT_PER_MINUTE} requests/minute, {RATE_LIMIT_PER_HOUR} requests/hour")
    
    # Log CORS configuration
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
    logger.info("API Routers:")
    logger.info("  → Documents Router: /documents/*")
    logger.info("  → Uploads Router: /upload/*")
    logger.info("  → Folders Router: /documents/folders/*")
    logger.info("  → Search Router: /search/*")
    logger.info("  → Files Router: /files/*")
    logger.info("  ✅ All routers registered")
    
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

@app.get("/")
async def root():
    """Root endpoint - API information."""
    logger.debug("Root endpoint accessed")
    return {
        "message": "DocVault AI Backend is running",
        "version": "1.0.0",
        "status": "healthy"
    }

@app.get("/health")
async def health_check():
    """
    Health check endpoint for container orchestration.
    
    Used by Docker/Kubernetes for liveness probes.
    Returns 200 if healthy, 503 if unhealthy.
    
    Returns:
        dict: Health status with HTTP 200 status code
    """
    logger.debug("Health check requested")
    try:
        # Check database connectivity
        from .routers.dependencies import db_service
        if db_service is None:
            logger.warning("Health check failed: Database not initialized")
            from fastapi import Response
            return Response(
                content='{"status": "unhealthy", "reason": "Database not initialized"}',
                media_type="application/json",
                status_code=503
            )
        
        # Check if services are initialized
        from .routers.dependencies import upload_service, search_service
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

@app.get("/ready")
async def readiness_check():
    """
    Readiness check endpoint for Kubernetes.
    
    Used by Kubernetes for readiness probes.
    Verifies the application can handle traffic.
    Returns 200 if ready, 503 if not ready.
    
    Returns:
        dict: Readiness status with HTTP 200 status code
    """
    logger.debug("Readiness check requested")
    try:
        from .routers.dependencies import db_service
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
