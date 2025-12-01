import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables (only in development)
# In containers, environment variables are set directly
if os.getenv("ENVIRONMENT") != "production":
    load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Upload directory - can be overridden by environment variable
UPLOAD_DIR_STR = os.getenv("UPLOAD_DIR", str(BASE_DIR / "uploads"))
UPLOAD_DIR = Path(UPLOAD_DIR_STR)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Database path for persistent storage
DB_DIR_STR = os.getenv("DB_DIR", str(BASE_DIR / "data"))
DB_DIR = Path(DB_DIR_STR)
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / "docvault.db"

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
AI_PROVIDER = os.getenv("AI_PROVIDER", "openrouter")

# Database configuration
DATABASE_TYPE = os.getenv("DATABASE_TYPE", "scalable_json")  # Options: 'json', 'scalable_json', 'memory'

# JSON database configuration
JSON_DB_PATH = os.getenv("JSON_DB_PATH")  # Path to JSON database directory

# File Storage configuration
STORAGE_TYPE = os.getenv("STORAGE_TYPE", "local")  # Options: 'local', 's3', 'supabase'

# Local storage configuration
LOCAL_STORAGE_DIR = os.getenv("LOCAL_STORAGE_DIR")  # Path to local storage directory

# S3 storage configuration
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL")  # For S3-compatible services (MinIO, etc.)

# Supabase Storage configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_STORAGE_BUCKET = os.getenv("SUPABASE_STORAGE_BUCKET", "files")

# Redis/Cache configuration (for million+ user scale)
REDIS_URL = os.getenv("REDIS_URL")  # Full Redis URL (redis://host:port)
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_CLUSTER_MODE = os.getenv("REDIS_CLUSTER_MODE", "false").lower() == "true"

# Message Queue configuration (Celery)
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")

# Rate Limiting
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "100"))
RATE_LIMIT_PER_HOUR = int(os.getenv("RATE_LIMIT_PER_HOUR", "1000"))

# Performance tuning
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "4"))
WORKER_CONNECTIONS = int(os.getenv("WORKER_CONNECTIONS", "1000"))
KEEP_ALIVE_TIMEOUT = int(os.getenv("KEEP_ALIVE_TIMEOUT", "65"))

# CDN Configuration
CDN_URL = os.getenv("CDN_URL")  # CDN URL for static assets
CDN_ENABLED = os.getenv("CDN_ENABLED", "false").lower() == "true"
