"""
Storage Factory

Creates the appropriate storage adapter based on configuration.
"""
from enum import Enum
from typing import Optional
from functools import lru_cache

from .base import StorageAdapter
from .local import LocalStorageAdapter
from .s3 import S3StorageAdapter
from .supabase import SupabaseStorageAdapter


class StorageType(str, Enum):
    """Supported storage types."""
    LOCAL = "local"
    S3 = "s3"
    SUPABASE = "supabase"


def get_storage_adapter(
    storage_type: Optional[str] = None,
    # Local storage options
    local_path: Optional[str] = None,
    # S3 options
    s3_bucket: Optional[str] = None,
    s3_region: Optional[str] = None,
    s3_access_key: Optional[str] = None,
    s3_secret_key: Optional[str] = None,
    s3_endpoint_url: Optional[str] = None,
    s3_prefix: Optional[str] = None,
    # Supabase options
    supabase_url: Optional[str] = None,
    supabase_key: Optional[str] = None,
    supabase_bucket: Optional[str] = None,
    supabase_prefix: Optional[str] = None,
) -> StorageAdapter:
    """
    Create a storage adapter based on configuration.
    
    If parameters are not provided, reads from settings.
    
    Args:
        storage_type: Type of storage ('local', 's3', 'supabase')
        local_path: Path for local storage
        s3_*: S3 configuration options
        supabase_*: Supabase configuration options
        
    Returns:
        Configured StorageAdapter instance
        
    Raises:
        ValueError: If storage type is not supported or required config is missing
    """
    # Import settings here to avoid circular imports
    from config import settings
    
    # Use settings if not provided
    storage_type = storage_type or settings.STORAGE_TYPE
    
    if storage_type == StorageType.LOCAL or storage_type == "local":
        path = local_path or settings.STORAGE_LOCAL_PATH
        if not path:
            raise ValueError("Local storage path not configured (STORAGE_LOCAL_PATH)")
        return LocalStorageAdapter(base_path=path)
    
    elif storage_type == StorageType.S3 or storage_type == "s3":
        bucket = s3_bucket or settings.STORAGE_S3_BUCKET
        if not bucket:
            raise ValueError("S3 bucket not configured (STORAGE_S3_BUCKET)")
        
        return S3StorageAdapter(
            bucket_name=bucket,
            region=s3_region or settings.STORAGE_S3_REGION or "us-east-1",
            access_key_id=s3_access_key or settings.STORAGE_S3_ACCESS_KEY,
            secret_access_key=s3_secret_key or settings.STORAGE_S3_SECRET_KEY,
            endpoint_url=s3_endpoint_url or settings.STORAGE_S3_ENDPOINT_URL,
            prefix=s3_prefix or settings.STORAGE_S3_PREFIX or "",
        )
    
    elif storage_type == StorageType.SUPABASE or storage_type == "supabase":
        url = supabase_url or settings.STORAGE_SUPABASE_URL
        key = supabase_key or settings.STORAGE_SUPABASE_KEY
        bucket = supabase_bucket or settings.STORAGE_SUPABASE_BUCKET
        
        if not url or not key or not bucket:
            raise ValueError(
                "Supabase storage not fully configured. Required: "
                "STORAGE_SUPABASE_URL, STORAGE_SUPABASE_KEY, STORAGE_SUPABASE_BUCKET"
            )
        
        return SupabaseStorageAdapter(
            url=url,
            key=key,
            bucket_name=bucket,
            prefix=supabase_prefix or settings.STORAGE_SUPABASE_PREFIX or "",
        )
    
    else:
        raise ValueError(
            f"Unsupported storage type: {storage_type}. "
            f"Supported types: {', '.join([t.value for t in StorageType])}"
        )


@lru_cache(maxsize=1)
def get_default_storage_adapter() -> StorageAdapter:
    """
    Get the default storage adapter based on settings.
    
    Cached for performance - reuses the same adapter instance.
    
    Returns:
        StorageAdapter configured from settings
    """
    return get_storage_adapter()


def clear_storage_cache() -> None:
    """Clear the cached storage adapter (useful for testing)."""
    get_default_storage_adapter.cache_clear()
