import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# Database path for persistent storage
DB_DIR = BASE_DIR / "data"
DB_DIR.mkdir(exist_ok=True)
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
