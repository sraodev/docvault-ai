"""
File service implementation.
Handles file operations using plug-and-play storage adapters.
Supports local filesystem, S3, and Supabase Storage.
"""
from pathlib import Path
from fastapi import UploadFile, HTTPException, status
from pypdf import PdfReader
from .interfaces import IFileService
from .storage import FileStorageFactory, FileStorageInterface
from ..core.config import STORAGE_TYPE, LOCAL_STORAGE_DIR, S3_BUCKET_NAME, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION, S3_ENDPOINT_URL, SUPABASE_URL, SUPABASE_KEY, SUPABASE_STORAGE_BUCKET

class FileService(IFileService):
    """
    File service implementation.
    Handles file operations - saving, reading, deleting files.
    Uses plug-and-play storage adapters (local, S3, Supabase).
    Follows Single Responsibility Principle.
    """
    
    def __init__(self, storage: FileStorageInterface = None):
        """
        Initialize file service with storage adapter.
        
        Args:
            storage: FileStorageInterface instance (if None, will be created from config)
        """
        self._storage: FileStorageInterface = storage
    
    @property
    async def storage(self) -> FileStorageInterface:
        """Get storage adapter (lazy initialization)."""
        if self._storage is None:
            self._storage = await self._create_storage()
        return self._storage
    
    async def _create_storage(self) -> FileStorageInterface:
        """Create storage adapter based on configuration."""
        if STORAGE_TYPE.lower() == "local":
            base_dir = Path(LOCAL_STORAGE_DIR) if LOCAL_STORAGE_DIR else None
            return await FileStorageFactory.create_and_initialize("local", base_dir=base_dir)
        elif STORAGE_TYPE.lower() == "s3":
            return await FileStorageFactory.create_and_initialize(
                "s3",
                bucket_name=S3_BUCKET_NAME,
                aws_access_key_id=AWS_ACCESS_KEY_ID,
                aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                region_name=AWS_REGION,
                endpoint_url=S3_ENDPOINT_URL
            )
        elif STORAGE_TYPE.lower() == "supabase":
            return await FileStorageFactory.create_and_initialize(
                "supabase",
                supabase_url=SUPABASE_URL,
                supabase_key=SUPABASE_KEY,
                bucket_name=SUPABASE_STORAGE_BUCKET
            )
        else:
            raise ValueError(f"Unsupported STORAGE_TYPE: {STORAGE_TYPE}")
    
    async def save_upload(self, file: UploadFile, destination: Path) -> None:
        """
        Save uploaded file using storage adapter.
        
        Args:
            file: FastAPI UploadFile object
            destination: Path where file should be stored (relative to storage root)
        """
        try:
            storage_adapter = await self.storage
            # Convert Path to string for storage adapter
            file_path = str(destination)
            await storage_adapter.save_file(file, file_path)
        except Exception as e:
            print(f"Error saving upload: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Could not save file: {str(e)}"
            )
    
    async def extract_text(self, file_path: Path) -> str:
        """
        Extract text from file using storage adapter.
        
        Args:
            file_path: Storage path of the file
        
        Returns:
            Extracted text content
        """
        try:
            storage_adapter = await self.storage
            file_path_str = str(file_path)
            
            # Check if file exists
            if not await storage_adapter.file_exists(file_path_str):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="File not found for extraction"
                )
            
            # Get file content
            file_bytes = await storage_adapter.get_file(file_path_str)
            
            # Extract text based on file type
            if file_path.suffix.lower() == ".pdf":
                try:
                    # For PDF, we need to save temporarily to extract text
                    # (pypdf needs a file-like object)
                    import tempfile
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                        tmp_file.write(file_bytes)
                        tmp_path = Path(tmp_file.name)
                    
                    try:
                        reader = PdfReader(tmp_path)
                        text_content = ""
                        for page in reader.pages:
                            text_content += page.extract_text() + "\n"
                        return text_content
                    finally:
                        # Clean up temp file
                        tmp_path.unlink()
                except Exception as e:
                    print(f"Error reading PDF: {e}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Error extracting text from PDF: {str(e)}"
                    )
            else:
                # Assume text/md file
                try:
                    return file_bytes.decode('utf-8', errors='ignore')
                except Exception as e:
                    print(f"Error reading text file: {e}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Error reading text file: {str(e)}"
                    )
        except HTTPException:
            raise
        except Exception as e:
            print(f"General file error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error processing file: {str(e)}"
            )
    
    async def delete_file(self, file_path: Path) -> None:
        """
        Delete a file using storage adapter.
        
        Args:
            file_path: Storage path of the file to delete
        """
        try:
            storage_adapter = await self.storage
            file_path_str = str(file_path)
            await storage_adapter.delete_file(file_path_str)
        except Exception as e:
            print(f"Error deleting file {file_path}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Could not delete file: {str(e)}"
            )
    
    async def save_markdown(self, content: str, destination: Path) -> None:
        """
        Save markdown content using storage adapter.
        
        Args:
            content: Markdown content to save
            destination: Storage path where content should be saved
        """
        try:
            storage_adapter = await self.storage
            file_path = str(destination)
            await storage_adapter.save_text(content, file_path)
        except Exception as e:
            print(f"Error saving markdown: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Could not save markdown: {str(e)}"
            )
    
    async def get_file_url(self, file_path: Path, expires_in: int = 3600) -> str:
        """
        Get a URL to access the file (for direct download/viewing).
        
        Args:
            file_path: Storage path of the file
            expires_in: URL expiration time in seconds (for signed URLs)
        
        Returns:
            URL string for accessing the file
        """
        storage_adapter = await self.storage
        file_path_str = str(file_path)
        return await storage_adapter.get_file_url(file_path_str, expires_in=expires_in)
