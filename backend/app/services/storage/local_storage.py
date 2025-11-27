"""
Local filesystem storage adapter implementing FileStorageInterface.
Stores files on the local filesystem - perfect for development and demos.
"""
import shutil
import asyncio
from pathlib import Path
from typing import Optional
from fastapi import UploadFile
from urllib.parse import quote

from .base import FileStorageInterface

class LocalFileStorage(FileStorageInterface):
    """
    Local filesystem storage adapter.
    Stores files in a local directory - perfect for development and demos.
    """
    
    def __init__(self, base_dir: Optional[Path] = None):
        """
        Initialize local file storage.
        
        Args:
            base_dir: Base directory for file storage (defaults to backend/uploads)
        """
        if base_dir is None:
            # Default to backend/uploads
            from ...core.config import BASE_DIR
            base_dir = BASE_DIR / "uploads"
        
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    async def initialize(self):
        """Initialize storage - ensure base directory exists."""
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    async def close(self):
        """Close storage (no-op for local filesystem)."""
        pass
    
    def _get_full_path(self, file_path: str) -> Path:
        """Get full filesystem path from storage path."""
        # Normalize path to prevent directory traversal
        normalized = Path(file_path).as_posix().lstrip('/')
        return self.base_dir / normalized
    
    async def save_file(self, file: UploadFile, file_path: str) -> str:
        """Save an uploaded file to local filesystem."""
        full_path = self._get_full_path(file_path)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        def _save():
            with open(full_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        
        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _save)
        
        return file_path
    
    async def get_file(self, file_path: str) -> bytes:
        """Retrieve a file from local filesystem."""
        full_path = self._get_full_path(file_path)
        
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        def _read():
            return full_path.read_bytes()
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _read)
    
    async def delete_file(self, file_path: str) -> bool:
        """Delete a file from local filesystem."""
        full_path = self._get_full_path(file_path)
        
        if not full_path.exists():
            return False
        
        def _delete():
            full_path.unlink()
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _delete)
        return True
    
    async def file_exists(self, file_path: str) -> bool:
        """Check if a file exists in local filesystem."""
        full_path = self._get_full_path(file_path)
        return full_path.exists()
    
    async def get_file_url(self, file_path: str, expires_in: Optional[int] = None) -> str:
        """
        Get a URL to access the file.
        For local storage, returns a relative path that can be served by FastAPI.
        """
        # Return relative path that can be used with FastAPI FileResponse
        # The router will handle serving the file
        return f"/files/{quote(file_path)}"
    
    async def save_text(self, content: str, file_path: str) -> str:
        """Save text content to local filesystem."""
        full_path = self._get_full_path(file_path)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        def _save():
            full_path.write_text(content, encoding="utf-8")
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _save)
        
        return file_path
    
    async def get_text(self, file_path: str) -> str:
        """Retrieve text content from local filesystem."""
        full_path = self._get_full_path(file_path)
        
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        def _read():
            return full_path.read_text(encoding="utf-8")
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _read)

