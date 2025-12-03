"""
Shared dependencies for routers.
Provides database and service initialization.

This module manages service lifecycle and dependency injection
for million+ user scale with caching and async processing.
"""
from ..services.database import DatabaseFactory
from ..services.ai_service import AIService
from ..services.file_service import FileService
from ..services.upload_service import UploadService
from ..services.document_processing_service import DocumentProcessingService
from ..services.search_service import SearchService
from ..core.config import DATABASE_TYPE, JSON_DB_PATH
from pathlib import Path

from ..core.logging_config import get_logger

logger = get_logger(__name__)

# Optional cache service import (requires aioredis)
try:
    from ..services.cache_service import CacheService
    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False
    CacheService = None

# Global services (will be initialized on startup)
# These are shared across all request handlers for efficiency
db_service = None
ai_service = None
file_service = None
upload_service = None
document_processing_service = None
search_service = None
cache_service = None  # Redis cache for million+ user scale


async def initialize_database():
    """Initialize database adapter based on configuration."""
    global db_service
    
    logger.info(f"Initializing database: {DATABASE_TYPE}")
    
    if DATABASE_TYPE.lower() == "json":
        data_dir = Path(JSON_DB_PATH) if JSON_DB_PATH else None
        logger.info(f"  → Database Type: JSON (file-based, legacy)")
        logger.debug(f"  → Database Path: {data_dir}")
        db_service = await DatabaseFactory.create_and_initialize("json", data_dir=data_dir)
        logger.info("  ✅ JSON Database initialized")
    elif DATABASE_TYPE.lower() == "scalable_json":
        data_dir = Path(JSON_DB_PATH) if JSON_DB_PATH else None
        logger.info(f"  → Database Type: Scalable JSON (shard-based, scalable to 500K+ records)")
        logger.debug(f"  → Database Path: {data_dir}")
        db_service = await DatabaseFactory.create_and_initialize("scalable_json", data_dir=data_dir)
        logger.info("  ✅ Scalable JSON Database initialized")
    elif DATABASE_TYPE.lower() == "memory":
        logger.info("  → Database Type: Memory (in-memory, non-persistent)")
        db_service = await DatabaseFactory.create_and_initialize("memory")
        logger.info("  ✅ Memory Database initialized")
    else:
        raise ValueError(f"Unsupported DATABASE_TYPE: {DATABASE_TYPE}. Supported types: 'json', 'scalable_json', 'memory'")


async def initialize_services():
    """
    Initialize all services after database is ready.
    
    This function sets up all business logic services including:
    - AI service for document processing
    - File service for storage operations
    - Upload service for file uploads
    - Document processing service for AI operations
    - Search service for semantic search
    - Cache service for Redis caching (million+ user scale)
    """
    global ai_service, file_service, upload_service, document_processing_service, search_service, cache_service
    
    if db_service is None:
        await initialize_database()
    
    logger.info("Initializing services...")
    
    # Initialize core services
    logger.info("  → Starting AI Service...")
    from ..core.config import AI_PROVIDER
    logger.info(f"    → Provider: {AI_PROVIDER}")
    ai_service = AIService()
    logger.info("  ✅ AI Service initialized")
    
    logger.info("  → Starting File Service...")
    from ..core.config import STORAGE_TYPE
    logger.info(f"    → Storage Type: {STORAGE_TYPE}")
    file_service = FileService()
    logger.info("  ✅ File Service initialized")
    
    # Initialize cache service (Redis) for high-performance caching
    # This is critical for million+ user scale
    logger.info("  → Starting Cache Service (Redis)...")
    if CACHE_AVAILABLE and CacheService is not None:
        try:
            cache_service = CacheService()
            await cache_service.connect()
            logger.info("  ✅ Cache Service (Redis) connected successfully")
        except Exception as e:
            logger.warning(f"  ⚠️  Cache Service not available (continuing without cache): {e}")
            cache_service = None
    else:
        logger.warning("  ⚠️  Cache Service not available (aioredis not installed, continuing without cache)")
        cache_service = None
    
    # Initialize business logic services
    logger.info("  → Starting Upload Service...")
    upload_service = UploadService(file_service, db_service)
    logger.info("  ✅ Upload Service initialized")
    
    logger.info("  → Starting Document Processing Service...")
    document_processing_service = DocumentProcessingService(ai_service, file_service, db_service)
    logger.info("  ✅ Document Processing Service initialized")
    
    logger.info("  → Starting Search Service...")
    search_service = SearchService(ai_service, db_service)
    logger.info("  ✅ Search Service initialized")
    
    # Summary
    services_started = [
        "Database Service",
        "AI Service",
        "File Service",
        "Upload Service",
        "Document Processing Service",
        "Search Service"
    ]
    if cache_service:
        services_started.append("Cache Service (Redis)")
    
    logger.info(f"✅ All services initialized successfully ({len(services_started)} services)")
    logger.info(f"   Services started: {', '.join(services_started)}")


def get_db_service():
    """Get database service (dependency injection)."""
    if db_service is None:
        raise RuntimeError("Database service not initialized")
    return db_service


def get_upload_service():
    """Get upload service (dependency injection)."""
    if upload_service is None:
        raise RuntimeError("Upload service not initialized")
    return upload_service


def get_document_processing_service():
    """Get document processing service (dependency injection)."""
    if document_processing_service is None:
        raise RuntimeError("Document processing service not initialized")
    return document_processing_service


def get_search_service():
    """Get search service (dependency injection)."""
    if search_service is None:
        raise RuntimeError("Search service not initialized")
    return search_service


def get_file_service():
    """Get file service (dependency injection)."""
    if file_service is None:
        raise RuntimeError("File service not initialized")
    return file_service


def get_cache_service():
    """
    Get cache service (dependency injection).
    
    Returns Redis cache service for high-performance caching.
    Essential for million+ user scale.
    """
    if cache_service is None:
        # Cache is optional - return None if not available
        return None
    return cache_service

