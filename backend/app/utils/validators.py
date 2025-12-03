"""
Validation utilities - Pure validation functions.
"""
from typing import List
from ..core.logging_config import get_logger

logger = get_logger(__name__)

def validate_folder_name(name: str) -> None:
    """
    Validate folder name.
    
    Raises:
        ValueError: If folder name is invalid
    """
    name = name.strip()
    if not name:
        raise ValueError("Folder name cannot be empty")
    
    invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
    found_chars = [char for char in invalid_chars if char in name]
    if found_chars:
        raise ValueError(f"Folder name cannot contain: {', '.join(found_chars)}")

def validate_filename(filename: str) -> None:
    """
    Validate filename.
    
    Raises:
        ValueError: If filename is invalid
    """
    if not filename or not filename.strip():
        raise ValueError("Filename cannot be empty")
    
    # Extract just the filename (remove path)
    from ..utils.filename import extract_filename
    clean_name = extract_filename(filename)
    
    if not clean_name:
        raise ValueError("Invalid filename")
