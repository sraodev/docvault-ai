# DocVault AI

A modern document management system that uses AI to automatically summarize and format uploaded documents. Features virtual folder organization, semantic search, real-time processing status, and a clean, responsive interface.

## Features

### 📤 Document Upload & Management
- **Multiple Upload Methods**:
  - **"+ New" dropdown**: File Upload and Folder Upload options
  - **Drag-and-drop**: Drag files or folders directly onto the main DriveView area
  - **Bulk Upload**: Upload multiple files and folders simultaneously
  - **ZIP Support**: Extract and upload files from ZIP archives while preserving folder structure
- **Supported File Formats**:
  - ✅ **PDF** - Full text extraction with `pypdf`
  - ✅ **DOCX** - Full text extraction (paragraphs and tables) with `python-docx`
  - ✅ **DOC** - Full text extraction with `textract` (requires antiword/LibreOffice)
  - ✅ **TXT, MD** - Plain text files
  - ⚠️ **RTF, ODT** - Storage only (text extraction coming soon)
- **Upload Features**:
  - Circular progress indicators (small, elegant design)
  - Duplicate detection via SHA-256 checksum
  - Real-time upload progress tracking
  - Folder structure preservation

### 🤖 AI Processing & Intelligence
- **AI-Powered Document Processing**:
  - **Summary Generation**: Concise, informative summaries of document content
  - **Markdown Conversion**: Clean, structured Markdown versions of documents
  - **Tag Extraction**: Automatic tag/keyword extraction from content
  - **Document Classification**: AI categorizes documents (Invoice, Agreement, Resume, Medical Record, etc.)
  - **Field Extraction**: Structured data extraction (e.g., invoice amounts, resume skills, contract dates)
  - **Embedding Generation**: Vector embeddings for semantic search
- **AI Providers**:
  - **OpenRouter** (default) - Access to multiple AI models including Claude, GPT-4, etc.
  - **Anthropic Claude** - Direct API integration
  - **Mock Provider** - Graceful fallback when API keys unavailable or credits insufficient
- **Smart Features**:
  - Automatic document categorization with color-coded tags
  - Field extraction based on document type
  - Semantic understanding of document content

### 🔍 Search & Discovery
- **Semantic Search**: AI-powered semantic search across all documents using embeddings and cosine similarity
  - Natural language queries (e.g., "invoices above ₹50,000", "resume containing Python")
  - Relevance scoring and ranking
  - Falls back to text-based search if embeddings unavailable
- **Real-time Search**: Debounced queries (500ms) for instant results
- **Advanced Filtering**: Filter by folder, document type, date range, and extracted fields

### 📁 Organization & Navigation
- **Virtual Folder Organization**: Organize documents into virtual folders/categories stored as metadata
  - No physical file movement required
  - Documents can belong to multiple folders (future enhancement)
  - Google Drive-style organization
- **Document Classification**: AI-powered document categorization
  - Automatic categorization (Invoice, Agreement, Resume, Medical Record, Research Paper, Bank Statement, Code, etc.)
  - Color-coded category tags displayed on file cards
  - Classification stored in `document_category` field for filtering and organization
- **Folder Explorer View**: Tree-structured navigation to browse documents by folder
  - Hides empty folders automatically
  - Collapsible folder tree
  - Breadcrumbs navigation
- **File Cards**: Google Drive-style square cards with:
  - Document category tags (color-coded by type)
  - Last modified date (smart formatting: "Today", "Yesterday", "X days ago")
  - File size and type indicators
  - Status indicators (uploading, processing, completed)

### 👁️ Document Viewer
- **Multi-tab Interface**:
  - **Original**: View original file content
  - **Summary**: AI-generated document summary
  - **Markdown**: Clean Markdown version
  - **Tags**: View all extracted tags and document category
- **Document Details**:
  - File metadata (size, upload date, modified date)
  - Extracted fields (for invoices, resumes, contracts)
  - Document classification
  - Folder location

### 🎨 User Interface
- **Modern Design**: Clean, Google Drive-inspired interface
- **Responsive Layout**: Mobile-friendly with adaptive layouts
- **View Modes**: Grid view (cards) and List view
- **Status Indicators**: Color-coded status (uploading=red, processing=orange, completed=blue)
- **Progress Tracking**: Small circular progress indicators for uploads and processing
- **Empty State Handling**: Empty folders automatically hidden
- **Breadcrumbs**: Clear navigation path (Documents > Folder > Document)

