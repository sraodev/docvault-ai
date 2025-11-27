"""
Supabase Storage adapter implementing FileStorageInterface.
Stores files in Supabase Storage - perfect for production deployments.
"""
import asyncio
from typing import Optional
from fastapi import UploadFile
from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions

from .base import FileStorageInterface

class SupabaseFileStorage(FileStorageInterface):
    """
    Supabase Storage adapter.
    Stores files in Supabase Storage buckets - perfect for production deployments.
    """
    
    def __init__(
        self,
        supabase_url: str,
        supabase_key: str,
        bucket_name: str
    ):
        """
        Initialize Supabase storage.
        
        Args:
            supabase_url: Supabase project URL
            supabase_key: Supabase service role key (or anon key with proper RLS)
            bucket_name: Supabase Storage bucket name
        """
        self.bucket_name = bucket_name
        
        # Initialize Supabase client
        self.supabase: Client = create_client(
            supabase_url,
            supabase_key,
            options=ClientOptions(
                auto_refresh_token=True,
                persist_session=False
            )
        )
    
    async def initialize(self):
        """Initialize storage - verify bucket exists and is accessible."""
        try:
            # Check if bucket exists
            buckets = self.supabase.storage.list_buckets()
            bucket_names = [b.name for b in buckets]
            
            if self.bucket_name not in bucket_names:
                raise ValueError(
                    f"Supabase Storage bucket '{self.bucket_name}' does not exist. "
                    f"Available buckets: {bucket_names}"
                )
        except Exception as e:
            raise ValueError(f"Error accessing Supabase Storage: {e}")
    
    async def close(self):
        """Close storage connection (no-op for Supabase, but included for interface)."""
        pass
    
    async def save_file(self, file: UploadFile, file_path: str) -> str:
        """Save an uploaded file to Supabase Storage."""
        # Reset file pointer to beginning
        await file.seek(0)
        
        # Read file content
        file_content = await file.read()
        
        def _upload():
            response = self.supabase.storage.from_(self.bucket_name).upload(
                path=file_path,
                file=file_content,
                file_options={
                    "content-type": file.content_type or "application/octet-stream",
                    "upsert": True  # Overwrite if exists
                }
            )
            return response
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _upload)
        
        return file_path
    
    async def get_file(self, file_path: str) -> bytes:
        """Retrieve a file from Supabase Storage."""
        def _download():
            try:
                response = self.supabase.storage.from_(self.bucket_name).download(file_path)
                return response
            except Exception as e:
                if "not found" in str(e).lower() or "404" in str(e):
                    raise FileNotFoundError(f"File not found in Supabase Storage: {file_path}")
                raise
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _download)
    
    async def delete_file(self, file_path: str) -> bool:
        """Delete a file from Supabase Storage."""
        def _delete():
            try:
                response = self.supabase.storage.from_(self.bucket_name).remove([file_path])
                # Supabase returns list of deleted paths
                return file_path in response
            except Exception as e:
                if "not found" in str(e).lower():
                    return False
                raise
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _delete)
    
    async def file_exists(self, file_path: str) -> bool:
        """Check if a file exists in Supabase Storage."""
        def _check():
            try:
                # Try to get file info
                files = self.supabase.storage.from_(self.bucket_name).list(file_path)
                # If path is a file, check if it exists
                if files:
                    return any(f.name == file_path.split('/')[-1] for f in files)
                return False
            except Exception:
                # If error, file doesn't exist
                return False
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _check)
    
    async def get_file_url(self, file_path: str, expires_in: Optional[int] = 3600) -> str:
        """
        Get a signed URL to access the file.
        
        Args:
            file_path: Storage path of the file
            expires_in: URL expiration time in seconds (default: 1 hour)
        
        Returns:
            Signed URL string
        """
        def _generate_url():
            try:
                response = self.supabase.storage.from_(self.bucket_name).create_signed_url(
                    path=file_path,
                    expires_in=expires_in or 3600
                )
                return response.get('signedURL', '')
            except Exception as e:
                raise ValueError(f"Error generating Supabase signed URL: {e}")
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _generate_url)
    
    async def save_text(self, content: str, file_path: str) -> str:
        """Save text content to Supabase Storage."""
        def _upload():
            response = self.supabase.storage.from_(self.bucket_name).upload(
                path=file_path,
                file=content.encode('utf-8'),
                file_options={
                    "content-type": "text/plain; charset=utf-8",
                    "upsert": True
                }
            )
            return response
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _upload)
        
        return file_path
    
    async def get_text(self, file_path: str) -> str:
        """Retrieve text content from Supabase Storage."""
        file_bytes = await self.get_file(file_path)
        return file_bytes.decode('utf-8')

