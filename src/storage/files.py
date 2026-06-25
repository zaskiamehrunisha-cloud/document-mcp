"""Local file storage utilities for uploads and previews."""
import shutil
from pathlib import Path
from typing import Optional
import uuid

from src.config.settings import settings
from src.common.exceptions import FileStorageError


class FileStorage:
    """Manages local file storage for uploads and previews."""
    
    def __init__(self):
        """Initialize file storage with configured directories."""
        self.upload_dir = Path(settings.upload_dir)
        self.preview_dir = Path(settings.preview_dir)
        self._ensure_directories()
    
    def _ensure_directories(self) -> None:
        """Create storage directories if they don't exist."""
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.preview_dir.mkdir(parents=True, exist_ok=True)
    
    def save_upload(self, file_content: bytes, original_filename: str, file_hash: str) -> Path:
        """
        Save an uploaded file to the upload directory.
        
        Args:
            file_content: Raw file bytes
            original_filename: Original filename with extension
            file_hash: SHA-256 hash for idempotent naming
            
        Returns:
            Path to the saved file
            
        Raises:
            FileStorageError: If save operation fails
        """
        try:
            # Use hash as filename to ensure idempotency
            ext = Path(original_filename).suffix
            filename = f"{file_hash}{ext}"
            file_path = self.upload_dir / filename
            
            # Write file atomically
            temp_path = file_path.with_suffix(f".tmp_{uuid.uuid4().hex}")
            temp_path.write_bytes(file_content)
            temp_path.replace(file_path)
            
            return file_path
        except Exception as e:
            raise FileStorageError(f"Failed to save upload: {e}") from e
    
    def get_upload_path(self, file_hash: str, extension: str) -> Path:
        """
        Get the path for an uploaded file by hash.
        
        Args:
            file_hash: SHA-256 hash
            extension: File extension with dot
            
        Returns:
            Path to the file
        """
        return self.upload_dir / f"{file_hash}{extension}"
    
    def file_exists(self, file_hash: str, extension: str) -> bool:
        """
        Check if an uploaded file exists.
        
        Args:
            file_hash: SHA-256 hash
            extension: File extension with dot
            
        Returns:
            True if file exists
        """
        return self.get_upload_path(file_hash, extension).exists()
    
    def save_preview(self, file_content: bytes, document_id: int, page: int) -> Path:
        """
        Save a preview image (e.g., DWG rasterization).
        
        Args:
            file_content: Image bytes
            document_id: Document ID
            page: Page number
            
        Returns:
            Path to the saved preview
        """
        try:
            filename = f"doc_{document_id}_page_{page}.png"
            file_path = self.preview_dir / filename
            file_path.write_bytes(file_content)
            return file_path
        except Exception as e:
            raise FileStorageError(f"Failed to save preview: {e}") from e
    
    def get_preview_path(self, document_id: int, page: int) -> Path:
        """
        Get the path for a preview image.
        
        Args:
            document_id: Document ID
            page: Page number
            
        Returns:
            Path to the preview image
        """
        return self.preview_dir / f"doc_{document_id}_page_{page}.png"
    
    def delete_upload(self, file_hash: str, extension: str) -> None:
        """
        Delete an uploaded file.
        
        Args:
            file_hash: SHA-256 hash
            extension: File extension with dot
        """
        file_path = self.get_upload_path(file_hash, extension)
        if file_path.exists():
            file_path.unlink()
    
    def cleanup_temp_files(self, max_age_hours: int = 24) -> int:
        """
        Clean up temporary files older than max_age_hours.
        
        Args:
            max_age_hours: Maximum age of temp files in hours
            
        Returns:
            Number of files deleted
        """
        import time
        
        deleted = 0
        cutoff_time = time.time() - (max_age_hours * 3600)
        
        for directory in [self.upload_dir, self.preview_dir]:
            for file_path in directory.glob("*.tmp_*"):
                if file_path.stat().st_mtime < cutoff_time:
                    try:
                        file_path.unlink()
                        deleted += 1
                    except Exception:
                        pass
        
        return deleted


# Global storage instance
file_storage = FileStorage()