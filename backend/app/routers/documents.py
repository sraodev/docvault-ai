from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException, Form
from typing import List, Dict, Optional
import uuid
from datetime import datetime
from pathlib import Path
from fastapi.responses import FileResponse

from ..models.document import DocumentMetadata
from ..services.ai_service import AIService
from ..services.file_service import FileService
from ..core.config import UPLOAD_DIR

router = APIRouter()

# In-memory database (Mock)
documents_db: Dict[str, dict] = {}

ai_service = AIService()
file_service = FileService()

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
    folder: Optional[str] = Form(None)
):
    """
    Upload a document with optional folder/category assignment.
    Folder is stored as metadata for virtual folder organization.
    """
    try:
        doc_id = str(uuid.uuid4())
        file_ext = Path(file.filename).suffix
        save_filename = f"{doc_id}{file_ext}"
        save_path = UPLOAD_DIR / save_filename

        # Save file
        file_service.save_upload(file, save_path)

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
            "folder": normalized_folder  # Store folder as metadata
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

@router.get("/documents", response_model=List[DocumentMetadata])
async def get_documents(folder: Optional[str] = None):
    """
    Get all documents, optionally filtered by folder.
    """
    if folder:
        return [doc for doc in documents_db.values() if doc.get("folder") == folder]
    return list(documents_db.values())

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
    return documents_db[doc_id]

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
