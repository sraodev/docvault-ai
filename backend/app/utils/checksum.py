"""
Checksum utilities - Pure functions for file checksum calculation.
"""
import hashlib
from pathlib import Path
from ..domain.value_objects import FileChecksum

def calculate_file_checksum(file_path: Path) -> FileChecksum:
    """
    Calculate SHA-256 checksum of a file.
    
    Args:
        file_path: Path to file
    
    Returns:
        SHA-256 checksum as hex string
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return FileChecksum(sha256_hash.hexdigest())

