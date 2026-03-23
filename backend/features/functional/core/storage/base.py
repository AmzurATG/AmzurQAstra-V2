"""
Base Storage Adapter Interface

Defines the contract for all storage adapters.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, BinaryIO
from datetime import datetime


@dataclass
class StorageFile:
    """Represents a stored file with metadata."""
    
    path: str  # Relative path within storage
    filename: str  # Original filename
    content_type: str
    size: int
    storage_url: Optional[str] = None  # Full URL if available (S3, Supabase)
    created_at: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "path": self.path,
            "filename": self.filename,
            "content_type": self.content_type,
            "size": self.size,
            "storage_url": self.storage_url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class StorageAdapter(ABC):
    """
    Abstract base class for storage adapters.
    
    All storage implementations (local, S3, Supabase) must implement this interface.
    """
    
    @abstractmethod
    async def save(
        self,
        file_content: bytes,
        filename: str,
        content_type: str,
        subdirectory: Optional[str] = None,
    ) -> StorageFile:
        """
        Save a file to storage.
        
        Args:
            file_content: Raw bytes of the file
            filename: Original filename
            content_type: MIME type of the file
            subdirectory: Optional subdirectory/prefix for organizing files
            
        Returns:
            StorageFile with metadata about the saved file
        """
        pass
    
    @abstractmethod
    async def delete(self, path: str) -> bool:
        """
        Delete a file from storage.
        
        Args:
            path: Relative path to the file
            
        Returns:
            True if deleted successfully, False otherwise
        """
        pass
    
    @abstractmethod
    async def get(self, path: str) -> Optional[bytes]:
        """
        Retrieve file content from storage.
        
        Args:
            path: Relative path to the file
            
        Returns:
            File contents as bytes, or None if not found
        """
        pass
    
    @abstractmethod
    async def exists(self, path: str) -> bool:
        """
        Check if a file exists in storage.
        
        Args:
            path: Relative path to the file
            
        Returns:
            True if file exists, False otherwise
        """
        pass
    
    @abstractmethod
    async def get_url(self, path: str, expires_in: int = 3600) -> Optional[str]:
        """
        Get a URL to access the file.
        
        Args:
            path: Relative path to the file
            expires_in: URL expiration time in seconds (for signed URLs)
            
        Returns:
            URL to access the file, or None if not available
        """
        pass
    
    @abstractmethod
    async def list_files(
        self, 
        prefix: Optional[str] = None,
        limit: int = 100,
    ) -> list[StorageFile]:
        """
        List files in storage.
        
        Args:
            prefix: Filter files by prefix/subdirectory
            limit: Maximum number of files to return
            
        Returns:
            List of StorageFile objects
        """
        pass
