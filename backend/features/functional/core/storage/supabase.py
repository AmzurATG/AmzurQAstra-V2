"""
Supabase Storage Adapter

Stores files in Supabase Storage buckets.
"""
import uuid
import httpx
from pathlib import Path
from typing import Optional
from datetime import datetime

from .base import StorageAdapter, StorageFile


class SupabaseStorageAdapter(StorageAdapter):
    """
    Supabase Storage adapter.
    
    Uses Supabase Storage API to store files in buckets.
    """
    
    def __init__(
        self,
        url: str,
        key: str,
        bucket_name: str,
        prefix: str = "",
    ):
        """
        Initialize Supabase storage adapter.
        
        Args:
            url: Supabase project URL
            key: Supabase service role key or anon key
            bucket_name: Storage bucket name
            prefix: Optional prefix for all stored files
        """
        self.url = url.rstrip("/")
        self.key = key
        self.bucket_name = bucket_name
        self.prefix = prefix.strip("/")
        self.storage_url = f"{self.url}/storage/v1"
        
        self._headers = {
            "Authorization": f"Bearer {key}",
            "apikey": key,
        }
    
    def _get_full_path(self, path: str) -> str:
        """Get full storage path from relative path."""
        if self.prefix:
            return f"{self.prefix}/{path}"
        return path
    
    def _generate_unique_filename(self, original_filename: str) -> str:
        """Generate a unique filename while preserving extension."""
        ext = Path(original_filename).suffix
        return f"{uuid.uuid4()}{ext}"
    
    async def save(
        self,
        file_content: bytes,
        filename: str,
        content_type: str,
        subdirectory: Optional[str] = None,
    ) -> StorageFile:
        """Save file to Supabase Storage."""
        # Build path
        unique_filename = self._generate_unique_filename(filename)
        relative_path = unique_filename
        if subdirectory:
            relative_path = f"{subdirectory}/{unique_filename}"
        
        full_path = self._get_full_path(relative_path)
        
        # Upload to Supabase Storage
        upload_url = f"{self.storage_url}/object/{self.bucket_name}/{full_path}"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                upload_url,
                headers={
                    **self._headers,
                    "Content-Type": content_type,
                    "x-upsert": "true",  # Overwrite if exists
                },
                content=file_content,
            )
            response.raise_for_status()
        
        # Build public URL
        storage_url = f"{self.storage_url}/object/public/{self.bucket_name}/{full_path}"
        
        return StorageFile(
            path=relative_path,
            filename=filename,
            content_type=content_type,
            size=len(file_content),
            storage_url=storage_url,
            created_at=datetime.utcnow(),
        )
    
    async def delete(self, path: str) -> bool:
        """Delete file from Supabase Storage."""
        full_path = self._get_full_path(path)
        delete_url = f"{self.storage_url}/object/{self.bucket_name}"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    delete_url,
                    headers=self._headers,
                    json={"prefixes": [full_path]},
                )
                return response.status_code in (200, 204)
        except Exception:
            return False
    
    async def get(self, path: str) -> Optional[bytes]:
        """Get file content from Supabase Storage."""
        full_path = self._get_full_path(path)
        download_url = f"{self.storage_url}/object/{self.bucket_name}/{full_path}"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    download_url,
                    headers=self._headers,
                )
                if response.status_code == 200:
                    return response.content
                return None
        except Exception:
            return None
    
    async def exists(self, path: str) -> bool:
        """Check if file exists in Supabase Storage."""
        full_path = self._get_full_path(path)
        # Use list to check existence
        list_url = f"{self.storage_url}/object/list/{self.bucket_name}"
        
        try:
            # Parse path to get folder and filename
            path_parts = full_path.rsplit("/", 1)
            prefix = path_parts[0] if len(path_parts) > 1 else ""
            filename = path_parts[-1]
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    list_url,
                    headers=self._headers,
                    json={
                        "prefix": prefix,
                        "search": filename,
                        "limit": 1,
                    },
                )
                if response.status_code == 200:
                    data = response.json()
                    return len(data) > 0
                return False
        except Exception:
            return False
    
    async def get_url(self, path: str, expires_in: int = 3600) -> Optional[str]:
        """Get signed URL for file access."""
        full_path = self._get_full_path(path)
        sign_url = f"{self.storage_url}/object/sign/{self.bucket_name}/{full_path}"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    sign_url,
                    headers=self._headers,
                    json={"expiresIn": expires_in},
                )
                if response.status_code == 200:
                    data = response.json()
                    signed_url = data.get("signedURL")
                    if signed_url:
                        return f"{self.url}{signed_url}"
                return None
        except Exception:
            return None
    
    async def list_files(
        self,
        prefix: Optional[str] = None,
        limit: int = 100,
    ) -> list[StorageFile]:
        """List files in Supabase Storage bucket."""
        search_prefix = self.prefix
        if prefix:
            search_prefix = f"{self.prefix}/{prefix}" if self.prefix else prefix
        
        list_url = f"{self.storage_url}/object/list/{self.bucket_name}"
        
        files: list[StorageFile] = []
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    list_url,
                    headers=self._headers,
                    json={
                        "prefix": search_prefix,
                        "limit": limit,
                    },
                )
                
                if response.status_code == 200:
                    data = response.json()
                    for item in data:
                        if item.get("id"):  # It's a file, not a folder
                            name = item.get("name", "")
                            relative_path = name
                            if search_prefix:
                                relative_path = f"{search_prefix}/{name}"
                            if self.prefix:
                                relative_path = relative_path[len(self.prefix) + 1:]
                            
                            files.append(StorageFile(
                                path=relative_path,
                                filename=name,
                                content_type=item.get("metadata", {}).get(
                                    "mimetype", "application/octet-stream"
                                ),
                                size=item.get("metadata", {}).get("size", 0),
                                created_at=datetime.fromisoformat(
                                    item.get("created_at", "").replace("Z", "+00:00")
                                ) if item.get("created_at") else None,
                            ))
        except Exception:
            pass
        
        return files
