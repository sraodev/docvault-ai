from pathlib import Path
import shutil
from fastapi import UploadFile
from pypdf import PdfReader

class FileService:
    @staticmethod
    def save_upload(file: UploadFile, destination: Path):
        with open(destination, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

    @staticmethod
    def extract_text(file_path: Path) -> str:
        text_content = ""
        try:
            if file_path.suffix.lower() == ".pdf":
                try:
                    reader = PdfReader(file_path)
                    for page in reader.pages:
                        text_content += page.extract_text() + "\n"
                except Exception as e:
                    print(f"Error reading PDF: {e}")
                    return "Error extracting text from PDF."
            else:
                # Assume text/md file
                try:
                    text_content = file_path.read_text(encoding="utf-8", errors="ignore")
                except Exception as e:
                    print(f"Error reading text file: {e}")
                    return "Error reading file content."
        except Exception as e:
             print(f"General file error: {e}")
             return "Error processing file."
        
        return text_content

    @staticmethod
    def save_markdown(content: str, path: Path):
        path.write_text(content, encoding="utf-8")

    @staticmethod
    def delete_file(path: Path):
        try:
            if path and path.exists():
                path.unlink()
        except Exception as e:
            print(f"Error deleting file {path}: {e}")