### 🏗️ Architecture & Scalability
- **Scalable Database**: Shard-based JSON database architecture supporting 500,000+ documents
  - 1,000-document shards for optimal performance
  - Global index for O(1) lookups
  - Write-ahead logging for durability
  - LRU cache (5,000 items)
  - Background compaction
- **Plug-and-Play Storage**: Switch between storage backends without code changes
  - **Local Filesystem**: Default for development
  - **AWS S3**: Production cloud storage
  - **Supabase Storage**: Alternative cloud storage
- **Plug-and-Play Database**: Switch between database backends
  - **Scalable JSON**: Production-ready, handles 500K+ documents
  - **Legacy JSON**: Simple file-based storage
  - **Memory**: In-memory for testing

## Tech Stack

### Backend
- **FastAPI** (Python 3.11+) - Modern, fast web framework
- **Uvicorn** - ASGI server for running FastAPI
- **pypdf** - PDF text extraction
- **python-docx** - DOCX text extraction (paragraphs and tables)
- **textract** - DOC text extraction (optional, requires antiword/LibreOffice)
- **python-dotenv** - Environment variable management
- **openai** - OpenAI SDK (used for OpenRouter API)
- **anthropic** - Anthropic Claude API SDK
- **boto3** - AWS S3 storage adapter
- **supabase** - Supabase Storage adapter
- **slowapi** - Rate limiting middleware
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
- **clsx** & **tailwind-merge** - Conditional CSS class utilities
- **framer-motion** - Animation library (optional)

## Project Structure

