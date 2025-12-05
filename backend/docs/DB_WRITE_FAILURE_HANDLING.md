# Database Write Failure Handling

## Overview

This document describes how the system handles cases where AI processing succeeds but database write fails.

## Problem Statement

When AI processing completes successfully but the database write fails, we need to:
1. Preserve the expensive AI results (summary, markdown, tags, embedding)
2. Allow retry of database write without re-running AI processing
3. Provide recovery mechanism for lost results
4. Handle transient vs permanent database failures

## Implementation

### Retry Logic

The system implements automatic retry with exponential backoff:

1. **First Attempt**: Immediate database write
2. **Retry 1**: Wait 2 seconds, retry
3. **Retry 2**: Wait 4 seconds, retry
4. **Retry 3**: Wait 8 seconds, retry
5. **After 3 failures**: Store results for manual recovery

### Result Storage

When database write fails after all retries, AI results are stored in two places:

1. **Document Metadata** (preferred): `ai_results_recovery` field
2. **Recovery File** (fallback): `{doc_id}_ai_results_recovery.json`

### Status Flags

Documents with DB write failures are marked with:

- `status: "failed"`
- `db_write_failed: true`
- `ai_processing_succeeded: true` (indicates AI succeeded)
- `ai_results_pending: true` (indicates results stored for recovery)
- `error: "Database write failed: ..."`

### Recovery Endpoint

A dedicated endpoint allows manual recovery:

```http
POST /api/v1/documents/{doc_id}/recover-db-write
```

## Flow Diagram

```
AI Processing Success
    ↓
Prepare DB Update Data
    ↓
Attempt DB Write (with retries)
    ├─→ Success → Status: "completed"
    │
    └─→ Failure (after 3 retries)
        ↓
    Store AI Results
    ├─→ In document metadata (ai_results_recovery)
    └─→ In recovery file (fallback)
        ↓
    Mark Document
    ├─→ status: "failed"
    ├─→ db_write_failed: true
    ├─→ ai_processing_succeeded: true
    └─→ ai_results_pending: true
        ↓
    Manual Recovery Available
    └─→ POST /documents/{doc_id}/recover-db-write
```

## API Usage

### Recover Database Write

```bash
# Recover a document with failed DB write
POST /api/v1/documents/{doc_id}/recover-db-write

# Response (success)
{
    "message": "Database write recovery successful",
    "status": "completed",
    "doc_id": "abc-123"
}

# Response (failure)
{
    "detail": "Failed to recover database write for document abc-123. AI results may have been lost."
}
```

### Check for Pending Recoveries

```bash
# Get all documents with pending AI results
GET /api/v1/documents?status=failed&ai_results_pending=true
```

## Recovery Data Structure

```json
{
    "summary": "Document summary...",
    "markdown_content": "# Document\n\nContent...",
    "markdown_filename": "abc-123_processed.md",
    "tags": ["tag1", "tag2"],
    "extracted_fields": {},
    "embedding": [0.1, 0.2, ...],
    "stored_at": "2024-01-01T12:00:00",
    "db_error": "Database connection timeout"
}
```

## Error Handling

### Transient Failures

- **Connection timeout**: Retried automatically
- **Lock timeout**: Retried automatically
- **Temporary unavailability**: Retried automatically

### Permanent Failures

- **Invalid data format**: Not retried (data issue)
- **Permission denied**: Not retried (access issue)
- **Document not found**: Not retried (data issue)

### Critical Failures

If even the error status update fails:
- Results are still stored in recovery file
- Critical log entry created
- Manual intervention required

## Best Practices

### For Developers

1. **Always check recovery data** before retrying AI processing
2. **Clean up recovery files** after successful recovery
3. **Monitor failed DB writes** to identify database issues
4. **Log all recovery attempts** for debugging

### For Operations

1. **Monitor documents** with `ai_results_pending: true`
2. **Set up alerts** for DB write failures
3. **Regular recovery** of pending results
4. **Database health checks** to prevent failures

## Monitoring

### Metrics to Track

- Documents with `db_write_failed: true`
- Documents with `ai_results_pending: true`
- Recovery success rate
- Average retry count before failure
- Recovery file count

### Logging

All DB write failures are logged with:
- Document ID
- Error message
- Retry attempt number
- Recovery data location

## Future Enhancements

- [ ] Automatic background recovery job
- [ ] Recovery queue for batch processing
- [ ] Database health monitoring
- [ ] Automatic retry after DB recovery
- [ ] Recovery dashboard/UI

## Example Scenarios

### Scenario 1: Transient DB Failure

```
1. AI processing completes successfully
2. DB write fails (connection timeout)
3. Retry 1: Wait 2s, retry → Success
4. Status: "completed"
```

### Scenario 2: Persistent DB Failure

```
1. AI processing completes successfully
2. DB write fails (all 3 retries fail)
3. Results stored in recovery file
4. Status: "failed", ai_results_pending: true
5. Manual recovery via endpoint
6. Status: "completed"
```

### Scenario 3: Critical Failure

```
1. AI processing completes successfully
2. DB write fails
3. Error status update also fails
4. Results stored in recovery file only
5. Critical log entry created
6. Manual intervention required
```

