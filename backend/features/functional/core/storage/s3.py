"""
AWS S3 Storage Adapter

Stores files in AWS S3 buckets. Supports both AWS S3 and S3-compatible
services (MinIO, DigitalOcean Spaces, etc.).
"""
import uuid
from pathlib import Path
from typing import Optional
from datetime import datetime

from .base import StorageAdapter, StorageFile


class S3StorageAdapter(StorageAdapter):
    """
    AWS S3 storage adapter.
    
    Supports AWS S3 and S3-compatible services like MinIO, 
    DigitalOcean Spaces, Backblaze B2, etc.
    """
    
    def __init__(
        self,
        bucket_name: str,
        region: str = "us-east-1",
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        prefix: str = "",
    ):
        """
        Initialize S3 storage adapter.
        
        Args:
            bucket_name: S3 bucket name
            region: AWS region
            access_key_id: AWS access key (uses default credentials if not provided)
            secret_access_key: AWS secret key
            endpoint_url: Custom endpoint for S3-compatible services
            prefix: Optional prefix for all stored files (e.g., "uploads/")
        """
        self.bucket_name = bucket_name
        self.region = region
        self.endpoint_url = endpoint_url
        self.prefix = prefix.strip("/")
        
        # Import boto3 lazily to avoid dependency issues
        try:
            import aioboto3
            self._aioboto3 = aioboto3
        except ImportError:
            raise ImportError(
                "aioboto3 is required for S3 storage. "
                "Install with: pip install aioboto3"
            )
        
        # Session configuration
        self._session_config = {
            "region_name": region,
        }
        if access_key_id and secret_access_key:
            self._session_config["aws_access_key_id"] = access_key_id
            self._session_config["aws_secret_access_key"] = secret_access_key
        
        self._client_config = {}
        if endpoint_url:
            self._client_config["endpoint_url"] = endpoint_url
    
    def _get_full_key(self, path: str) -> str:
        """Get full S3 key from relative path."""
        if self.prefix:
            return f"{self.prefix}/{path}"
        return path
    
    def _generate_unique_filename(self, original_filename: str) -> str:
        """Generate a unique filename while preserving extension."""
        ext = Path(original_filename).suffix
        return f"{uuid.uuid4()}{ext}"
    
    async def _get_client(self):
        """Get S3 client context manager."""
        session = self._aioboto3.Session(**self._session_config)
        return session.client("s3", **self._client_config)
    
    async def save(
        self,
        file_content: bytes,
        filename: str,
        content_type: str,
        subdirectory: Optional[str] = None,
    ) -> StorageFile:
        """Save file to S3."""
        # Build key
        unique_filename = self._generate_unique_filename(filename)
        relative_path = unique_filename
        if subdirectory:
            relative_path = f"{subdirectory}/{unique_filename}"
        
        full_key = self._get_full_key(relative_path)
        
        # Upload to S3
        async with await self._get_client() as client:
            await client.put_object(
                Bucket=self.bucket_name,
                Key=full_key,
                Body=file_content,
                ContentType=content_type,
                Metadata={
                    "original_filename": filename,
                },
            )
            
            # Get URL
            if self.endpoint_url:
                storage_url = f"{self.endpoint_url}/{self.bucket_name}/{full_key}"
            else:
                storage_url = f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{full_key}"
        
        return StorageFile(
            path=relative_path,
            filename=filename,
            content_type=content_type,
            size=len(file_content),
            storage_url=storage_url,
            created_at=datetime.utcnow(),
        )
    
    async def delete(self, path: str) -> bool:
        """Delete file from S3."""
        full_key = self._get_full_key(path)
        
        try:
            async with await self._get_client() as client:
                await client.delete_object(
                    Bucket=self.bucket_name,
                    Key=full_key,
                )
            return True
        except Exception:
            return False
    
    async def get(self, path: str) -> Optional[bytes]:
        """Get file content from S3."""
        full_key = self._get_full_key(path)
        
        try:
            async with await self._get_client() as client:
                response = await client.get_object(
                    Bucket=self.bucket_name,
                    Key=full_key,
                )
                return await response["Body"].read()
        except Exception:
            return None
    
    async def exists(self, path: str) -> bool:
        """Check if file exists in S3."""
        full_key = self._get_full_key(path)
        
        try:
            async with await self._get_client() as client:
                await client.head_object(
                    Bucket=self.bucket_name,
                    Key=full_key,
                )
            return True
        except Exception:
            return False
    
    async def get_url(self, path: str, expires_in: int = 3600) -> Optional[str]:
        """Get presigned URL for file access."""
        full_key = self._get_full_key(path)
        
        try:
            async with await self._get_client() as client:
                url = await client.generate_presigned_url(
                    "get_object",
                    Params={
                        "Bucket": self.bucket_name,
                        "Key": full_key,
                    },
                    ExpiresIn=expires_in,
                )
            return url
        except Exception:
            return None
    
    async def list_files(
        self,
        prefix: Optional[str] = None,
        limit: int = 100,
    ) -> list[StorageFile]:
        """List files in S3 bucket."""
        search_prefix = self.prefix
        if prefix:
            search_prefix = f"{self.prefix}/{prefix}" if self.prefix else prefix
        
        files: list[StorageFile] = []
        
        try:
            async with await self._get_client() as client:
                paginator = client.get_paginator("list_objects_v2")
                
                async for page in paginator.paginate(
                    Bucket=self.bucket_name,
                    Prefix=search_prefix,
                    MaxKeys=limit,
                ):
                    for obj in page.get("Contents", []):
                        key = obj["Key"]
                        # Remove prefix to get relative path
                        relative_path = key
                        if self.prefix:
                            relative_path = key[len(self.prefix) + 1:]
                        
                        files.append(StorageFile(
                            path=relative_path,
                            filename=Path(key).name,
                            content_type=self._guess_content_type(key),
                            size=obj["Size"],
                            created_at=obj.get("LastModified"),
                        ))
                        
                        if len(files) >= limit:
                            return files
        except Exception:
            pass
        
        return files
    
    def _guess_content_type(self, filename: str) -> str:
        """Guess content type from filename extension."""
        import mimetypes
        mime_type, _ = mimetypes.guess_type(filename)
        return mime_type or "application/octet-stream"