```
DocVaultAI/
├── backend/                           # Backend API server (FastAPI)
│   ├── app/
│   │   ├── api/                       # API layer (DTOs, exceptions, mappers)
│   │   │   ├── dto.py                 # Data Transfer Objects
│   │   │   ├── exceptions.py         # Custom API exceptions
│   │   │   └── mappers.py            # Data mapping utilities
│   │   ├── core/                      # Core configuration
│   │   │   └── config.py             # Environment variables and configuration
│   │   ├── domain/                    # Domain layer
│   │   │   ├── entities.py           # Domain entities
│   │   │   └── value_objects.py      # Value objects
│   │   ├── models/                    # Data models
│   │   │   └── document.py           # Document metadata Pydantic models
│   │   ├── routers/                   # API endpoints (HTTP layer)
│   │   │   ├── documents.py          # Document CRUD operations
│   │   │   ├── files.py              # File serving endpoints
│   │   │   ├── folders.py            # Folder operations
│   │   │   ├── search.py             # Search endpoints
│   │   │   ├── uploads.py            # Upload endpoints
│   │   │   └── dependencies.py       # Shared dependencies
│   │   ├── services/                  # Business logic layer
│   │   │   ├── ai_service.py         # AI service orchestration
│   │   │   ├── file_service.py       # File operations (save, extract, delete)
│   │   │   ├── providers.py          # AI provider implementations (OpenRouter, Anthropic, Mock)
│   │   │   ├── document_service.py   # Document business logic
│   │   │   ├── document_processing_service.py  # Document processing pipeline
│   │   │   ├── folder_service.py     # Folder business logic
│   │   │   ├── search_service.py     # Search business logic
│   │   │   ├── upload_service.py     # Upload orchestration
│   │   │   ├── upload_queue.py       # Upload queue management
│   │   │   ├── upload_processor.py   # Background upload processing
│   │   │   ├── cache_service.py      # Redis caching (optional)
│   │   │   ├── message_queue.py      # Message queue integration
│   │   │   ├── tasks.py              # Background task definitions
│   │   │   ├── database/             # Database adapters (plug-and-play)
│   │   │   │   ├── base.py          # Database interface
│   │   │   │   ├── factory.py       # Database factory pattern
│   │   │   │   ├── json_adapter.py  # Legacy JSON adapter
│   │   │   │   ├── scalable_json_adapter.py  # Shard-based JSON database
│   │   │   │   ├── memory_adapter.py  # In-memory adapter (testing)
│   │   │   │   └── migrate_to_scalable.py  # Migration utilities
│   │   │   └── storage/              # Storage adapters (plug-and-play)
│   │   │       ├── base.py          # Storage interface
│   │   │       ├── factory.py       # Storage factory pattern
│   │   │       ├── local_storage.py  # Local filesystem storage
│   │   │       ├── s3_storage.py     # AWS S3 storage
│   │   │       ├── supabase_storage.py  # Supabase Storage
│   │   │       └── migrate_storage.py  # Storage migration utilities
│   │   ├── repositories/             # Repository pattern (data access abstraction)
│   │   │   ├── interfaces.py        # Repository interfaces
│   │   │   ├── document_repository.py  # Document repository
│   │   │   └── folder_repository.py   # Folder repository
│   │   ├── middleware/               # FastAPI middleware
│   │   │   └── rate_limit.py        # Rate limiting middleware
│   │   ├── utils/                     # Utility functions
│   │   │   ├── checksum.py          # File checksum calculation (SHA-256)
│   │   │   ├── tag_extractor.py     # Rule-based tag extraction
│   │   │   ├── document_utils.py    # Document utilities
│   │   │   ├── search_utils.py      # Search utilities
│   │   │   └── validators.py        # Input validation
│   │   └── main.py                   # FastAPI app initialization
│   ├── data/
│   │   └── json_db/                  # Scalable JSON database storage
│   │       ├── index.json            # Global document index (O(1) lookups)
│   │       ├── documents/            # Shard-based document storage (1K docs/shard)
│   │       │   ├── 0-999/
│   │       │   ├── 1000-1999/
│   │       │   └── ...
│   │       ├── folders/              # Folder metadata
│   │       └── logs/                 # Write-ahead logs (WAL)
│   ├── uploads/                       # Uploaded files storage (local)
│   ├── venv/                          # Python virtual environment (gitignored)
│   ├── main.py                        # Application entry point
│   ├── requirements.txt               # Python dependencies
│   └── .env                           # Environment variables (gitignored)
│
├── frontend/                          # Frontend React application
│   ├── src/
│   │   ├── components/                # React components
│   │   │   ├── DriveView.tsx         # Main drive view (grid/list, search, cards)
│   │   │   ├── DocumentList.tsx      # List view of documents
│   │   │   ├── DocumentViewer.tsx    # Document detail viewer (tabs: original, summary, markdown, tags)
│   │   │   ├── FolderExplorerView.tsx  # Tree-structured folder view
│   │   │   ├── Sidebar.tsx           # Main sidebar (upload, folder tree, navigation)
│   │   │   ├── UploadArea.tsx        # File upload component (drag-and-drop)
│   │   │   └── ProgressBar.tsx       # Circular progress indicators (small/medium/large)
│   │   ├── hooks/                     # Custom React hooks
│   │   │   └── useDocuments.ts       # Document state management and API interactions
│   │   ├── services/                  # API client layer
│   │   │   └── api.ts                # Axios-based API client functions
│   │   ├── types/                     # TypeScript type definitions
│   │   │   └── index.ts              # Document, Folder, and other type definitions
│   │   ├── utils/                     # Utility functions
│   │   │   ├── checksum.ts           # Client-side checksum calculation
│   │   │   ├── filename.ts            # Filename extraction and utilities
│   │   │   └── formatSize.ts         # File size formatting (KB, MB, GB)
│   │   ├── App.tsx                    # Main application component
│   │   ├── main.tsx                   # Application entry point
│   │   └── index.css                  # Global styles
│   ├── node_modules/                  # Node.js dependencies (gitignored)
│   ├── package.json                   # Node.js dependencies and scripts
│   ├── vite.config.ts                 # Vite configuration
│   └── tsconfig.json                  # TypeScript configuration
│
├── docs/                              # Documentation
│   ├── QUICK_START.md                 # Quick start guide
│   ├── SYSTEM_DESIGN_AND_SCALABILITY_ANALYSIS.md  # Architecture and scalability
│   ├── DATABASE_ARCHITECTURE.md      # Database design
│   ├── STORAGE_ARCHITECTURE.md       # Storage adapters
│   ├── UPLOAD_ARCHITECTURE.md        # Upload pipeline
│   ├── FILE_FORMAT_SUPPORT_ANALYSIS.md  # Supported file formats
│   ├── PRODUCTION_AI_PROCESSING_RECOMMENDATION.md  # Production recommendations
│   ├── CODING_GUIDELINES.md          # Code standards
│   ├── CODE_WALKTHROUGH.md           # Code structure guide
│   └── README.md                     # Documentation index
│
├── deploy/                            # Deployment configurations
│   ├── k8s/                           # Kubernetes manifests
│   ├── nginx/                         # Nginx configuration
│   └── docker-compose.yml             # Docker Compose setup
│
├── .gitignore                         # Git ignore rules
├── README.md                          # This file
└── LICENSE                            # License file
```

