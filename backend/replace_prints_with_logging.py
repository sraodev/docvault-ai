#!/usr/bin/env python3
"""
Script to replace print() statements with logging calls.

This script:
1. Finds all print() statements in Python files
2. Replaces them with appropriate logger calls based on context
3. Handles different print patterns (info, error, warning, debug)
"""

import re
from pathlib import Path

APP_DIR = Path(__file__).parent / "app"

def classify_print_statement(line: str) -> str:
    """Classify print statement to determine log level."""
    line_lower = line.lower()
    
    # Error patterns
    if any(keyword in line_lower for keyword in ['error', 'failed', 'exception', '❌', 'failed']):
        return 'error'
    
    # Warning patterns
    if any(keyword in line_lower for keyword in ['warning', 'warn', '⚠️', 'skip', 'skipped']):
        return 'warning'
    
    # Info patterns (success, status, general info)
    if any(keyword in line_lower for keyword in ['✅', 'success', 'complete', 'migrated', 'loaded', 'found', 'starting', '📋', '📊', '📁', '💾']):
        return 'info'
    
    # Debug patterns (detailed info, progress)
    if any(keyword in line_lower for keyword in ['debug', 'processing', '📥', '📤', '🔍', '🔄']):
        return 'debug'
    
    # Default to info
    return 'info'

def replace_print_in_file(file_path: Path) -> int:
    """Replace print statements with logging in a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if file has logger
        if 'logger = get_logger(__name__)' not in content:
            return 0
        
        lines = content.split('\n')
        replacements = 0
        
        for i, line in enumerate(lines):
            # Match print statements
            if re.search(r'print\s*\(', line):
                # Determine log level
                log_level = classify_print_statement(line)
                
                # Extract the print content
                # Handle different print formats
                if 'print(f"' in line or "print(f'" in line:
                    # f-string print
                    match = re.search(r'print\(f?["\'](.*?)["\']\)', line)
                    if match:
                        content_str = match.group(1)
                        # Replace with logger call
                        indent = len(line) - len(line.lstrip())
                        new_line = ' ' * indent + f'logger.{log_level}(f"{content_str}")'
                        lines[i] = new_line
                        replacements += 1
                elif 'print(' in line:
                    # Regular print
                    match = re.search(r'print\((.*?)\)', line)
                    if match:
                        content_expr = match.group(1)
                        # Replace with logger call
                        indent = len(line) - len(line.lstrip())
                        new_line = ' ' * indent + f'logger.{log_level}({content_expr})'
                        lines[i] = new_line
                        replacements += 1
        
        if replacements > 0:
            new_content = '\n'.join(lines)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
        
        return replacements
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return 0

def main():
    """Main function."""
    python_files = list(APP_DIR.rglob("*.py"))
    python_files = [f for f in python_files if '__pycache__' not in str(f) and 'venv' not in str(f)]
    
    total_replacements = 0
    files_updated = 0
    
    for file_path in sorted(python_files):
        replacements = replace_print_in_file(file_path)
        if replacements > 0:
            print(f"✓ {file_path.relative_to(APP_DIR.parent)}: {replacements} replacements")
            total_replacements += replacements
            files_updated += 1
    
    print(f"\nSummary:")
    print(f"  Files updated: {files_updated}")
    print(f"  Total replacements: {total_replacements}")

if __name__ == "__main__":
    main()

