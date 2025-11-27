# DocVault AI - Development Guide

This guide covers local development setup and workflows for DocVault AI.

## Prerequisites

- **Python 3.11+** (recommended: Python 3.11)
- **Node.js 18+** (recommended: Node.js 18 or 20)
- **npm** or **yarn**
- **Git**

## Project Structure

```
DocVaultAI/
├── backend/          # FastAPI backend application
├── frontend/         # React + TypeScript frontend
├── infra/           # Infrastructure as Code (Terraform, etc.)
├── deploy/          # Deployment configurations
│   └── k8s/         # Kubernetes manifests
├── workers/         # Background worker services
└── docs/            # Additional documentation
```

## Quick Start Verification

Run the verification script to check your setup:
```bash
./scripts/verify-setup.sh
```

Or manually verify:
```bash
# Backend
cd backend
source venv/bin/activate
python -c "from app.main import app; print('Backend OK')"

# Frontend
cd frontend
npm run build
```

## Local Development Setup

### Backend Setup

1. **Navigate to backend directory:**
   ```bash
   cd backend
   ```

2. **Create and activate virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**
   Create a `.env` file in the `backend/` directory:
   ```env
   OPENAI_API_KEY=your_openai_api_key_here
   ANTHROPIC_API_KEY=your_anthropic_api_key_here
   # Add other environment variables as needed
   ```

5. **Run the backend server:**
   ```bash
   # Option 1: Using uvicorn directly (recommended)
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

   # Option 2: Using the main.py entry point
   python main.py
   ```

   The backend will be available at `http://localhost:8000`
   
   **Verify it works:**
   ```bash
   curl http://localhost:8000/
   # Should return: {"message":"DocVault AI Backend is running"}
   ```

### Frontend Setup

1. **Navigate to frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Run the development server:**
   ```bash
   # Option 1: Using npm start (alias for dev)
   npm start
   
   # Option 2: Using npm run dev
   npm run dev
   ```

   The frontend will be available at `http://localhost:5173` (Vite default port)
   
   **Verify it works:**
   - Open `http://localhost:5173` in your browser
   - You should see the DocVault AI interface

## Development Workflow

### Running Both Services

**Terminal 1 - Backend:**
```bash
cd backend
source venv/bin/activate  # On Windows: venv\Scripts\activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

### Backend Development

- **API Documentation:** Once the backend is running, visit:
  - Swagger UI: `http://localhost:8000/docs`
  - ReDoc: `http://localhost:8000/redoc`

- **Hot Reload:** The `--reload` flag enables automatic reloading on code changes

- **Testing:**
  ```bash
  cd backend
  pytest tests/
  ```

### Frontend Development

- **Hot Module Replacement:** Vite automatically reloads on file changes

- **Linting:**
  ```bash
  cd frontend
  npm run lint
  ```

- **Building for Production:**
  ```bash
  cd frontend
  npm run build
  ```

## Environment Variables

### Backend (.env file in backend/)

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | OpenAI API key for AI processing | Yes |
| `ANTHROPIC_API_KEY` | Anthropic API key (alternative) | No |
| `UPLOAD_DIR` | Directory for file uploads | No (defaults to `uploads/`) |

### Frontend

The frontend API URL is configured in `frontend/src/services/api.ts`. 
Default: `http://localhost:8000`

## Common Issues

### Backend Issues

**Port already in use:**
```bash
# Find and kill process on port 8000
lsof -ti:8000 | xargs kill -9  # macOS/Linux
# Or change port in uvicorn command
uvicorn app.main:app --reload --port 8001
```

**Module not found errors:**
- Ensure virtual environment is activated
- Reinstall dependencies: `pip install -r requirements.txt`

**CORS errors:**
- Ensure backend CORS middleware allows frontend origin
- Check `backend/app/main.py` for CORS configuration

### Frontend Issues

**Port already in use:**
- Vite will automatically try the next available port
- Or specify port: `npm run dev -- --port 3000`

**API connection errors:**
- Verify backend is running on `http://localhost:8000`
- Check `frontend/src/services/api.ts` for correct API URL

## Database & Storage

Currently, the application uses an in-memory database (dictionary) for document storage. 
Files are stored in the `backend/uploads/` directory.

**For production:**
- Replace in-memory storage with PostgreSQL/MongoDB
- Use cloud storage (S3, GCS) for file storage
- Configure proper database migrations

## Testing

### Backend Tests
```bash
cd backend
pytest tests/ -v
```

### Frontend Tests
```bash
cd frontend
npm test  # If test setup exists
```

## Code Quality

### Backend
- Follow PEP 8 style guide
- Use type hints
- Write docstrings for functions/classes

### Frontend
- Follow ESLint rules
- Use TypeScript for type safety
- Follow React best practices

## Debugging

### Backend Debugging
- Use Python debugger: `import pdb; pdb.set_trace()`
- Check logs in terminal output
- Use FastAPI's automatic API documentation

### Frontend Debugging
- Use React DevTools browser extension
- Check browser console for errors
- Use Vite's error overlay for build issues

## Next Steps

- [ ] Set up PostgreSQL database
- [ ] Configure cloud storage (S3/GCS)
- [ ] Add Redis for caching
- [ ] Set up Celery for background tasks
- [ ] Configure Docker containers
- [ ] Set up CI/CD pipeline
- [ ] Add monitoring and logging

## Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)
- [Vite Documentation](https://vitejs.dev/)
- [TypeScript Documentation](https://www.typescriptlang.org/)

