"""
Local Filesystem Storage Adapter

Stores files on the local filesystem. The base path is configurable
via environment variables and should be outside the backend folder
to prevent uvicorn restarts on file changes.
"""
import os
import uuid
import aiofiles
from pathlib import Path
from typing import Optional
from datetime import datetime

from .base import StorageAdapter, StorageFile


class LocalStorageAdapter(StorageAdapter):
    """
    Local filesystem storage adapter.
    
    Files are stored in a configurable directory, organized by subdirectories.
    The storage path should be configured outside the backend folder to prevent
    uvicorn reload triggers.
    """
    
    def __init__(self, base_path: str):
        """
        Initialize local storage adapter.
        
        Args:
            base_path: Base directory for file storage (absolute or relative to project root)
        """
        self.base_path = Path(base_path).resolve()
        self._ensure_base_directory()
    
    def _ensure_base_directory(self) -> None:
        """Create base directory if it doesn't exist."""
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def _get_full_path(self, relative_path: str) -> Path:
        """Get full filesystem path from relative path."""
        return self.base_path / relative_path
    
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
        """Save file to local filesystem."""
        # Build target directory
        target_dir = self.base_path
        if subdirectory:
            target_dir = target_dir / subdirectory
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename
        unique_filename = self._generate_unique_filename(filename)
        file_path = target_dir / unique_filename
        
        # Write file
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(file_content)
        
        # Calculate relative path
        relative_path = str(file_path.relative_to(self.base_path))
        
        return StorageFile(
            path=relative_path,
            filename=filename,
            content_type=content_type,
            size=len(file_content),
            storage_url=None,  # Local files don't have URLs
            created_at=datetime.utcnow(),
        )
    
    async def delete(self, path: str) -> bool:
        """Delete file from local filesystem."""
        full_path = self._get_full_path(path)
        try:
            if full_path.exists():
                os.remove(full_path)
                
                # Clean up empty parent directories
                parent = full_path.parent
                while parent != self.base_path:
                    if not any(parent.iterdir()):
                        parent.rmdir()
                        parent = parent.parent
                    else:
                        break
                        
                return True
            return False
        except Exception:
            return False
    
    async def get(self, path: str) -> Optional[bytes]:
        """Read file content from local filesystem."""
        full_path = self._get_full_path(path)
        try:
            if full_path.exists():
                async with aiofiles.open(full_path, "rb") as f:
                    return await f.read()
            return None
        except Exception:
            return None
    
    async def exists(self, path: str) -> bool:
        """Check if file exists on local filesystem."""
        full_path = self._get_full_path(path)
        return full_path.exists()
    
    async def get_url(self, path: str, expires_in: int = 3600) -> Optional[str]:
        """
        Local files don't have direct URLs.
        Returns None - use the API endpoint to serve files.
        """
        return None
    
    async def list_files(
        self,
        prefix: Optional[str] = None,
        limit: int = 100,
    ) -> list[StorageFile]:
        """List files in local storage."""
        search_path = self.base_path
        if prefix:
            search_path = search_path / prefix
        
        files: list[StorageFile] = []
        
        if not search_path.exists():
            return files
        
        for file_path in search_path.rglob("*"):
            if file_path.is_file() and len(files) < limit:
                relative_path = str(file_path.relative_to(self.base_path))
                stat = file_path.stat()
                
                files.append(StorageFile(
                    path=relative_path,
                    filename=file_path.name,
                    content_type=self._guess_content_type(file_path.name),
                    size=stat.st_size,
                    created_at=datetime.fromtimestamp(stat.st_ctime),
                ))
        
        return files
    
    def _guess_content_type(self, filename: str) -> str:
        """Guess content type from filename extension."""
        import mimetypes
        mime_type, _ = mimetypes.guess_type(filename)
        return mime_type or "application/octet-stream"
