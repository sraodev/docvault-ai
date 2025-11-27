from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException, Form
from typing import List, Dict, Optional
import uuid
from datetime import datetime
from pathlib import Path
from fastapi.responses import FileResponse
import hashlib

from ..models.document import DocumentMetadata
from ..services.ai_service import AIService
from ..services.file_service import FileService
from ..core.config import UPLOAD_DIR

router = APIRouter()

# In-memory database (Mock)
documents_db: Dict[str, dict] = {}

ai_service = AIService()
file_service = FileService()

def calculate_file_checksum(file_path: Path) -> str:
    """Calculate SHA-256 checksum of a file"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def check_duplicate_by_checksum(checksum: str) -> Optional[dict]:
    """Check if a file with the same checksum already exists"""
    for doc_id, doc in documents_db.items():
        if doc.get("checksum") == checksum:
            return doc
    return None

def process_document_background(doc_id: str, file_path: Path):
    """
    Background task to process document with AI.
    """
    try:
        print(f"Processing document {doc_id}...")
        
        # 1. Extract Text
        text_content = file_service.extract_text(file_path)

        # 2. Generate Summary and Markdown
        summary = ai_service.generate_summary(text_content)
        markdown_content = ai_service.generate_markdown(text_content)

        # 3. Save Markdown
        md_filename = f"{doc_id}_processed.md"
        md_path = UPLOAD_DIR / md_filename
        file_service.save_markdown(markdown_content, md_path)

        # 4. Update DB
        if doc_id in documents_db:
            documents_db[doc_id]["summary"] = summary
            documents_db[doc_id]["markdown_path"] = str(md_path)
            documents_db[doc_id]["status"] = "completed"
        
        print(f"Finished processing {doc_id}")

    except Exception as e:
        print(f"Fatal error processing {doc_id}: {e}")
        if doc_id in documents_db:
            documents_db[doc_id]["status"] = "failed"

@router.post("/upload", response_model=DocumentMetadata)
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    folder: Optional[str] = Form(None),
    checksum: Optional[str] = Form(None)
):
    """
    Upload a document with optional folder/category assignment.
    Folder is stored as metadata for virtual folder organization.
    Checks duplicate files by checksum if provided.
    """
    try:
        doc_id = str(uuid.uuid4())
        file_ext = Path(file.filename).suffix
        save_filename = f"{doc_id}{file_ext}"
        save_path = UPLOAD_DIR / save_filename

        # Save file first to calculate checksum
        file_service.save_upload(file, save_path)
        
        # Get file size
        file_size = save_path.stat().st_size
        
        # Calculate checksum
        file_checksum = checksum or calculate_file_checksum(save_path)
        
        # Check for duplicate
        duplicate_doc = check_duplicate_by_checksum(file_checksum)
        if duplicate_doc:
            # Delete the just uploaded file since it's a duplicate
            file_service.delete_file(save_path)
            raise HTTPException(
                status_code=409,
                detail=f"File '{file.filename}' already exists as '{duplicate_doc['filename']}'"
            )

        # Normalize folder name (trim whitespace, use None for empty strings)
        normalized_folder = folder.strip() if folder and folder.strip() else None

        doc_meta = {
            "id": doc_id,
            "filename": file.filename,
            "upload_date": datetime.now().isoformat(),
            "file_path": str(save_path),
            "status": "processing",
            "summary": None,
            "markdown_path": None,
            "folder": normalized_folder,
            "checksum": file_checksum,
            "size": file_size
        }
        
        documents_db[doc_id] = doc_meta

        # Trigger background processing
        background_tasks.add_task(process_document_background, doc_id, save_path)

        return doc_meta
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in upload_file: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.post("/upload/check-duplicate")
async def check_duplicate(checksum: str = Form(...)):
    """
    Check if a file with the given checksum already exists.
    """
    duplicate_doc = check_duplicate_by_checksum(checksum)
    if duplicate_doc:
        return {
            "is_duplicate": True,
            "document_id": duplicate_doc["id"],
            "filename": duplicate_doc["filename"]
        }
    return {"is_duplicate": False}

@router.post("/upload/check-duplicates")
async def check_duplicates(checksums: List[str] = Form(...)):
    """
    Check multiple checksums at once for duplicates.
    """
    duplicates = []
    for checksum in checksums:
        duplicate_doc = check_duplicate_by_checksum(checksum)
        if duplicate_doc:
            duplicates.append({
                "checksum": checksum,
                "document_id": duplicate_doc["id"],
                "filename": duplicate_doc["filename"]
            })
    return {"duplicates": duplicates}

@router.get("/documents", response_model=List[DocumentMetadata])
async def get_documents(folder: Optional[str] = None):
    """
    Get all documents, optionally filtered by folder.
    Ensures all documents have a size field by calculating it from the file if missing.
    """
    docs = list(documents_db.values())
    
    # Filter by folder if specified
    if folder:
        docs = [doc for doc in docs if doc.get("folder") == folder]
    
    # Ensure all documents have size field
    for doc in docs:
        if "size" not in doc or doc.get("size") is None:
            file_path = Path(doc.get("file_path", ""))
            if file_path.exists():
                try:
                    doc["size"] = file_path.stat().st_size
                except Exception as e:
                    print(f"Error calculating size for {doc.get('id')}: {e}")
                    doc["size"] = None
    
    return docs

@router.get("/documents/folders/list")
async def get_folders():
    """
    Get list of all available folders/categories.
    Returns unique folder names from all documents.
    """
    folders = set()
    for doc in documents_db.values():
        folder = doc.get("folder")
        if folder:
            folders.add(folder)
    return {"folders": sorted(list(folders))}

@router.get("/documents/{doc_id}", response_model=DocumentMetadata)
async def get_document(doc_id: str):
    if doc_id not in documents_db:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc = documents_db[doc_id]
    
    # Ensure document has size field
    if "size" not in doc or doc.get("size") is None:
        file_path = Path(doc.get("file_path", ""))
        if file_path.exists():
            try:
                doc["size"] = file_path.stat().st_size
            except Exception as e:
                print(f"Error calculating size for {doc_id}: {e}")
                doc["size"] = None
    
    return doc

@router.get("/files/{filename}")
async def get_file(filename: str):
    file_path = UPLOAD_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)

@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    if doc_id not in documents_db:
        raise HTTPException(status_code=404, detail="Document not found")
    
    try:
        doc = documents_db[doc_id]
        
        # Delete original file
        if doc.get("file_path"):
            file_service.delete_file(Path(doc["file_path"]))
            
        # Delete markdown file
        if doc.get("markdown_path"):
            file_service.delete_file(Path(doc["markdown_path"]))
            
        # Remove from DB
        del documents_db[doc_id]
        
        return {"message": "Document deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting document {doc_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Deletion failed: {str(e)}")