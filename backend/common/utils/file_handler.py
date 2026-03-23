"""
File handling utilities
"""
import os
import mimetypes
from pathlib import Path
from typing import Optional, Tuple


def get_file_extension(filename: str) -> str:
    """Get file extension from filename."""
    return Path(filename).suffix.lower()


def get_mime_type(filename: str) -> str:
    """Get MIME type from filename."""
    mime_type, _ = mimetypes.guess_type(filename)
    return mime_type or "application/octet-stream"


def is_allowed_extension(filename: str, allowed: list) -> bool:
    """Check if file extension is allowed."""
    ext = get_file_extension(filename)
    return ext in allowed


def get_file_size_mb(file_path: str) -> float:
    """Get file size in MB."""
    size_bytes = os.path.getsize(file_path)
    return size_bytes / (1024 * 1024)


def ensure_directory(path: str) -> Path:
    """Ensure directory exists, create if not."""
    dir_path = Path(path)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to remove unsafe characters."""
    # Replace unsafe characters
    unsafe_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
    safe_filename = filename
    for char in unsafe_chars:
        safe_filename = safe_filename.replace(char, '_')
    return safe_filename
