from pathlib import Path
import shutil
from fastapi import UploadFile, HTTPException, status
from pypdf import PdfReader

class FileService:
    @staticmethod
    def save_upload(file: UploadFile, destination: Path):
        try:
            with open(destination, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        except Exception as e:
            print(f"Error saving upload: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Could not save file: {str(e)}"
            )

    @staticmethod
    def extract_text(file_path: Path) -> str:
        text_content = ""
        try:
            if not file_path.exists():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="File not found for extraction"
                )

            if file_path.suffix.lower() == ".pdf":
                try:
                    reader = PdfReader(file_path)
                    for page in reader.pages:
                        text_content += page.extract_text() + "\n"
                except Exception as e:
                    print(f"Error reading PDF: {e}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Error extracting text from PDF: {str(e)}"
                    )
            else:
                # Assume text/md file
                try:
                    text_content = file_path.read_text(encoding="utf-8", errors="ignore")
                except Exception as e:
                    print(f"Error reading text file: {e}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Error reading text file: {str(e)}"
                    )
        except HTTPException:
            raise
        except Exception as e:
             print(f"General file error: {e}")
             raise HTTPException(
                 status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                 detail=f"Error processing file: {str(e)}"
             )
        
        return text_content

    @staticmethod
    def save_markdown(content: str, path: Path):
        try:
            path.write_text(content, encoding="utf-8")
        except Exception as e:
            print(f"Error saving markdown: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Could not save markdown: {str(e)}"
            )

    @staticmethod
    def delete_file(path: Path):
        try:
            if path and path.exists():
                path.unlink()
        except Exception as e:
            print(f"Error deleting file {path}: {e}")
            # Log but maybe don't raise for cleanup tasks? 
            # Or raise if it's critical. For now, let's raise to be safe.
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Could not delete file: {str(e)}"
            )
