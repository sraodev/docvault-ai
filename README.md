# DocVault AI

A modern document management system that uses AI to automatically summarize and format uploaded documents. Features virtual folder organization, semantic search, real-time processing status, and a clean, responsive interface.

## Features

- **Document Upload**: Multiple upload methods:
  - **"+ New" dropdown**: File Upload and Folder Upload options
  - **Drag-and-drop**: Drag files or folders directly onto the main DriveView area
  - Supports PDF, TXT, MD, DOCX, and other document formats
  - Circular progress indicators for upload and processing status
- **AI Processing**: Automatically generates concise summaries, tags, and clean Markdown versions using AI providers (OpenRouter, Anthropic Claude, or Mock)
  - Graceful fallback to Mock provider when API keys are unavailable or credits are insufficient
  - Smart document classification and field extraction
- **Semantic Search**: AI-powered semantic search across all documents using embeddings and cosine similarity
  - Falls back to text-based search if semantic search is unavailable
  - Real-time search with debounced queries
- **Smart Folders**: AI-powered automatic document organization into smart folders based on document classification
- **Virtual Folder Organization**: Organize documents into virtual folders/categories stored as metadata
- **Folder Explorer View**: Tree-structured navigation to browse documents by folder
  - Hides empty folders automatically
  - Visual distinction for Smart Folders
- **Document Viewer**: View original files, AI-generated summaries, processed markdown, and tags
- **Breadcrumbs Navigation**: Clear navigation path showing Documents > Folder > Document
- **Real-time Status Updates**: Live updates on document processing status (uploading, processing, completed, failed)
- **File Type Badges**: Visual indicators for document types (PDF, DOCX, etc.)
- **Responsive Design**: Mobile-friendly interface with adaptive layouts
- **Scalable Database**: Shard-based JSON database architecture supporting hundreds of thousands of documents
- **Plug-and-Play Storage**: Switch between local filesystem, AWS S3, or Supabase Storage without code changes

## Tech Stack

