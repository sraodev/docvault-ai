#!/usr/bin/env python3
"""
Helper script to add logging imports to Python files that don't have them.

This script:
1. Finds all Python files in the app directory
2. Checks if they already have logging imports
3. Adds logging import and logger initialization if missing

Usage:
    python add_logging_helper.py
"""

import os
import re
from pathlib import Path

APP_DIR = Path(__file__).parent / "app"

LOGGING_IMPORT = "from ..core.logging_config import get_logger"
LOGGER_INIT = "logger = get_logger(__name__)"

def has_logging_import(content: str) -> bool:
    """Check if file already has logging import."""
    return "get_logger" in content or "logging.getLogger" in content

def add_logging_import(file_path: Path) -> bool:
    """Add logging import to a file if it doesn't have it."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if has_logging_import(content):
            return False  # Already has logging
        
        # Find the last import statement
        lines = content.split('\n')
        last_import_idx = -1
        
        for i, line in enumerate(lines):
            if line.strip().startswith('import ') or line.strip().startswith('from '):
                last_import_idx = i
        
        if last_import_idx == -1:
            # No imports found, add at the beginning
            insert_idx = 0
        else:
            insert_idx = last_import_idx + 1
        
        # Calculate relative import depth
        depth = len(file_path.relative_to(APP_DIR).parts) - 1
        
        # Adjust import path based on depth
        if depth == 0:
            import_line = "from .core.logging_config import get_logger"
        elif depth == 1:
            import_line = "from ..core.logging_config import get_logger"
        elif depth == 2:
            import_line = "from ...core.logging_config import get_logger"
        else:
            import_line = "from " + (".." * depth) + ".core.logging_config import get_logger"
        
        # Insert logging import and logger initialization
        lines.insert(insert_idx, import_line)
        lines.insert(insert_idx + 1, "")
        lines.insert(insert_idx + 2, "logger = get_logger(__name__)")
        
        # Write back
        new_content = '\n'.join(lines)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        return True
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """Main function to process all Python files."""
    python_files = list(APP_DIR.rglob("*.py"))
    
    # Exclude __pycache__ and venv
    python_files = [f for f in python_files if '__pycache__' not in str(f) and 'venv' not in str(f)]
    
    updated = 0
    skipped = 0
    
    for file_path in sorted(python_files):
        # Skip the logging config file itself
        if 'logging_config.py' in str(file_path):
            continue
        
        if add_logging_import(file_path):
            print(f"✓ Added logging to: {file_path.relative_to(APP_DIR.parent)}")
            updated += 1
        else:
            skipped += 1
    
    print(f"\nSummary:")
    print(f"  Updated: {updated} files")
    print(f"  Skipped: {skipped} files (already have logging)")
    print(f"  Total: {len(python_files)} files")

if __name__ == "__main__":
    main()

