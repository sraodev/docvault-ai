"""
Value Objects - Immutable objects that represent domain concepts.
These have no identity and are compared by value.
"""
from typing import NewType

# Value objects for type safety and domain clarity
FileChecksum = NewType("FileChecksum", str)
FilePath = NewType("FilePath", str)
FolderPath = NewType("FolderPath", str)

