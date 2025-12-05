# Idempotency Implementation

## Overview

The API Gateway now supports idempotency keys to prevent duplicate operations. This ensures that retried requests return the same result without re-executing the operation.

## How It Works

### 1. Client Sends Request with Idempotency Key

```bash
POST /api/v1/documents/{doc_id}/process
Headers:
  Idempotency-Key: abc-123-def-456
```

### 2. Server Behavior

- **First Request**: Processes normally and caches the response
- **Duplicate Request**: Returns cached response immediately (no re-processing)

### 3. Response Headers

All responses include:
- `Idempotency-Key`: Echo of the provided key
- `X-Idempotency-Cached`: `true` if cached, `false` if new

## Supported Operations

Idempotency keys work for all **state-modifying** HTTP methods:
- `POST` - Create operations
- `PUT` - Update operations
- `PATCH` - Partial updates
- `DELETE` - Delete operations

**GET** requests are not cached (they're already idempotent).

## Storage Backend

### Redis (Preferred)
- Uses Redis DB 3 for idempotency keys
- Distributed across multiple server instances
- TTL: 24 hours (configurable)

### In-Memory Fallback
- Used if Redis is unavailable
- Limited to single server instance
- Auto-cleanup when cache exceeds 10,000 entries

## Configuration

### Environment Variables

```bash
# Redis configuration (for distributed idempotency)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=  # Optional
```

### TTL Configuration

Default TTL is 24 hours. Can be customized in middleware initialization:

```python
IdempotencyMiddleware(app, ttl=3600)  # 1 hour
```

## Usage Examples

### Python (requests)

```python
import requests
import uuid

# Generate idempotency key
idempotency_key = str(uuid.uuid4())

# First request
response1 = requests.post(
    "http://localhost:8000/api/v1/documents/123/process",
    headers={"Idempotency-Key": idempotency_key}
)

# Duplicate request (returns cached response)
response2 = requests.post(
    "http://localhost:8000/api/v1/documents/123/process",
    headers={"Idempotency-Key": idempotency_key}
)

# Both responses are identical
assert response1.json() == response2.json()
assert response2.headers["X-Idempotency-Cached"] == "true"
```

### JavaScript (fetch)

```javascript
const idempotencyKey = crypto.randomUUID();

// First request
const response1 = await fetch('http://localhost:8000/api/v1/documents/123/process', {
  method: 'POST',
  headers: {
    'Idempotency-Key': idempotencyKey
  }
});

// Duplicate request
const response2 = await fetch('http://localhost:8000/api/v1/documents/123/process', {
  method: 'POST',
  headers: {
    'Idempotency-Key': idempotencyKey
  }
});

// Check if cached
const isCached = response2.headers.get('X-Idempotency-Cached') === 'true';
```

### cURL

```bash
# Generate key
IDEMPOTENCY_KEY=$(uuidgen)

# First request
curl -X POST http://localhost:8000/api/v1/documents/123/process \
  -H "Idempotency-Key: $IDEMPOTENCY_KEY"

# Duplicate request (returns cached)
curl -X POST http://localhost:8000/api/v1/documents/123/process \
  -H "Idempotency-Key: $IDEMPOTENCY_KEY"
```

## Key Requirements

1. **Format**: Any string up to 128 characters
2. **Uniqueness**: Should be unique per operation
3. **Persistence**: Keys are cached for 24 hours
4. **Scope**: Keys are scoped to method + path (different endpoints don't collide)

## Best Practices

1. **Generate Unique Keys**: Use UUIDs or similar
2. **Include in Retries**: Always include the same key when retrying
3. **Handle Cached Responses**: Check `X-Idempotency-Cached` header
4. **Key Scope**: Different operations should use different keys

## Error Handling

- **400 Bad Request**: If idempotency key is too long (>128 chars)
- **Caching Errors**: If caching fails, request still processes normally
- **Error Responses**: Not cached (only 2xx responses are cached)

## Implementation Details

### Cache Key Generation

Cache keys are generated from:
- HTTP Method
- Request Path
- Idempotency Key

This ensures different endpoints don't collide.

### Response Caching

Only successful responses (2xx) are cached:
- `200 OK` - Cached
- `201 Created` - Cached
- `204 No Content` - Cached
- `400 Bad Request` - Not cached
- `500 Internal Error` - Not cached

## Monitoring

Idempotency operations are logged:
- Cache hits: `Idempotency: Returning cached response for key...`
- Cache misses: `Idempotency: Processing new request with key...`

## Limitations

1. **In-Memory Mode**: Limited to single server instance
2. **TTL**: Cached responses expire after 24 hours
3. **Body Size**: Very large responses may impact performance
4. **Error Responses**: Not cached (only success responses)

## Future Enhancements

- [ ] Configurable TTL per endpoint
- [ ] Idempotency key validation (format checking)
- [ ] Metrics/monitoring for cache hit rates
- [ ] Support for streaming responses
- [ ] Idempotency key rotation/cleanup

