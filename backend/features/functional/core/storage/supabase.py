"""
Supabase Storage Adapter

Stores files in Supabase Storage buckets.
Uses urllib (stdlib) for HTTP calls via asyncio.to_thread to avoid
httpx async/sync transport detection issues.
"""
import asyncio
import json as json_mod
import logging
import uuid
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional
from datetime import datetime

from .base import StorageAdapter, StorageFile

logger = logging.getLogger(__name__)


def _urllib_request(
    url: str,
    *,
    method: str = "GET",
    headers: dict | None = None,
    data: bytes | None = None,
    timeout: float = 60.0,
) -> tuple[int, bytes]:
    """Perform an HTTP request using urllib (stdlib). Returns (status, body)."""
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


class SupabaseStorageAdapter(StorageAdapter):
    """Supabase Storage adapter."""
    
    def __init__(
        self,
        url: str,
        key: str,
        bucket_name: str,
        prefix: str = "",
    ):
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
        if self.prefix:
            return f"{self.prefix}/{path}"
        return path
    
    def _generate_unique_filename(self, original_filename: str) -> str:
        ext = Path(original_filename).suffix
        return f"{uuid.uuid4()}{ext}"

    async def save(
        self,
        file_content: bytes,
        filename: str,
        content_type: str,
        subdirectory: Optional[str] = None,
        preserve_filename: bool = False,
    ) -> StorageFile:
        """Save file to Supabase Storage."""
        stored_filename = filename if preserve_filename else self._generate_unique_filename(filename)
        relative_path = stored_filename
        if subdirectory:
            relative_path = f"{subdirectory}/{stored_filename}"
        
        full_path = self._get_full_path(relative_path)
        upload_url = f"{self.storage_url}/object/{self.bucket_name}/{full_path}"
        
        headers = {
            **self._headers,
            "Content-Type": content_type,
            "x-upsert": "true",
        }

        status, body = await asyncio.to_thread(
            _urllib_request, upload_url,
            method="POST", headers=headers, data=bytes(file_content),
        )
        if status >= 400:
            logger.error(
                "Supabase Storage upload failed: %s %s — %s",
                status, upload_url, body.decode(errors="replace"),
            )
            raise RuntimeError(
                f"Supabase upload failed ({status}): {body.decode(errors='replace')[:500]}"
            )
        
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
        payload = json_mod.dumps({"prefixes": [full_path]}).encode()
        headers = {**self._headers, "Content-Type": "application/json"}
        
        try:
            status, _ = await asyncio.to_thread(
                _urllib_request, delete_url,
                method="DELETE", headers=headers, data=payload,
            )
            return status in (200, 204)
        except Exception:
            return False
    
    async def get(self, path: str) -> Optional[bytes]:
        """Get file content from Supabase Storage."""
        full_path = self._get_full_path(path)
        download_url = f"{self.storage_url}/object/{self.bucket_name}/{full_path}"
        
        try:
            status, body = await asyncio.to_thread(
                _urllib_request, download_url,
                method="GET", headers=self._headers,
            )
            return body if status == 200 else None
        except Exception:
            return None
    
    async def exists(self, path: str) -> bool:
        """Check if file exists in Supabase Storage."""
        full_path = self._get_full_path(path)
        list_url = f"{self.storage_url}/object/list/{self.bucket_name}"
        
        try:
            path_parts = full_path.rsplit("/", 1)
            prefix = path_parts[0] if len(path_parts) > 1 else ""
            filename = path_parts[-1]
            
            payload = json_mod.dumps(
                {"prefix": prefix, "search": filename, "limit": 1}
            ).encode()
            headers = {**self._headers, "Content-Type": "application/json"}
            status, body = await asyncio.to_thread(
                _urllib_request, list_url,
                method="POST", headers=headers, data=payload,
            )
            if status == 200:
                return len(json_mod.loads(body)) > 0
            return False
        except Exception:
            return False
    
    async def get_url(self, path: str, expires_in: int = 3600) -> Optional[str]:
        """Get signed URL for file access."""
        full_path = self._get_full_path(path)
        sign_url = f"{self.storage_url}/object/sign/{self.bucket_name}/{full_path}"
        
        try:
            payload = json_mod.dumps({"expiresIn": expires_in}).encode()
            headers = {**self._headers, "Content-Type": "application/json"}
            status, body = await asyncio.to_thread(
                _urllib_request, sign_url,
                method="POST", headers=headers, data=payload,
            )
            if status == 200:
                data = json_mod.loads(body)
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
            payload = json_mod.dumps(
                {"prefix": search_prefix, "limit": limit}
            ).encode()
            headers = {**self._headers, "Content-Type": "application/json"}
            status, body = await asyncio.to_thread(
                _urllib_request, list_url,
                method="POST", headers=headers, data=payload,
            )
            
            if status == 200:
                data = json_mod.loads(body)
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