### Key Directories Explained

**Backend (`backend/app/`):**
- **`routers/`**: Thin HTTP layer - handles requests/responses, delegates to services
- **`services/`**: Thick business logic layer - contains all application logic
- **`repositories/`**: Data access abstraction layer
- **`models/`**: Pydantic models for data validation
- **`utils/`**: Reusable utility functions

**Frontend (`frontend/src/`):**
- **`components/`**: React UI components
- **`hooks/`**: Custom React hooks for state management
- **`services/`**: API client functions
- **`types/`**: TypeScript type definitions
- **`utils/`**: Client-side utility functions

## Setup & Running

### Prerequisites

- **Node.js** (v18 or higher) - [Download](https://nodejs.org/)
- **Python** (v3.11 or higher) - [Download](https://www.python.org/downloads/)
- **Git** - [Download](https://git-scm.com/)
- **AI API Key** (Optional) - Get from [OpenRouter](https://openrouter.ai/) or [Anthropic](https://www.anthropic.com/)

### Quick Start

```bash
# Clone the repository
git clone https://github.com/sraodev/docvault-ai.git
cd DocVaultAI

# Backend setup (Terminal 1)
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # Edit .env with your API keys
python main.py

# Frontend setup (Terminal 2)
cd frontend
npm install
npm run dev
```

### Backend Setup (Detailed)

1. **Navigate to backend directory:**
   ```bash
   cd backend
   ```

2. **Create and activate virtual environment:**
   ```bash
   # Create virtual environment
   python3 -m venv venv
   
   # Activate virtual environment
   # On macOS/Linux:
   source venv/bin/activate
   # On Windows:
   venv\Scripts\activate
   ```

3. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   
   Create a `.env` file in the `backend` directory (or copy from `.env.example` if available):
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
   
   # Server Configuration
   PORT=8000  # Optional: default is 8000
   HOST=0.0.0.0  # Optional: default is 0.0.0.0
   
   # Rate Limiting (Optional)
   RATE_LIMIT_ENABLED=false  # Enable/disable rate limiting (default: false)
   
   # CORS Configuration (Optional)
   CORS_ORIGINS=http://localhost:3000,http://localhost:5173  # Comma-separated origins
   
   # Environment
   ENVIRONMENT=development  # Options: development, production (affects API docs visibility)
   ```
   
   **Note**: If you don't have an AI API key, the system will use the Mock provider (limited functionality but works for testing).

5. **Initialize database (first run only):**
   ```bash
   # Database will be automatically initialized on first run
   # No manual setup required
   ```

6. **Start the backend server:**
   ```bash
   # Option 1: Using the entry point (recommended)
   python main.py
   
   # Option 2: Using uvicorn directly
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

   **Backend API will be available at:**
   - API Base URL: `http://localhost:8000`
   - Interactive API Docs: `http://localhost:8000/docs` (Swagger UI)
   - Alternative Docs: `http://localhost:8000/redoc` (ReDoc)

### Frontend Setup (Detailed)

1. **Navigate to frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install Node.js dependencies:**
   ```bash
   npm install
   # or
   yarn install
   # or
   pnpm install
   ```

3. **Configure API endpoint (if needed):**
   
   The frontend is configured to connect to `http://localhost:8000` by default.
   To change this, edit `frontend/src/services/api.ts`:
   ```typescript
   const API_URL = process.env.VITE_API_URL || 'http://localhost:8000'
   ```
   
   Or create a `.env` file in the `frontend` directory:
   ```env
   VITE_API_URL=http://localhost:8000
   ```

4. **Start the development server:**
   ```bash
   npm run dev
   # or
   yarn dev
   # or
   pnpm dev
   ```

   **Frontend will be available at:**
   - Development URL: `http://localhost:3000` (or the port shown in terminal)
   - Vite will automatically open your browser

### Running Both Services

**Option 1: Two Terminal Windows (Recommended)**

**Terminal 1 - Backend:**
```bash
cd backend
source venv/bin/activate  # On Windows: venv\Scripts\activate
python main.py
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

**Option 2: Using a Process Manager**

You can use `concurrently` or `npm-run-all` to run both services:

```bash
# Install concurrently globally
npm install -g concurrently

# Run both services
concurrently "cd backend && source venv/bin/activate && python main.py" "cd frontend && npm run dev"
```

### Verification

1. **Backend is running** if you see:
   ```
   INFO:     Uvicorn running on http://0.0.0.0:8000
   INFO:     Application startup complete.
   ```

2. **Frontend is running** if you see:
   ```
   VITE v5.x.x  ready in xxx ms
   ➜  Local:   http://localhost:3000/
   ```

3. **Test the API** by visiting `http://localhost:8000/docs` - you should see the Swagger UI

4. **Test the frontend** by visiting `http://localhost:3000` - you should see the DocVault AI interface

### Troubleshooting

**Backend Issues:**
- **Port already in use**: Change `PORT` in `.env` or kill the process using port 8000
- **Module not found**: Ensure virtual environment is activated and dependencies are installed
- **Database errors**: Check `JSON_DB_PATH` in `.env` and ensure directory exists
- **Storage errors**: Check `STORAGE_TYPE` and corresponding configuration

**Frontend Issues:**
- **Cannot connect to API**: Verify backend is running and `VITE_API_URL` is correct
- **Port already in use**: Vite will automatically use the next available port
- **Build errors**: Clear `node_modules` and reinstall: `rm -rf node_modules && npm install`

**Common Solutions:**
```bash
# Backend: Reinstall dependencies
cd backend
source venv/bin/activate
pip install --upgrade -r requirements.txt

# Frontend: Clear cache and reinstall
cd frontend
rm -rf node_modules package-lock.json
npm install
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
   - Documents are automatically classified by AI (Invoice, Agreement, Resume, etc.) with category tags displayed on file cards
   - Note: Smart Folders (automatic folder organization) is currently disabled - documents are classified but not auto-organized into folders

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

- `POST /documents/{doc_id}/process` - Manually trigger AI processing for a document
  - Returns: Success message
  - Background task: Generates summary, markdown, tags, classification, and embeddings

- `POST /documents/{doc_id}/regenerate-summary` - Regenerate AI summary for a document
  - Returns: Success message
  - Background task: Regenerates summary and markdown

- `POST /documents/regenerate-all-summaries` - Regenerate summaries for all documents
  - Query params: `limit` (optional) - Maximum number of documents to process
  - Returns: Success message with count
  - Background task: Processes documents in batch

- `GET /documents/missing-summaries` - Get documents that are missing summaries
  - Query params: `limit` (optional) - Maximum number of documents to return
  - Returns: List of documents without summaries

### Folder Operations

- `GET /documents/folders/list` - Get list of all available folders
  - Returns: `{ "folders": ["folder1", "folder2", ...] }`

- `POST /documents/folders` - Create a new folder
  - Body: `multipart/form-data` with `folder_name` field
  - Returns: Folder metadata

- `DELETE /documents/folders/{folder_path}` - Delete a folder and its contents
  - Path param: `folder_path` - Full folder path (e.g., "Invoices/2024")
  - Returns: Success message
  - Note: Deletes all documents in the folder

- `PUT /documents/folders/{folder_path}/move` - Move/rename a folder
  - Path param: `folder_path` - Current folder path
  - Body: `multipart/form-data` with `new_folder_path` (optional)
  - Returns: Success message
  - If `new_folder_path` is empty, moves folder to root

### File Operations

- `GET /files/{filename}` - Download or view an uploaded file
  - Returns: File content (text content for .md files)
  - Supports: PDF, DOCX, DOC, TXT, MD, and other formats

### Upload Operations

- `POST /upload/bulk` - Upload multiple files and folders
  - Body: `multipart/form-data` with `files[]` array and optional `folder` field
  - Supports ZIP file extraction with folder structure preservation
  - Returns: List of uploaded documents with status

- `POST /upload/check-duplicate` - Check if a file with given checksum exists
  - Body: `multipart/form-data` with `checksum` (SHA-256)
  - Returns: `{ "exists": true/false, "document": {...} }` if duplicate found

- `POST /upload/check-duplicates` - Check multiple checksums at once
  - Body: `multipart/form-data` with `checksums[]` array
  - Returns: List of duplicate checksums with document metadata

### Search & Discovery

- `GET /documents/search` - Semantic search across documents
  - Query params: 
    - `q` (required) - Search query
    - `limit` (optional, default: 10) - Maximum results
    - `min_similarity` (optional, default: 0.3) - Minimum similarity threshold (0.0-1.0)
  - Returns: Matching documents with similarity scores
  - Supports natural language queries (e.g., "invoices above ₹50,000", "resume containing Python")

- `GET /documents/tags` - Get all unique tags across documents
  - Returns: `{ "tags": [...], "tag_counts": {...}, "total_tags": N }`
  - Tags sorted by frequency, then alphabetically

- `GET /documents/tags/{tag}` - Get documents with specific tag
  - Path param: `tag` - Tag name (URL encoded)
  - Returns: List of documents containing the tag

### Health & Status

- `GET /` - Root endpoint - API information
  - Returns: `{ "message": "...", "version": "1.0.0", "status": "healthy" }`

- `GET /health` - Health check endpoint (for container orchestration)
  - Returns: `{ "status": "healthy", "database": "connected", "services": "initialized" }`
  - Returns 503 if unhealthy

- `GET /ready` - Readiness check endpoint (for Kubernetes)
  - Returns: `{ "ready": true }`
  - Returns 503 if not ready

## Assumptions

1. **File Storage**: Defaults to local filesystem storage in the `uploads/` directory. Can be configured to use AWS S3 or Supabase Storage via environment variables.

2. **Database**: Uses scalable JSON database by default (supports 500,000+ documents). Can be configured to use legacy JSON or in-memory storage via `DATABASE_TYPE` environment variable.

3. **Authentication**: No authentication/authorization implemented. Assume single-user or add authentication for production.

4. **File Size Limits**: No explicit file size limits enforced. Consider adding limits based on your infrastructure.

5. **AI Provider**: Defaults to OpenRouter. Falls back to Mock AI if no API key is provided or if API calls fail (e.g., insufficient credits).

6. **PDF Processing**: Uses basic PDF text extraction. Complex PDFs (scanned images, complex layouts) may require OCR.

7. **Concurrent Processing**: Background tasks run asynchronously with upload queue management. For very high volume, consider a dedicated task queue (Celery, RQ). Current implementation processes documents sequentially using FastAPI BackgroundTasks.

8. **Error Recovery**: Failed document processing is marked as "failed" but not automatically retried. The system gracefully handles AI service failures by falling back to Mock provider.

9. **Folder Names**: Folder names are case-sensitive and stored as provided. No validation or normalization.

10. **File Types**: 
    - **Fully Supported**: PDF, TXT, MD, DOCX (text extraction), DOC (text extraction with textract)
    - **Storage Only**: RTF, ODT (stored but text extraction not yet implemented)
    - **Not Supported**: Images (no OCR), Excel, PowerPoint, CSV (coming soon)

11. **Semantic Search**: Requires embeddings to be generated during document processing. Falls back to text-based search if embeddings are unavailable.

## Recent Improvements

### Latest Features (2025)

- **Document Classification**: AI-powered document categorization with color-coded tags on file cards
  - Categories: Invoice, Agreement/Contract, Resume, Medical Record, Research Paper, Bank Statement, Code, etc.
  - Automatic classification during document processing
  - Visual indicators at bottom-right of file cards

- **Enhanced File Cards**: Google Drive-style square cards with:
  - Category tags (bottom-right corner)
  - Last modified date with smart formatting
  - Smaller, elegant progress indicators (24px)
  - Better visual hierarchy and spacing

- **Full DOCX & DOC Support**: Complete text extraction for Word documents
  - DOCX: Extracts paragraphs and tables using `python-docx`
  - DOC: Extracts text using `textract` (requires system dependencies)
  - AI processing enabled for all Word documents

- **Improved UI/UX**:
  - Smaller circular progress indicators (24px) positioned at top-right
  - Smart date formatting (relative dates for recent files)
  - Better card layout and spacing
  - Color-coded category tags

### Previous Highlights

- **Scalable Database**: Migrated from in-memory storage to shard-based JSON database supporting 500,000+ documents
- **Semantic Search**: Added AI-powered semantic search using embeddings and cosine similarity
- **Document Classification**: AI-powered automatic document categorization with color-coded tags
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
- **Rate Limiting**: Rate limiting middleware already implemented using `slowapi` (configurable via `RATE_LIMIT_ENABLED` environment variable)
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

## Documentation

Comprehensive documentation is available in the `docs/` directory:

- **[Quick Start Guide](docs/QUICK_START.md)** - Get started quickly with setup instructions
- **[System Design & Scalability Analysis](docs/SYSTEM_DESIGN_AND_SCALABILITY_ANALYSIS.md)** - Complete system architecture, scalability analysis, and performance metrics
- **[Database Architecture](docs/DATABASE_ARCHITECTURE.md)** - Database design, plug-and-play architecture, and Scalable JSON details
- **[Storage Architecture](docs/STORAGE_ARCHITECTURE.md)** - Storage adapters (Local, S3, Supabase) and cloud storage setup
- **[Upload Architecture](docs/UPLOAD_ARCHITECTURE.md)** - Upload queue management and processing pipeline
- **[File Format Support](docs/FILE_FORMAT_SUPPORT_ANALYSIS.md)** - Supported formats, extraction methods, and implementation guides
- **[Production AI Processing](docs/PRODUCTION_AI_PROCESSING_RECOMMENDATION.md)** - Recommendations for production AI processing (Celery, Redis)
- **[Coding Guidelines](docs/CODING_GUIDELINES.md)** - Code standards, best practices, and development workflow
- **[Code Walkthrough](docs/CODE_WALKTHROUGH.md)** - Understanding the codebase structure and navigation
- **[Reading Code Guide](docs/READING_CODE_GUIDE.md)** - How to read and understand the codebase
- **[OpenRouter Setup](docs/OPENROUTER_SETUP.md)** - Setting up OpenRouter API for AI processing

## Performance & Scalability

### Current Capacity
- **Database**: 500,000+ documents efficiently with shard-based architecture
- **Storage**: Unlimited (depends on storage backend - Local, S3, or Supabase)
- **Concurrent Processing**: Sequential AI processing using FastAPI BackgroundTasks
- **Search**: Semantic search with embeddings (O(n) complexity), falls back to text search
- **File Formats**: Full support for PDF, DOCX, DOC, TXT, MD with text extraction

### Scalability Recommendations
- **AI Processing**: Consider Celery + Redis for production (see `docs/PRODUCTION_AI_PROCESSING_RECOMMENDATION.md`)
  - Current: Sequential processing with BackgroundTasks
  - Recommended: Celery workers for parallel AI processing
- **Database**: Current scalable JSON database handles production workloads (500K+ documents)
  - Can migrate to PostgreSQL/MongoDB for advanced querying if needed
- **Storage**: Already supports cloud storage (S3, Supabase) - configure via environment variables
- **Caching**: Optional Redis cache for frequently accessed documents and search results
- **Load Balancing**: Add load balancer (nginx, AWS ALB) for high availability
- **Monitoring**: Add application monitoring (Sentry, DataDog) and logging

### Performance Characteristics
- **Read Operations**: O(1) via global index lookup + cache hit
- **Write Operations**: O(1) index update + O(1) shard write + WAL append
- **Search**: O(n) for semantic search (with embedding pre-computation), O(n) for text search
- **Scalability**: Handles 500,000+ documents efficiently with predictable performance

## License

This project is a prototype/demo application. Please review and update the license as needed for your use case.

## Contributing

This is a prototype application. For production use, consider:
- Adding comprehensive test coverage (unit tests, integration tests)
- Implementing proper error handling and logging
- Adding authentication and authorization (JWT, OAuth2)
- Setting up CI/CD pipelines (GitHub Actions, GitLab CI)
- Adding monitoring and alerting (Sentry, DataDog, Prometheus)
- Implementing data backup and recovery strategies
- Migrating to Celery for AI processing (see production recommendations)
- Adding support for more file formats (Excel, PowerPoint, Images with OCR)
- Implementing rate limiting and API throttling
- Adding WebSocket support for real-time updates (replace polling)
