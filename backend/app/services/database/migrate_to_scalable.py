"""
Migration script to convert legacy JSON database to scalable JSON database format.

This script migrates from:
- documents.json (single file)
- folders.json (single file)

To:
- index.json (global index)
- documents/{shard}/doc_id.json (shard-based storage)
- folders/{folder}.json (individual folder files)
"""
import json
import asyncio
from pathlib import Path
from typing import Dict, List
from datetime import datetime

def migrate_legacy_to_scalable(legacy_data_dir: Path, scalable_data_dir: Path):
    """
    Migrate legacy JSON database to scalable format.
    
    Args:
        legacy_data_dir: Directory containing documents.json and folders.json
        scalable_data_dir: Directory for scalable database (will be created)
    """
    print(f"🔄 Starting migration from {legacy_data_dir} to {scalable_data_dir}")
    
    # Create scalable database directories
    scalable_data_dir.mkdir(parents=True, exist_ok=True)
    documents_dir = scalable_data_dir / "documents"
    folders_dir = scalable_data_dir / "folders"
    logs_dir = scalable_data_dir / "logs"
    
    documents_dir.mkdir(exist_ok=True)
    folders_dir.mkdir(exist_ok=True)
    logs_dir.mkdir(exist_ok=True)
    
    # Load legacy data
    legacy_docs_file = legacy_data_dir / "documents.json"
    legacy_folders_file = legacy_data_dir / "folders.json"
    
    documents: Dict[str, Dict] = {}
    folders: Dict[str, Dict] = {}
    
    # Load documents
    if legacy_docs_file.exists():
        print(f"📖 Loading documents from {legacy_docs_file}")
        try:
            with open(legacy_docs_file, 'r', encoding='utf-8') as f:
                documents = json.load(f)
            print(f"   Loaded {len(documents)} documents")
        except Exception as e:
            print(f"   ⚠️  Error loading documents: {e}")
    else:
        print(f"   ⚠️  {legacy_docs_file} not found, skipping documents")
    
    # Load folders
    if legacy_folders_file.exists():
        print(f"📖 Loading folders from {legacy_folders_file}")
        try:
            with open(legacy_folders_file, 'r', encoding='utf-8') as f:
                folders = json.load(f)
            print(f"   Loaded {len(folders)} folders")
        except Exception as e:
            print(f"   ⚠️  Error loading folders: {e}")
    else:
        print(f"   ⚠️  {legacy_folders_file} not found, skipping folders")
    
    # Initialize index
    index = {
        "last_id": 0,
        "documents": {}
    }
    
    # Migrate documents
    print(f"📝 Migrating {len(documents)} documents to shard-based storage...")
    migrated_count = 0
    
    for doc_id, doc_data in documents.items():
        try:
            # Determine shard
            try:
                doc_num = int(doc_id)
                shard_start = (doc_num // 1000) * 1000
                shard_end = shard_start + 999
            except (ValueError, TypeError):
                import hashlib
                hash_val = int(hashlib.md5(doc_id.encode()).hexdigest()[:8], 16)
                shard_start = (hash_val % 100000) // 1000 * 1000
                shard_end = shard_start + 999
            
            shard_name = f"{shard_start}-{shard_end}"
            shard_dir = documents_dir / shard_name
            shard_dir.mkdir(exist_ok=True)
            
            # Save document to shard
            doc_file = shard_dir / f"{doc_id}.json"
            with open(doc_file, 'w', encoding='utf-8') as f:
                json.dump(doc_data, f, indent=2, ensure_ascii=False)
            
            # Update index
            index["documents"][doc_id] = {
                "filename": doc_data.get("filename", ""),
                "folder": doc_data.get("folder"),
                "shard": shard_name,
                "path": f"documents/{shard_name}/{doc_id}.json",
                "updated": doc_data.get("updated_at", datetime.now().isoformat())
            }
            
            # Update last_id
            try:
                doc_num = int(doc_id)
                if doc_num > index["last_id"]:
                    index["last_id"] = doc_num
            except (ValueError, TypeError):
                pass
            
            migrated_count += 1
            
            if migrated_count % 100 == 0:
                print(f"   Migrated {migrated_count}/{len(documents)} documents...")
        
        except Exception as e:
            print(f"   ⚠️  Error migrating document {doc_id}: {e}")
    
    print(f"✅ Migrated {migrated_count} documents")
    
    # Migrate folders
    print(f"📁 Migrating {len(folders)} folders...")
    for folder_path, folder_data in folders.items():
        try:
            # Sanitize folder path for filename
            safe_name = folder_path.replace('/', '_').replace('\\', '_')
            folder_file = folders_dir / f"{safe_name}.json"
            
            with open(folder_file, 'w', encoding='utf-8') as f:
                json.dump(folder_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"   ⚠️  Error migrating folder {folder_path}: {e}")
    
    print(f"✅ Migrated {len(folders)} folders")
    
    # Save index
    index_file = scalable_data_dir / "index.json"
    print(f"💾 Saving index to {index_file}")
    with open(index_file, 'w', encoding='utf-8') as f:
        json.dump(index, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Migration complete!")
    print(f"   📊 Statistics:")
    print(f"      - Documents: {len(index['documents'])}")
    print(f"      - Folders: {len(folders)}")
    print(f"      - Shards: {len(set(entry['shard'] for entry in index['documents'].values()))}")
    print(f"   📁 New database location: {scalable_data_dir}")


async def main():
    """Main migration function."""
    import sys
    
    # Default paths
    base_dir = Path(__file__).resolve().parent.parent.parent.parent
    legacy_data_dir = base_dir / "data" / "json_db"
    scalable_data_dir = base_dir / "data" / "scalable_json_db"
    
    # Allow override via command line
    if len(sys.argv) > 1:
        legacy_data_dir = Path(sys.argv[1])
    if len(sys.argv) > 2:
        scalable_data_dir = Path(sys.argv[2])
    
    # Check if legacy database exists
    if not (legacy_data_dir / "documents.json").exists() and not (legacy_data_dir / "folders.json").exists():
        print(f"⚠️  No legacy database found at {legacy_data_dir}")
        print(f"   Migration not needed or database already migrated.")
        return
    
    # Confirm migration
    print(f"⚠️  This will migrate your database from:")
    print(f"   {legacy_data_dir}")
    print(f"   to:")
    print(f"   {scalable_data_dir}")
    print(f"\n   The original files will NOT be deleted.")
    print(f"   Continue? (yes/no): ", end='')
    
    response = input().strip().lower()
    if response not in ['yes', 'y']:
        print("Migration cancelled.")
        return
    
    # Perform migration
    migrate_legacy_to_scalable(legacy_data_dir, scalable_data_dir)
    
    print(f"\n🎉 Migration successful!")
    print(f"   To use the new database, set:")
    print(f"   DATABASE_TYPE=scalable_json")
    print(f"   JSON_DB_PATH={scalable_data_dir}")


if __name__ == "__main__":
    asyncio.run(main())

