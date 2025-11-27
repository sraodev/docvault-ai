"""
AWS S3 storage adapter implementing FileStorageInterface.
Stores files in AWS S3 - perfect for production deployments.
"""
import asyncio
from typing import Optional
from fastapi import UploadFile
import boto3
from botocore.exceptions import ClientError
from botocore.config import Config

from .base import FileStorageInterface

class S3FileStorage(FileStorageInterface):
    """
    AWS S3 storage adapter.
    Stores files in S3 buckets - perfect for production deployments.
    """
    
    def __init__(
        self,
        bucket_name: str,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        region_name: str = "us-east-1",
        endpoint_url: Optional[str] = None  # For S3-compatible services (MinIO, etc.)
    ):
        """
        Initialize S3 storage.
        
        Args:
            bucket_name: S3 bucket name
            aws_access_key_id: AWS access key (or use IAM role)
            aws_secret_access_key: AWS secret key (or use IAM role)
            region_name: AWS region
            endpoint_url: Optional custom endpoint (for S3-compatible services)
        """
        self.bucket_name = bucket_name
        self.region_name = region_name
        
        # Initialize S3 client
        config = Config(
            signature_version='s3v4',
            retries={'max_attempts': 3}
        )
        
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region_name,
            endpoint_url=endpoint_url,
            config=config
        )
    
    async def initialize(self):
        """Initialize storage - verify bucket exists and is accessible."""
        try:
            # Check if bucket exists and is accessible
            self.s3_client.head_bucket(Bucket=self.bucket_name)
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == '404':
                raise ValueError(f"S3 bucket '{self.bucket_name}' does not exist")
            elif error_code == '403':
                raise ValueError(f"Access denied to S3 bucket '{self.bucket_name}'")
            else:
                raise ValueError(f"Error accessing S3 bucket: {e}")
    
    async def close(self):
        """Close storage connection (no-op for boto3, but included for interface)."""
        pass
    
    async def save_file(self, file: UploadFile, file_path: str) -> str:
        """Save an uploaded file to S3."""
        # Reset file pointer to beginning
        await file.seek(0)
        
        def _upload():
            self.s3_client.upload_fileobj(
                file.file,
                self.bucket_name,
                file_path,
                ExtraArgs={'ContentType': file.content_type or 'application/octet-stream'}
            )
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _upload)
        
        return file_path
    
    async def get_file(self, file_path: str) -> bytes:
        """Retrieve a file from S3."""
        def _download():
            try:
                response = self.s3_client.get_object(Bucket=self.bucket_name, Key=file_path)
                return response['Body'].read()
            except ClientError as e:
                if e.response['Error']['Code'] == 'NoSuchKey':
                    raise FileNotFoundError(f"File not found in S3: {file_path}")
                raise
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _download)
    
    async def delete_file(self, file_path: str) -> bool:
        """Delete a file from S3."""
        def _delete():
            try:
                self.s3_client.delete_object(Bucket=self.bucket_name, Key=file_path)
                return True
            except ClientError as e:
                if e.response['Error']['Code'] == 'NoSuchKey':
                    return False
                raise
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _delete)
    
    async def file_exists(self, file_path: str) -> bool:
        """Check if a file exists in S3."""
        def _check():
            try:
                self.s3_client.head_object(Bucket=self.bucket_name, Key=file_path)
                return True
            except ClientError as e:
                if e.response['Error']['Code'] == '404':
                    return False
                raise
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _check)
    
    async def get_file_url(self, file_path: str, expires_in: Optional[int] = 3600) -> str:
        """
        Get a presigned URL to access the file.
        
        Args:
            file_path: S3 key of the file
            expires_in: URL expiration time in seconds (default: 1 hour)
        
        Returns:
            Presigned URL string
        """
        def _generate_url():
            return self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': file_path},
                ExpiresIn=expires_in or 3600
            )
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _generate_url)
    
    async def save_text(self, content: str, file_path: str) -> str:
        """Save text content to S3."""
        def _upload():
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=file_path,
                Body=content.encode('utf-8'),
                ContentType='text/plain; charset=utf-8'
            )
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _upload)
        
        return file_path
    
    async def get_text(self, file_path: str) -> str:
        """Retrieve text content from S3."""
        file_bytes = await self.get_file(file_path)
        return file_bytes.decode('utf-8')

