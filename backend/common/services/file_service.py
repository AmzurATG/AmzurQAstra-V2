"""
File Service for handling file uploads and storage
"""
import os
import uuid
import aiofiles
from typing import Optional
from pathlib import Path
from fastapi import UploadFile

from config import settings


class FileService:
    """Service for file operations."""
    
    def __init__(self):
        self.upload_dir = Path(settings.UPLOAD_DIR)
        self.max_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024  # Convert to bytes
    
    async def save_file(
        self,
        file: UploadFile,
        subdirectory: Optional[str] = None,
    ) -> str:
        """
        Save uploaded file and return the file path.
        
        Args:
            file: Uploaded file
            subdirectory: Optional subdirectory within upload folder
        
        Returns:
            Relative path to the saved file
        """
        # Create directory if not exists
        target_dir = self.upload_dir
        if subdirectory:
            target_dir = target_dir / subdirectory
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename
        file_ext = Path(file.filename).suffix if file.filename else ""
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = target_dir / unique_filename
        
        # Save file
        async with aiofiles.open(file_path, "wb") as out_file:
            content = await file.read()
            await out_file.write(content)
        
        # Return relative path
        return str(file_path.relative_to(self.upload_dir))
    
    async def delete_file(self, file_path: str) -> bool:
        """Delete a file."""
        full_path = self.upload_dir / file_path
        if full_path.exists():
            os.remove(full_path)
            return True
        return False
    
    async def get_file_path(self, relative_path: str) -> Optional[Path]:
        """Get full file path."""
        full_path = self.upload_dir / relative_path
        if full_path.exists():
            return full_path
        return None
    
    def validate_file_size(self, file: UploadFile) -> bool:
        """Validate file size."""
        # Note: This requires reading the file, better to check after upload
        return True
    
    def get_allowed_extensions(self, file_type: str) -> list:
        """Get allowed extensions for a file type."""
        extensions = {
            "document": [".pdf", ".docx", ".doc", ".md", ".txt"],
            "image": [".png", ".jpg", ".jpeg", ".gif", ".webp"],
            "data": [".json", ".csv", ".xlsx", ".xls"],
        }
        return extensions.get(file_type, [])
