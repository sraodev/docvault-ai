"""
JSON file-based adapter implementing DatabaseInterface.
Perfect for local demos - stores all data in JSON files for persistence.
Data persists between restarts, no database setup needed.
"""
import json
import asyncio
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import copy
from threading import Lock

from .base import DatabaseInterface

class JSONAdapter(DatabaseInterface):
    """
    JSON file-based database adapter.
    Stores all data in JSON files - perfect for local demos and development.
    Data persists between restarts.
    """
    
    def __init__(self, data_dir: Optional[Path] = None):
        """
        Initialize JSON adapter.
        
        Args:
            data_dir: Directory to store JSON files (defaults to backend/data/json_db)
        """
        if data_dir is None:
            # Default to backend/data/json_db
            base_dir = Path(__file__).resolve().parent.parent.parent.parent
            data_dir = base_dir / "data" / "json_db"
        
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # JSON file paths
        self.documents_file = self.data_dir / "documents.json"
        self.folders_file = self.data_dir / "folders.json"
        
        # In-memory storage (loaded from JSON files)
        self._documents: Dict[str, Dict] = {}
        self._folders: Dict[str, Dict] = {}
        self._checksum_index: Dict[str, str] = {}
        self._folder_index: Dict[str, List[str]] = {}
        
        # Lock for thread-safe file operations
        self._lock = Lock()
    
    async def initialize(self):
        """Initialize database - load data from JSON files."""
        # Load data synchronously (file I/O is fast)
        self._load_data()
    
    async def close(self):
        """Close database - save data to JSON files."""
        await self._save_data()
    
    def _load_data(self):
        """Load data from JSON files into memory."""
        # Load documents
        if self.documents_file.exists():
            try:
                with open(self.documents_file, 'r', encoding='utf-8') as f:
                    self._documents = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load documents.json: {e}")
                self._documents = {}
        else:
            self._documents = {}
        
        # Load folders
        if self.folders_file.exists():
            try:
                with open(self.folders_file, 'r', encoding='utf-8') as f:
                    self._folders = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load folders.json: {e}")
                self._folders = {}
        else:
            self._folders = {}
        
        # Rebuild indexes
        self._rebuild_indexes()
    
    def _rebuild_indexes(self):
        """Rebuild indexes from loaded data."""
        self._checksum_index.clear()
        self._folder_index.clear()
        
        # Rebuild checksum index
        for doc_id, doc in self._documents.items():
            checksum = doc.get("checksum")
            if checksum:
                self._checksum_index[checksum] = doc_id
        
        # Rebuild folder index
        for doc_id, doc in self._documents.items():
            folder = doc.get("folder")
            if folder:
                if folder not in self._folder_index:
                    self._folder_index[folder] = []
                if doc_id not in self._folder_index[folder]:
                    self._folder_index[folder].append(doc_id)
    
    async def _save_data(self):
        """Save data from memory to JSON files."""
        def _save():
            with self._lock:
                # Save documents
                try:
                    with open(self.documents_file, 'w', encoding='utf-8') as f:
                        json.dump(self._documents, f, indent=2, ensure_ascii=False)
                except IOError as e:
                    print(f"Error saving documents.json: {e}")
                
                # Save folders
                try:
                    with open(self.folders_file, 'w', encoding='utf-8') as f:
                        json.dump(self._folders, f, indent=2, ensure_ascii=False)
                except IOError as e:
                    print(f"Error saving folders.json: {e}")
        
        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _save)
    
    # Document operations
    async def create_document(self, doc_data: Dict) -> Dict:
        """Create a new document record."""
        doc_id = doc_data.get("id")
        if not doc_id:
            raise ValueError("Document must have an 'id' field")
        
        # Add timestamps if not present
        now = datetime.now().isoformat()
        if "created_at" not in doc_data:
            doc_data["created_at"] = now
        if "updated_at" not in doc_data:
            doc_data["updated_at"] = now
        
        # Store document (deep copy to avoid reference issues)
        self._documents[doc_id] = copy.deepcopy(doc_data)
        
        # Update indexes
        checksum = doc_data.get("checksum")
        if checksum:
            self._checksum_index[checksum] = doc_id
        
        folder = doc_data.get("folder")
        if folder:
            if folder not in self._folder_index:
                self._folder_index[folder] = []
            if doc_id not in self._folder_index[folder]:
                self._folder_index[folder].append(doc_id)
        
        # Save to file
        await self._save_data()
        
        return copy.deepcopy(self._documents[doc_id])
    
    async def get_document(self, doc_id: str) -> Optional[Dict]:
        """Get a document by ID."""
        doc = self._documents.get(doc_id)
        return copy.deepcopy(doc) if doc else None
    
    async def get_all_documents(self, folder: Optional[str] = None) -> List[Dict]:
        """Get all documents, optionally filtered by folder."""
        if folder is None:
            return [copy.deepcopy(doc) for doc in self._documents.values()]
        else:
            doc_ids = self._folder_index.get(folder, [])
            return [copy.deepcopy(self._documents[doc_id]) for doc_id in doc_ids if doc_id in self._documents]
    
    async def update_document(self, doc_id: str, updates: Dict) -> Optional[Dict]:
        """Update a document."""
        if doc_id not in self._documents:
            return None
        
        doc = self._documents[doc_id]
        
        # Update fields
        for key, value in updates.items():
            doc[key] = value
        
        # Update timestamp
        doc["updated_at"] = datetime.now().isoformat()
        
        # Update indexes if checksum or folder changed
        old_checksum = doc.get("checksum")
        new_checksum = updates.get("checksum")
        if new_checksum and new_checksum != old_checksum:
            if old_checksum and old_checksum in self._checksum_index:
                del self._checksum_index[old_checksum]
            self._checksum_index[new_checksum] = doc_id
        
        old_folder = doc.get("folder")
        new_folder = updates.get("folder")
        if new_folder != old_folder:
            if old_folder and old_folder in self._folder_index:
                if doc_id in self._folder_index[old_folder]:
                    self._folder_index[old_folder].remove(doc_id)
            if new_folder:
                if new_folder not in self._folder_index:
                    self._folder_index[new_folder] = []
                if doc_id not in self._folder_index[new_folder]:
                    self._folder_index[new_folder].append(doc_id)
        
        # Save to file
        await self._save_data()
        
        return copy.deepcopy(doc)
    
    async def delete_document(self, doc_id: str) -> bool:
        """Delete a document."""
        if doc_id not in self._documents:
            return False
        
        doc = self._documents[doc_id]
        
        # Remove from indexes
        checksum = doc.get("checksum")
        if checksum and checksum in self._checksum_index:
            del self._checksum_index[checksum]
        
        folder = doc.get("folder")
        if folder and folder in self._folder_index:
            if doc_id in self._folder_index[folder]:
                self._folder_index[folder].remove(doc_id)
        
        # Delete document
        del self._documents[doc_id]
        
        # Save to file
        await self._save_data()
        
        return True
    
    async def find_document_by_checksum(self, checksum: str) -> Optional[Dict]:
        """Find a document by checksum."""
        doc_id = self._checksum_index.get(checksum)
        if doc_id and doc_id in self._documents:
            return copy.deepcopy(self._documents[doc_id])
        return None
    
    async def get_documents_by_folder(self, folder_path: str, include_subfolders: bool = False) -> List[Dict]:
        """Get documents in a folder, optionally including subfolders."""
        if include_subfolders:
            results = []
            for doc in self._documents.values():
                doc_folder = doc.get("folder")
                if doc_folder and (doc_folder == folder_path or doc_folder.startswith(folder_path + "/")):
                    results.append(copy.deepcopy(doc))
            return results
        else:
            doc_ids = self._folder_index.get(folder_path, [])
            return [copy.deepcopy(self._documents[doc_id]) for doc_id in doc_ids if doc_id in self._documents]
    
    # Folder operations
    async def create_folder(self, folder_data: Dict) -> Dict:
        """Create a folder record."""
        folder_path = folder_data.get("folder_path")
        if not folder_path:
            raise ValueError("Folder must have a 'folder_path' field")
        
        # Add timestamps if not present
        now = datetime.now().isoformat()
        if "created_at" not in folder_data:
            folder_data["created_at"] = now
        if "updated_at" not in folder_data:
            folder_data["updated_at"] = now
        
        # Store folder (deep copy)
        self._folders[folder_path] = copy.deepcopy(folder_data)
        
        # Initialize folder index if not exists
        if folder_path not in self._folder_index:
            self._folder_index[folder_path] = []
        
        # Save to file
        await self._save_data()
        
        return copy.deepcopy(self._folders[folder_path])
    
    async def get_folder(self, folder_path: str) -> Optional[Dict]:
        """Get a folder by path."""
        folder = self._folders.get(folder_path)
        return copy.deepcopy(folder) if folder else None
    
    async def get_all_folders(self) -> List[str]:
        """Get all folder paths (from both folders collection and documents)."""
        folders_set = set()
        
        # Add folders from folders collection
        folders_set.update(self._folders.keys())
        
        # Add folders from documents
        for doc in self._documents.values():
            folder = doc.get("folder")
            if folder:
                folders_set.add(folder)
        
        return sorted(list(folders_set))
    
    async def delete_folder(self, folder_path: str) -> int:
        """Delete a folder and return count of deleted items."""
        deleted_count = 0
        
        # Get all documents in this folder and subfolders
        docs_to_delete = await self.get_documents_by_folder(folder_path, include_subfolders=True)
        
        # Delete documents
        for doc in docs_to_delete:
            await self.delete_document(doc["id"])
            deleted_count += 1
        
        # Delete folder metadata
        if folder_path in self._folders:
            del self._folders[folder_path]
        
        # Clean up folder index
        if folder_path in self._folder_index:
            del self._folder_index[folder_path]
        
        # Remove subfolder indexes
        subfolders_to_remove = [
            fpath for fpath in self._folder_index.keys()
            if fpath.startswith(folder_path + "/")
        ]
        for subfolder in subfolders_to_remove:
            del self._folder_index[subfolder]
            if subfolder in self._folders:
                del self._folders[subfolder]
        
        # Save to file
        await self._save_data()
        
        return deleted_count
    
    async def update_folder_path(self, old_path: str, new_path: Optional[str]) -> int:
        """Update folder paths when moving folders."""
        moved_count = 0
        
        # Get all documents in old folder and subfolders
        docs_to_move = await self.get_documents_by_folder(old_path, include_subfolders=True)
        
        for doc in docs_to_move:
            doc_id = doc["id"]
            current_folder = doc.get("folder")
            
            if current_folder:
                # Calculate new folder path
                if current_folder == old_path:
                    new_doc_folder = new_path
                elif current_folder.startswith(old_path + "/"):
                    relative_path = current_folder[len(old_path) + 1:]
                    if new_path:
                        new_doc_folder = f"{new_path}/{relative_path}"
                    else:
                        new_doc_folder = relative_path
                else:
                    continue
                
                # Update document folder
                await self.update_document(doc_id, {"folder": new_doc_folder})
                moved_count += 1
        
        # Update folder metadata
        if old_path in self._folders:
            folder_data = self._folders[old_path]
            if new_path:
                folder_data["folder_path"] = new_path
                folder_data["parent_folder"] = new_path.rsplit("/", 1)[0] if "/" in new_path else None
                folder_data["updated_at"] = datetime.now().isoformat()
                self._folders[new_path] = folder_data
                del self._folders[old_path]
            else:
                del self._folders[old_path]
        
        # Update folder indexes
        if old_path in self._folder_index:
            if new_path:
                self._folder_index[new_path] = self._folder_index.pop(old_path)
            else:
                doc_ids = self._folder_index.pop(old_path)
                root_key = "" if "" in self._folder_index else None
                if root_key is None:
                    self._folder_index[""] = []
                self._folder_index[""].extend(doc_ids)
        
        # Save to file
        await self._save_data()
        
        return moved_count
    
    async def get_documents_missing_summaries(self, limit: Optional[int] = None) -> List[Dict]:
        """Get documents that are missing summaries (summary is None or empty)."""
        results = []
        
        for doc in self._documents.values():
            summary = doc.get("summary")
            # Check if summary is None, empty string, or missing
            if not summary or (isinstance(summary, str) and not summary.strip()):
                results.append(copy.deepcopy(doc))
        
        # Sort by upload_date (newest first) for better UX
        results.sort(key=lambda x: x.get("upload_date", ""), reverse=True)
        
        # Apply limit if specified
        if limit is not None and limit > 0:
            results = results[:limit]
        
        return results
    
    def get_stats(self) -> Dict:
        """Get statistics about the JSON database (useful for debugging)."""
        return {
            "total_documents": len(self._documents),
            "total_folders": len(self._folders),
            "checksum_index_size": len(self._checksum_index),
            "folder_index_size": len(self._folder_index),
            "data_directory": str(self.data_dir)
        }

