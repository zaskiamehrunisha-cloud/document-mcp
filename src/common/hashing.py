"""SHA-256 content hashing utilities for idempotent uploads and caching."""
import hashlib
from pathlib import Path
from typing import Union


def compute_file_hash(file_path: Union[str, Path]) -> str:
    """
    Compute SHA-256 hash of a file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Hexadecimal SHA-256 hash string
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        # Read in 64KB chunks to handle large files efficiently
        for byte_block in iter(lambda: f.read(65536), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def compute_content_hash(content: bytes) -> str:
    """
    Compute SHA-256 hash of byte content.
    
    Args:
        content: Raw bytes to hash
        
    Returns:
        Hexadecimal SHA-256 hash string
    """
    return hashlib.sha256(content).hexdigest()


def compute_text_hash(text: str) -> str:
    """
    Compute SHA-256 hash of text content.
    
    Args:
        text: String content to hash
        
    Returns:
        Hexadecimal SHA-256 hash string
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()