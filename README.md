# DocVault AI

A modern document management system that uses AI to automatically summarize and format uploaded documents. Features virtual folder organization, real-time processing status, and a clean, responsive interface.

## Features

- **Document Upload**: Multiple upload methods:
  - **"+ New" dropdown**: File Upload and Folder Upload options
  - **Drag-and-drop**: Drag files or folders directly onto the main DriveView area
  - Supports PDF, TXT, MD, and other document formats
- **AI Processing**: Automatically generates concise summaries and clean Markdown versions using AI providers (OpenRouter, Anthropic Claude, or Mock)
- **Virtual Folder Organization**: Organize documents into virtual folders/categories stored as metadata
- **Folder Explorer View**: Tree-structured navigation to browse documents by folder
- **Document Viewer**: View original files, AI-generated summaries, and processed markdown
- **Breadcrumbs Navigation**: Clear navigation path showing Documents > Folder > Document
- **Real-time Status Updates**: Live updates on document processing status (processing, completed, failed)
- **File Type Badges**: Visual indicators for document types (PDF, DOCX, etc.)
- **Responsive Design**: Mobile-friendly interface with adaptive layouts

## Tech Stack

### Backend
- **FastAPI** (Python 3.10+) - Modern, fast web framework
- **Uvicorn** - ASGI server for running FastAPI
- **PyPDF2** - PDF text extraction
- **python-dotenv** - Environment variable management
- **OpenRouter API** - AI service provider (default)
- **Anthropic API** - Alternative AI service provider

### Frontend
- **React 18** - UI library
- **TypeScript** - Type-safe JavaScript
- **Vite** - Fast build tool and dev server
- **Tailwind CSS** - Utility-first CSS framework
- **Lucide React** - Icon library
- **Axios** - HTTP client for API requests

## Project Structure

```
DocVaultAI/
├── backend/
│   ├── app/
│   │   ├── core/
│   │   │   └── config.py          # Configuration and environment variables
│   │   ├── models/
│   │   │   └── document.py        # Document metadata Pydantic models
│   │   ├── routers/
│   │   │   └── documents.py      # API endpoints for document operations
│   │   ├── services/
│   │   │   ├── ai_service.py      # AI service orchestration
│   │   │   ├── file_service.py    # File operations (save, extract, delete)
│   │   │   └── providers.py      # AI provider implementations (OpenRouter, Anthropic, Mock)
│   │   └── main.py                # FastAPI app initialization
│   ├── main.py                    # Application entry point
│   ├── requirements.txt           # Python dependencies
│   ├── uploads/                   # Uploaded files storage directory
│   └── tests/                     # Backend tests
│
└── frontend/
    ├── src/
    │   ├── components/
    │   │   ├── DocumentList.tsx        # List view of documents
    │   │   ├── DocumentViewer.tsx      # Document detail viewer with tabs
    │   │   ├── FolderExplorerView.tsx  # Tree-structured folder view
    │   │   ├── Sidebar.tsx              # Main sidebar with upload and navigation
    │   │   └── UploadArea.tsx          # File upload component with folder selection
    │   ├── hooks/
    │   │   └── useDocuments.ts         # Custom hook for document state management
    │   ├── services/
    │   │   └── api.ts                  # API client functions
    │   ├── types/
    │   │   └── index.ts                # TypeScript type definitions
    │   ├── App.tsx                     # Main application component
    │   └── main.tsx                    # Application entry point
    ├── package.json                    # Node.js dependencies
    └── vite.config.ts                  # Vite configuration
```

## Setup & Running

### Prerequisites

- **Node.js** (v18 or higher)
- **Python** (v3.10 or higher)
- **AI API Key** (Optional - OpenRouter or Anthropic API key)

### Backend Setup

1. **Navigate to the backend directory:**
   ```bash
   cd backend
   ```

2. **Create a virtual environment:**
   ```bash
   python3 -m venv venv
   # On macOS/Linux:
   source venv/bin/activate
   # On Windows:
   venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   
   Create a `.env` file in the `backend` directory (optional):
   ```env
   OPENROUTER_API_KEY=your_openrouter_api_key_here
   # OR
   ANTHROPIC_API_KEY=your_anthropic_api_key_here
   AI_PROVIDER=openrouter  # Options: openrouter, anthropic, mock (default: openrouter)
   ```
   
   Or export environment variables:
   ```bash
   export OPENROUTER_API_KEY="your_api_key_here"
   export AI_PROVIDER="openrouter"
   ```

5. **Start the backend server:**
   ```bash
   # Using the entry point
   python main.py
   
   # OR using uvicorn directly
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

   The backend API will be available at `http://localhost:8000`
   - API Documentation: `http://localhost:8000/docs`
   - Alternative docs: `http://localhost:8000/redoc`

### Frontend Setup

1. **Navigate to the frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Start the development server:**
   ```bash
   npm run dev
   ```

   The frontend will be available at `http://localhost:5173` (or the port shown in the terminal)

### Running Both Services

To run both services simultaneously, open two terminal windows:

**Terminal 1 (Backend):**
```bash
cd backend
source venv/bin/activate  # or venv\Scripts\activate on Windows
python main.py
```

**Terminal 2 (Frontend):**
```bash
cd frontend
npm run dev
```

## Architecture & Design Choices

### Backend Architecture

**Layered Architecture:**
- **Routers Layer** (`routers/documents.py`): Handles HTTP requests and responses
- **Services Layer** (`services/`): Business logic for AI processing and file operations
- **Models Layer** (`models/document.py`): Data models and validation using Pydantic
- **Core Layer** (`core/config.py`): Configuration and environment management

**Key Design Decisions:**

