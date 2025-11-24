# AI Document Vault

A prototype document management system that uses AI to automatically summarize and format uploaded documents.

## Features
- **Document Upload**: Drag and drop interface for uploading files (PDF, Text, Markdown).
- **AI Processing**: Automatically generates a concise summary and a clean Markdown version of the document using Anthropic's Claude.
- **Document Explorer**: Browse and manage your uploaded documents.
- **Dual View**: View the original file alongside the AI-generated insights.

## Tech Stack
- **Backend**: FastAPI (Python), Uvicorn
- **Frontend**: React, Vite, Tailwind CSS, Lucide Icons
- **AI**: Anthropic Claude API

## Setup & Running

### Prerequisites
- Node.js (v18+)
- Python (v3.10+)
- Anthropic API Key (Optional, but required for real AI features)

### 1. Backend Setup
Navigate to the `backend` directory:
```bash
cd backend
```

Create a virtual environment and install dependencies:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Set your API key (optional):
```bash
export ANTHROPIC_API_KEY="your_api_key_here"
# Or create a .env file with ANTHROPIC_API_KEY=...
```

Start the server:
```bash
uvicorn main:app --reload --port 8000
```

### 2. Frontend Setup
Navigate to the `frontend` directory:
```bash
cd frontend
```

Install dependencies:
```bash
npm install
```

Start the development server:
```bash
npm run dev
```

The application will be available at `http://localhost:3000` (or the port shown in the terminal).

## Architecture
- **FastAPI Backend**: Handles file uploads, stores files locally in `uploads/`, and manages the background task queue for AI processing.
- **React Frontend**: Polling-based UI that updates document status in real-time. Uses Tailwind for styling.
- **AI Integration**: Extracts text from PDFs/Text files and sends it to Claude Haiku for fast summarization and formatting.

## Notes
- If no API key is provided, the system will use a **Mock AI** response for demonstration purposes.
- PDF text extraction is basic; for complex PDFs, a more robust OCR solution (like Tesseract or Amazon Textract) would be needed.
