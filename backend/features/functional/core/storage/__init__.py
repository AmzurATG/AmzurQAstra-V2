"""
Storage Module for Document Uploads

This module provides a flexible storage adapter system supporting:
- Local filesystem storage
- AWS S3 storage
- Supabase storage

The storage backend is configured via environment variables.
"""

from .base import StorageAdapter, StorageFile
from .local import LocalStorageAdapter
from .s3 import S3StorageAdapter
from .supabase import SupabaseStorageAdapter
from .factory import get_storage_adapter, StorageType

__all__ = [
    "StorageAdapter",
    "StorageFile",
    "LocalStorageAdapter",
    "S3StorageAdapter",
    "SupabaseStorageAdapter",
    "get_storage_adapter",
    "StorageType",
]