1. **Pluggable AI Providers**: Implemented a provider pattern allowing easy switching between OpenRouter, Anthropic, and Mock AI services. This makes the system flexible and testable.

2. **Background Processing**: Document processing (text extraction, AI summarization) runs asynchronously using FastAPI's `BackgroundTasks` to avoid blocking the API response.

3. **In-Memory Storage**: Currently uses an in-memory dictionary (`documents_db`) for document metadata. This is suitable for prototyping but should be replaced with a persistent database (PostgreSQL, MongoDB) for production.

4. **Virtual Folders**: Folders are stored as metadata rather than physical directory structures. This approach:
   - Simplifies file management (no need to move physical files)
   - Allows documents to belong to multiple folders (future enhancement)
   - Follows the pattern used by modern cloud storage services (Google Drive, Dropbox)

5. **Route Ordering**: Specific routes (`/documents/folders/list`) are defined before parameterized routes (`/documents/{doc_id}`) to ensure FastAPI matches them correctly.

6. **Cross-Platform Path Handling**: File paths are normalized to handle both Unix (`/`) and Windows (`\`) path separators.

### Frontend Architecture

**Component Structure:**
- **Container Components**: `App.tsx`, `Sidebar.tsx` - Manage state and orchestrate child components
- **Presentational Components**: `DocumentList.tsx`, `DocumentViewer.tsx`, `UploadArea.tsx` - Focus on UI rendering
- **Custom Hooks**: `useDocuments.ts` - Encapsulates document state management and API interactions

**Key Design Decisions:**

1. **Polling for Updates**: The frontend polls the backend every 5 seconds to update document processing status. This is simple and effective for prototyping, but WebSockets would be better for production.

2. **View Modes**: Two view modes (List and Folder Explorer) provide flexibility in how users navigate documents.

3. **Responsive Design**: Mobile-first approach with adaptive layouts. Folder tree collapses on mobile devices.

4. **Type Safety**: Full TypeScript implementation ensures type safety across the application.

5. **Error Handling**: Comprehensive error handling with user-friendly error messages and fallback states.

6. **Breadcrumbs**: Provides clear navigation context, showing the user's location in the document hierarchy.

## API Endpoints

### Document Operations

- `POST /upload` - Upload a document with optional folder assignment
  - Body: `multipart/form-data` with `file` and optional `folder` field
  - Returns: Document metadata

- `GET /documents` - Get all documents, optionally filtered by folder
  - Query params: `folder` (optional) - Filter by folder name
  - Returns: List of document metadata

- `GET /documents/{doc_id}` - Get a specific document by ID
  - Returns: Document metadata

- `DELETE /documents/{doc_id}` - Delete a document and its associated files
  - Returns: Success message

### Folder Operations

- `GET /documents/folders/list` - Get list of all available folders
  - Returns: `{ "folders": ["folder1", "folder2", ...] }`

### File Operations

- `GET /files/{filename}` - Download or view an uploaded file
  - Returns: File content

## Assumptions

1. **File Storage**: Files are stored locally in the `uploads/` directory. For production, consider cloud storage (S3, Azure Blob Storage, etc.).

2. **Database**: Currently uses in-memory storage. Production should use a persistent database.

3. **Authentication**: No authentication/authorization implemented. Assume single-user or add authentication for production.

4. **File Size Limits**: No explicit file size limits enforced. Consider adding limits based on your infrastructure.

5. **AI Provider**: Defaults to OpenRouter. Falls back to Mock AI if no API key is provided.

6. **PDF Processing**: Uses basic PDF text extraction. Complex PDFs (scanned images, complex layouts) may require OCR.

7. **Concurrent Processing**: Background tasks run sequentially per document. For high volume, consider a task queue (Celery, RQ).

8. **Error Recovery**: Failed document processing is marked as "failed" but not automatically retried.

9. **Folder Names**: Folder names are case-sensitive and stored as provided. No validation or normalization.

10. **File Types**: Supports PDF, TXT, and MD files. Other file types may not process correctly.

## Development Notes

### Adding a New AI Provider

1. Create a new provider class in `backend/app/services/providers.py` implementing the `AIProvider` interface
2. Add provider selection logic in `AIService` class
3. Update environment variable handling in `core/config.py`

### Adding File Type Support

1. Update `FileService.extract_text()` in `backend/app/services/file_service.py`
2. Add appropriate text extraction library (e.g., `python-docx` for Word documents)
3. Update frontend file type detection in components

### Production Considerations

- **Database**: Replace in-memory storage with PostgreSQL or MongoDB
- **File Storage**: Move to cloud storage (S3, Azure Blob Storage)
- **Authentication**: Add JWT or OAuth2 authentication
- **Rate Limiting**: Implement rate limiting for API endpoints
- **Caching**: Add Redis for caching frequently accessed documents
- **Monitoring**: Add logging and monitoring (Sentry, DataDog)
- **WebSockets**: Replace polling with WebSockets for real-time updates
- **Task Queue**: Use Celery or RQ for background processing
- **Load Balancing**: Add load balancing for high availability
- **CI/CD**: Set up continuous integration and deployment pipelines

## Testing

### Backend Tests

Run backend tests:
```bash
cd backend
pytest tests/
```

### Frontend Tests

Run frontend tests (if configured):
```bash
cd frontend
npm test
```

## License

This project is a prototype/demo application. Please review and update the license as needed for your use case.

## Contributing

This is a prototype application. For production use, consider:
- Adding comprehensive test coverage
- Implementing proper error handling and logging
- Adding authentication and authorization
- Setting up CI/CD pipelines
- Adding monitoring and alerting
- Implementing data backup and recovery strategies
