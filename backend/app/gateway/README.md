# API Gateway Module

The API Gateway module provides a centralized gateway layer for the DocVault AI API. It handles request routing, middleware management, API versioning, error handling, and request/response transformation.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    API Gateway                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │  Middleware  │  │  Versioning  │  │   Routing    │ │
│  │  - CORS      │  │  - v1, v2    │  │  - Registry  │ │
│  │  - Rate Limit│  │  - Detection │  │  - Metadata  │ │
│  │  - Logging   │  │              │  │              │ │
│  │  - Error     │  │              │  │              │ │
│  │  - RequestID │  │              │  │              │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │   API Routers        │
              │  - Documents         │
              │  - Uploads           │
              │  - Folders          │
              │  - Search           │
              │  - Files            │
              └──────────────────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │   Services Layer      │
              │  - Business Logic     │
              └──────────────────────┘
```

## Features

### 1. **Centralized Middleware**
- **Request ID Middleware**: Adds unique request IDs for tracing
- **Request Logging Middleware**: Logs all requests/responses with timing
- **Error Handling Middleware**: Centralized error handling and response formatting
- **CORS Middleware**: Cross-origin resource sharing configuration
- **Rate Limiting**: Protection against API abuse

### 2. **API Versioning**
- URL-based versioning: `/api/v1/documents`
- Header-based versioning: `X-API-Version: v1`
- Accept header versioning: `application/vnd.api.v1+json`
- Backward compatibility: Routes available without version prefix

### 3. **Route Registry**
- Centralized route registration with metadata
- Route statistics and summaries
- Tag-based route organization
- Deprecated route tracking

### 4. **Error Handling**
- Standardized error responses
- Business exception to HTTP exception mapping
- Development vs production error details
- Request ID in error responses

## Usage

### Basic Setup

```python
from app.gateway import APIGateway, APIVersion
from app.routers import documents, uploads

# Initialize gateway
gateway = APIGateway(
    title="DocVault AI API",
    description="Document management system",
    version="1.0.0"
)

# Setup middleware
gateway.setup_middleware()

# Register routers
gateway.register_router(
    documents.router,
    prefix="/api/v1",
    tags=["Documents"],
    version=APIVersion.V1
)

# Get FastAPI app
app = gateway.get_app()
```

### Registering Routes

```python
# With versioning
gateway.register_router(
    router,
    prefix="/api/v1",
    tags=["Documents"],
    version=APIVersion.V1
)

# Without versioning (backward compatibility)
gateway.register_router(
    router,
    tags=["Documents"]
)
```

### Accessing Request ID

The request ID is automatically added to all requests and available in handlers:

```python
from fastapi import Request

@router.get("/documents")
async def get_documents(request: Request):
    request_id = request.state.request_id
    logger.info(f"Processing request {request_id}")
    # ...
```

### Error Handling

Business exceptions are automatically converted to HTTP exceptions:

```python
from app.api.exceptions import DocumentNotFoundError

@router.get("/documents/{doc_id}")
async def get_document(doc_id: str):
    doc = await db_service.get_document(doc_id)
    if not doc:
        raise DocumentNotFoundError(f"Document {doc_id} not found")
    # Automatically converted to 404 HTTPException
```

## API Endpoints

### Versioned Endpoints
- `/api/v1/documents/*` - Document operations
- `/api/v1/upload/*` - File uploads
- `/api/v1/documents/folders/*` - Folder operations
- `/api/v1/search/*` - Search operations
- `/api/v1/files/*` - File operations

### Legacy Endpoints (Backward Compatibility)
- `/documents/*` - Document operations
- `/upload/*` - File uploads
- `/documents/folders/*` - Folder operations
- `/search/*` - Search operations
- `/files/*` - File operations

### Health Check Endpoints
- `/` - API information
- `/health` - Liveness probe (Docker/Kubernetes)
- `/ready` - Readiness probe (Kubernetes)

## Middleware Order

Middleware is applied in the following order:

1. **Error Handling** (outermost) - Catches all exceptions
2. **Request ID** - Adds request ID for tracing
3. **Request Logging** - Logs requests/responses
4. **CORS** - Handles cross-origin requests
5. **Rate Limiting** - Enforced by slowapi

## Configuration

Gateway behavior can be configured via environment variables:

- `ENVIRONMENT` - Set to "production" to disable docs
- `CORS_ORIGINS` - Comma-separated list of allowed origins
- `RATE_LIMIT_ENABLED` - Enable/disable rate limiting
- `RATE_LIMIT_PER_MINUTE` - Requests per minute limit
- `RATE_LIMIT_PER_HOUR` - Requests per hour limit

## Adding New API Versions

To add a new API version (e.g., v2):

1. Add version to `APIVersion` enum:
```python
class APIVersion(str, Enum):
    V1 = "v1"
    V2 = "v2"  # New version
```

2. Register routers with new version:
```python
gateway.register_router(
    v2_router,
    prefix="/api/v2",
    tags=["Documents"],
    version=APIVersion.V2
)
```

3. Update version detection logic if needed (handled automatically)

## Request/Response Flow

1. **Request arrives** → Gateway receives request
2. **Request ID added** → Unique ID assigned for tracing
3. **Request logged** → Method, path, query params logged
4. **CORS checked** → Origin validated
5. **Rate limit checked** → Request count validated
6. **Route matched** → Version detected, router selected
7. **Handler executed** → Business logic runs
8. **Response logged** → Status code, duration logged
9. **Response returned** → With request ID header

## Error Response Format

All errors follow a standardized format:

```json
{
    "error": "Error message",
    "status_code": 404,
    "path": "/api/v1/documents/123",
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "detail": "Additional error details (development only)"
}
```

## Benefits

1. **Separation of Concerns**: Gateway handles cross-cutting concerns, routers handle business logic
2. **Versioning**: Easy to maintain multiple API versions
3. **Observability**: Request IDs and logging for debugging
4. **Error Handling**: Consistent error responses across the API
5. **Scalability**: Middleware can be optimized independently
6. **Maintainability**: Centralized configuration and routing

## Future Enhancements

- Authentication/Authorization middleware
- Request/Response transformation
- API key management
- Request throttling per user
- API analytics and metrics
- Circuit breaker pattern
- Request caching

