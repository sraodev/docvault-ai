from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import documents
from .core.config import UPLOAD_DIR

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
    UPLOAD_DIR.mkdir(exist_ok=True)

@app.get("/")
async def root():
    return {"message": "DocVault AI Backend is running"}
