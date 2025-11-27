from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import documents
from .core.config import UPLOAD_DIR, DATABASE_TYPE

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(documents.router)

@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    UPLOAD_DIR.mkdir(exist_ok=True)
    
    # Initialize database adapter (plug-and-play)
    print(f"🔌 Initializing database: {DATABASE_TYPE}")
    await documents.initialize_database()
    print(f"✅ Database initialized: {DATABASE_TYPE}")
    
    # JSON and Memory databases don't need migrations
    if DATABASE_TYPE.lower() == "json":
        print("ℹ️  JSON database: No migrations needed (file-based JSON storage)")
    elif DATABASE_TYPE.lower() == "memory":
        print("ℹ️  Memory database: No migrations needed (in-memory, no persistence)")

@app.get("/")
async def root():
    return {"message": "DocVault AI Backend is running"}