### Backend
- **FastAPI** (Python 3.11+) - Modern, fast web framework
- **Uvicorn** - ASGI server for running FastAPI
- **PyPDF2** - PDF text extraction
- **python-dotenv** - Environment variable management
- **OpenRouter API** - AI service provider (default) with embedding support
- **Anthropic API** - Alternative AI service provider
- **Scalable JSON Database** - Shard-based file database supporting 500,000+ documents
- **Storage Adapters** - Pluggable storage backends (Local, S3, Supabase)
- **NumPy** - Vector operations for semantic search

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
│   │   │   └── config.py              # Configuration and environment variables
│   │   ├── domain/
│   │   │   ├── entities.py            # Domain entities
│   │   │   └── value_objects.py       # Value objects
│   │   ├── models/
│   │   │   └── document.py            # Document metadata Pydantic models
│   │   ├── routers/
│   │   │   └── documents.py           # API endpoints for document operations
│   │   ├── services/
│   │   │   ├── ai_service.py           # AI service orchestration
│   │   │   ├── file_service.py        # File operations (save, extract, delete)
│   │   │   ├── providers.py           # AI provider implementations (OpenRouter, Anthropic, Mock)
│   │   │   ├── database/              # Database adapters (JSON, Scalable JSON, Memory)
│   │   │   │   ├── factory.py         # Database factory pattern
│   │   │   │   └── scalable_json_adapter.py  # Shard-based JSON database
│   │   │   ├── storage/               # Storage adapters (Local, S3, Supabase)
│   │   │   │   ├── factory.py         # Storage factory pattern
│   │   │   │   ├── local_storage.py   # Local filesystem storage
│   │   │   │   ├── s3_storage.py      # AWS S3 storage
│   │   │   │   └── supabase_storage.py # Supabase Storage
│   │   │   ├── upload_queue.py        # Upload queue management
│   │   │   └── upload_processor.py    # Background upload processing
│   │   ├── repositories/              # Repository pattern for data access
│   │   │   ├── document_repository.py
│   │   │   └── folder_repository.py
│   │   ├── utils/
│   │   │   ├── checksum.py            # File checksum calculation
│   │   │   └── tag_extractor.py       # Tag extraction utilities
│   │   └── main.py                    # FastAPI app initialization
│   ├── data/
│   │   └── json_db/                   # Scalable JSON database storage
│   │       ├── index.json             # Global document index
│   │       ├── documents/             # Shard-based document storage
│   │       └── folders/               # Folder metadata
│   ├── main.py                        # Application entry point
│   ├── requirements.txt               # Python dependencies
│   ├── uploads/                       # Uploaded files storage directory
│   └── tests/                         # Backend tests
│
└── frontend/
    ├── src/
    │   ├── components/
    │   │   ├── DriveView.tsx          # Main drive view with search and file display
    │   │   ├── DocumentList.tsx       # List view of documents
    │   │   ├── DocumentViewer.tsx     # Document detail viewer with tabs
    │   │   ├── FolderExplorerView.tsx # Tree-structured folder view
    │   │   ├── Sidebar.tsx            # Main sidebar with upload and navigation
    │   │   ├── UploadArea.tsx         # File upload component with folder selection
    │   │   └── ProgressBar.tsx        # Circular progress indicators
    │   ├── hooks/
    │   │   └── useDocuments.ts        # Custom hook for document state management
    │   ├── services/
    │   │   └── api.ts                 # API client functions
    │   ├── types/
    │   │   └── index.ts               # TypeScript type definitions
    │   ├── utils/
    │   │   ├── checksum.ts            # Client-side checksum calculation
    │   │   ├── filename.ts            # Filename utilities
    │   │   └── formatSize.ts          # File size formatting
    │   ├── App.tsx                    # Main application component
    │   └── main.tsx                   # Application entry point
    ├── package.json                   # Node.js dependencies
    └── vite.config.ts                 # Vite configuration
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
   
   Create a `.env` file in the `backend` directory:
   ```env
   # AI Provider Configuration
   OPENROUTER_API_KEY=your_openrouter_api_key_here
   ANTHROPIC_API_KEY=your_anthropic_api_key_here  # Optional
   AI_PROVIDER=openrouter  # Options: openrouter, anthropic, mock (default: openrouter)
   
   # Database Configuration
   DATABASE_TYPE=scalable_json  # Options: scalable_json, json, memory (default: scalable_json)
   JSON_DB_PATH=./data/json_db  # Path to JSON database directory (optional)
   
   # Storage Configuration
   STORAGE_TYPE=local  # Options: local, s3, supabase (default: local)
   LOCAL_STORAGE_DIR=./uploads  # Path to local storage directory (optional)
   
   # S3 Storage Configuration (if STORAGE_TYPE=s3)
   S3_BUCKET_NAME=your-bucket-name
   AWS_ACCESS_KEY_ID=your-access-key
   AWS_SECRET_ACCESS_KEY=your-secret-key
   AWS_REGION=us-east-1
   S3_ENDPOINT_URL=  # Optional: for S3-compatible services (MinIO, etc.)
   
   # Supabase Storage Configuration (if STORAGE_TYPE=supabase)
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=your-supabase-key
   SUPABASE_STORAGE_BUCKET=files  # Default: files
   ```
   
   Or export environment variables:
   ```bash
   export OPENROUTER_API_KEY="your_api_key_here"
   export AI_PROVIDER="openrouter"
   export DATABASE_TYPE="scalable_json"
   export STORAGE_TYPE="local"
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

   The frontend will be available at `http://localhost:3000` (or the port shown in the terminal)

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
# Frontend runs on http://localhost:3000 by default
```

## Architecture & Design Choices

### Backend Architecture

**Layered Architecture:**
- **Routers Layer** (`routers/documents.py`): Handles HTTP requests and responses
- **Services Layer** (`services/`): Business logic for AI processing and file operations
- **Models Layer** (`models/document.py`): Data models and validation using Pydantic
- **Core Layer** (`core/config.py`): Configuration and environment management

**Key Design Decisions:**

1. **Pluggable AI Providers**: Implemented a provider pattern allowing easy switching between OpenRouter, Anthropic, and Mock AI services. The system gracefully falls back to Mock provider when API keys are unavailable or credits are insufficient, ensuring core functionality remains available.

2. **Scalable JSON Database**: Uses a shard-based JSON database architecture that can handle hundreds of thousands of documents efficiently:
   - Documents stored in 1,000-document shards
   - Global index for O(1) lookups
   - Write-ahead logging for durability
   - LRU cache for performance
   - Background compaction for cleanup

3. **Plug-and-Play Storage**: Factory pattern allows switching between storage backends (Local, S3, Supabase) without changing business logic. Storage adapters implement a common interface.

4. **Background Processing**: Document processing (text extraction, AI summarization, embedding generation) runs asynchronously using FastAPI's `BackgroundTasks` and upload queue to avoid blocking the API response.

5. **Semantic Search**: AI-powered semantic search using embeddings and cosine similarity. Falls back to text-based search if embeddings are unavailable.

6. **Virtual Folders**: Folders are stored as metadata rather than physical directory structures. This approach:
   - Simplifies file management (no need to move physical files)
   - Allows documents to belong to multiple folders (future enhancement)
   - Follows the pattern used by modern cloud storage services (Google Drive, Dropbox)
   - Smart Folders automatically organize documents based on AI classification

7. **Route Ordering**: Specific routes (`/documents/folders/list`) are defined before parameterized routes (`/documents/{doc_id}`) to ensure FastAPI matches them correctly.

8. **Cross-Platform Path Handling**: File paths are normalized to handle both Unix (`/`) and Windows (`\`) path separators. Relative paths are used consistently for storage operations.

### Frontend Architecture

**Component Structure:**
- **Container Components**: `App.tsx`, `Sidebar.tsx` - Manage state and orchestrate child components
- **Presentational Components**: `DocumentList.tsx`, `DocumentViewer.tsx`, `UploadArea.tsx` - Focus on UI rendering
- **Custom Hooks**: `useDocuments.ts` - Encapsulates document state management and API interactions

**Key Design Decisions:**

1. **Polling for Updates**: The frontend polls the backend every 5 seconds to update document processing status. This is simple and effective for prototyping, but WebSockets would be better for production.

2. **Semantic Search**: Real-time semantic search with debounced queries (500ms). Falls back to client-side text filtering if semantic search fails.

3. **View Modes**: Two view modes (List and Folder Explorer) provide flexibility in how users navigate documents.

4. **Responsive Design**: Mobile-first approach with adaptive layouts. Folder tree collapses on mobile devices.

5. **Type Safety**: Full TypeScript implementation ensures type safety across the application.

6. **Error Handling**: Comprehensive error handling with user-friendly error messages and fallback states.

7. **Breadcrumbs**: Provides clear navigation context, showing the user's location in the document hierarchy.

8. **Progress Indicators**: Circular progress indicators for upload and processing status, providing clear visual feedback.

9. **Empty Folder Handling**: Empty folders are automatically hidden from the sidebar tree view for cleaner navigation.

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

- `POST /documents/search` - Semantic search across all documents
  - Body: `{ "query": "search text", "limit": 10 }`
  - Returns: List of matching documents with relevance scores

### Folder Operations

- `GET /documents/folders/list` - Get list of all available folders
  - Returns: `{ "folders": ["folder1", "folder2", ...] }`

### File Operations

- `GET /files/{filename}` - Download or view an uploaded file
  - Returns: File content (text content for .md files)

## Assumptions

1. **File Storage**: Defaults to local filesystem storage in the `uploads/` directory. Can be configured to use AWS S3 or Supabase Storage via environment variables.

2. **Database**: Uses scalable JSON database by default (supports 500,000+ documents). Can be configured to use legacy JSON or in-memory storage via `DATABASE_TYPE` environment variable.

3. **Authentication**: No authentication/authorization implemented. Assume single-user or add authentication for production.

4. **File Size Limits**: No explicit file size limits enforced. Consider adding limits based on your infrastructure.

5. **AI Provider**: Defaults to OpenRouter. Falls back to Mock AI if no API key is provided or if API calls fail (e.g., insufficient credits).

6. **PDF Processing**: Uses basic PDF text extraction. Complex PDFs (scanned images, complex layouts) may require OCR.

7. **Concurrent Processing**: Background tasks run asynchronously with upload queue management. For very high volume, consider a dedicated task queue (Celery, RQ).

8. **Error Recovery**: Failed document processing is marked as "failed" but not automatically retried. The system gracefully handles AI service failures by falling back to Mock provider.

9. **Folder Names**: Folder names are case-sensitive and stored as provided. No validation or normalization.

10. **File Types**: Supports PDF, TXT, MD, DOCX, and other text-based files. Other file types may not process correctly.

11. **Semantic Search**: Requires embeddings to be generated during document processing. Falls back to text-based search if embeddings are unavailable.

## Recent Improvements

### Version Highlights

- **Scalable Database**: Migrated from in-memory storage to shard-based JSON database supporting 500,000+ documents
- **Semantic Search**: Added AI-powered semantic search using embeddings and cosine similarity
- **Smart Folders**: Automatic document organization based on AI classification
- **Storage Adapters**: Implemented plug-and-play storage architecture (Local, S3, Supabase)
- **AI Service Resilience**: Graceful fallback to Mock provider when API keys are unavailable or credits are insufficient
- **Enhanced UI**: Circular progress indicators, improved folder navigation, empty folder hiding
- **Path Handling**: Consistent relative path handling across storage operations

## Development Notes

### Adding a New AI Provider

1. Create a new provider class in `backend/app/services/providers.py` implementing the `AIProvider` interface from `backend/app/services/interfaces.py`
2. Implement all required methods: `generate_summary`, `generate_tags`, `classify_document`, `extract_fields`, `generate_embedding`
3. Add provider selection logic in `AIService` class (`backend/app/services/ai_service.py`)
4. Update environment variable handling in `core/config.py`
5. Ensure graceful error handling and fallback to Mock provider

### Adding a New Storage Backend

1. Create a new storage class in `backend/app/services/storage/` implementing the `FileStorageInterface` from `backend/app/services/storage/base.py`
2. Implement all required methods: `save_file`, `get_file`, `delete_file`, `file_exists`, `get_file_url`, `save_text`, `get_text`
3. Register the new storage type in `StorageFactory` (`backend/app/services/storage/factory.py`)
4. Update environment variable handling in `core/config.py`

### Adding a New Database Backend

1. Create a new database adapter in `backend/app/services/database/` implementing the `DatabaseAdapter` interface
2. Implement all required methods for CRUD operations
3. Register the new database type in `DatabaseFactory` (`backend/app/services/database/factory.py`)
4. Update environment variable handling in `core/config.py`

### Adding File Type Support

1. Update `FileService.extract_text()` in `backend/app/services/file_service.py`
2. Add appropriate text extraction library (e.g., `python-docx` for Word documents)
3. Update frontend file type detection in components (`DriveView.tsx`, etc.)
4. Add file type icon and color mapping in frontend components

### Production Considerations

- **Database**: The scalable JSON database supports production workloads, but consider PostgreSQL or MongoDB for multi-user scenarios or advanced querying needs
- **File Storage**: Already supports cloud storage (S3, Supabase). Configure via `STORAGE_TYPE` environment variable
- **Authentication**: Add JWT or OAuth2 authentication
- **Rate Limiting**: Implement rate limiting for API endpoints
- **Caching**: Add Redis for caching frequently accessed documents and search results
- **Monitoring**: Add logging and monitoring (Sentry, DataDog)
- **WebSockets**: Replace polling with WebSockets for real-time updates
- **Task Queue**: Consider Celery or RQ for very high volume scenarios (current upload queue handles moderate loads)
- **Load Balancing**: Add load balancing for high availability
- **CI/CD**: Set up continuous integration and deployment pipelines
- **Backup**: Implement regular backups for the JSON database and file storage

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
