"""
Checksum utilities - Pure functions for file checksum calculation.
"""
import hashlib
from pathlib import Path
from ..domain.value_objects import FileChecksum

def calculate_file_checksum(file_path: Path) -> str:
    """
    Calculate SHA-256 checksum of a file.
    
    Args:
        file_path: Path to file
    
    Returns:
        SHA-256 checksum as hex string
        
    Raises:
        FileNotFoundError: If file doesn't exist
        IOError: If file cannot be read
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
    except IOError as e:
        raise IOError(f"Error reading file {file_path}: {e}") from e
    
    return sha256_hash.hexdigest()

