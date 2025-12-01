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
import os
import time

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
    # Ensure upload directory exists
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    
    # Initialize database and services
    await initialize_database()
    await initialize_services()
    
    # Initialize cache service (if Redis available)
    try:
        from .services.cache_service import cache_service
        await cache_service.connect()
        print("✅ Redis cache connected")
    except Exception as e:
        print(f"⚠️  Redis cache not available (continuing without cache): {e}")
    
    print("✅ DocVault AI Backend initialized successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    # Disconnect cache service
    try:
        from .services.cache_service import cache_service
        await cache_service.disconnect()
    except Exception:
        pass
    
    print("🛑 DocVault AI Backend shutting down")

@app.get("/")
async def root():
    """Root endpoint - API information."""
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
    try:
        # Check database connectivity
        from .routers.dependencies import db_service
        if db_service is None:
            from fastapi import Response
            return Response(
                content='{"status": "unhealthy", "reason": "Database not initialized"}',
                media_type="application/json",
                status_code=503
            )
        
        # Check if services are initialized
        from .routers.dependencies import upload_service, search_service
        if upload_service is None or search_service is None:
            from fastapi import Response
            return Response(
                content='{"status": "unhealthy", "reason": "Services not initialized"}',
                media_type="application/json",
                status_code=503
            )
        
        return {
            "status": "healthy",
            "database": "connected",
            "services": "initialized"
        }
    except Exception as e:
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
    try:
        from .routers.dependencies import db_service
        if db_service is None:
            from fastapi import Response
            return Response(
                content='{"ready": false, "reason": "Database not initialized"}',
                media_type="application/json",
                status_code=503
            )
        
        # Try a simple database operation to verify connectivity
        await db_service.get_all_documents(limit=1)
        
        return {"ready": True}
    except Exception as e:
        from fastapi import Response
        return Response(
            content=f'{{"ready": false, "reason": "{str(e)}"}}',
            media_type="application/json",
            status_code=503
        )
