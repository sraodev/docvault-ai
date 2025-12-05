# AI Processing Failure Handling

## Overview

This document describes how the system handles cases where file upload succeeds but AI processing fails.

## Problem Statement

When a file is successfully uploaded but AI processing fails, the document should:
1. Be marked with appropriate status
2. Store error details for debugging
3. Allow retry of AI processing
4. Preserve partial results (if any)
5. Not block the upload process

## Implementation

### Status Handling

The system uses the following statuses for documents:

- **`ready`**: Document uploaded, ready for AI processing (or AI unavailable but retryable)
- **`processing`**: AI processing in progress
- **`completed`**: AI processing successful
- **`failed`**: AI processing failed (can be retried)

### Error Types

#### 1. AI Service Unavailable (Credits/API Key)
- **Status**: `ready` (retryable)
- **Fields**: `ai_error`, `ai_processing_failed: true`
- **Behavior**: Document remains usable, can retry when service available

#### 2. Critical AI Failure
- **Status**: `failed`
- **Fields**: `error`, `ai_error`, `ai_processing_failed: true`
- **Behavior**: Document marked as failed, can be manually retried

#### 3. Text Extraction Failure
- **Status**: `failed`
- **Fields**: `error`
- **Behavior**: Document cannot be processed (file format issue)

### Error Storage

Documents store error information in multiple fields:

```python
{
    "status": "failed",
    "error": "AI processing failed: Summary generation error: ...",
    "ai_error": "Summary generation error: ...",
    "ai_processing_failed": True,
    "ai_retry_count": 1,
    "ai_next_retry_time": "2024-01-01T12:00:00"
}
```

### Retry Mechanism

#### Automatic Retry
- Failed documents can be retried via `/documents/{doc_id}/process` endpoint
- Status is reset from `failed` to `ready` before retry
- Error flags are cleared on successful retry

#### Manual Retry
Users can manually retry failed documents:
1. Call `POST /documents/{doc_id}/process`
2. System checks if document is failed
3. Resets status to `ready` and clears error flags
4. Starts new processing attempt

### Partial Results Preservation

When AI processing fails partially:
- **Summary available**: Stored even if markdown failed
- **Tags available**: Always generated (AI or rule-based fallback)
- **Embedding available**: Generated if possible
- **Markdown**: Only saved if both summary and markdown succeed

### Example Flow

```
1. File Upload Success
   └─> Document created with status: "processing"

2. AI Processing Starts
   └─> Status: "processing"

3a. AI Processing Success
    └─> Status: "completed"
    └─> Summary, markdown, tags, embedding stored

3b. AI Service Unavailable (Credits)
    └─> Status: "ready"
    └─> ai_error: "Insufficient credits"
    └─> ai_processing_failed: true
    └─> Tags still generated (rule-based)

3c. AI Processing Failed (Critical)
    └─> Status: "failed"
    └─> error: "AI processing failed: ..."
    └─> ai_error: "..."
    └─> ai_processing_failed: true
    └─> Partial results preserved if available

4. Retry Failed Document
   └─> POST /documents/{doc_id}/process
   └─> Status reset: "failed" -> "ready"
   └─> Error flags cleared
   └─> New processing attempt starts
```

## API Endpoints

### Process Document (with Retry Support)

```http
POST /api/v1/documents/{doc_id}/process
```

**Behavior:**
- If status is `failed`: Automatically resets to `ready` and retries
- If status is `processing`: Returns immediately (already processing)
- If status is `completed`: Returns immediately (already done)
- If status is `ready`: Starts processing

**Response:**
```json
{
    "message": "AI processing started",
    "status": "processing"
}
```

## Error Handling Best Practices

### For Developers

1. **Always check status before processing**
   ```python
   if doc.get("status") == "failed":
       # Allow retry
   ```

2. **Store error details**
   ```python
   await db_service.update_document(doc_id, {
       "status": "failed",
       "error": error_message,
       "ai_error": ai_specific_error
   })
   ```

3. **Preserve partial results**
   ```python
   update_data = {
       "summary": summary,  # Keep if available
       "tags": tags,  # Always generated
       "status": "failed"  # But mark as failed
   }
   ```

### For Users

1. **Check document status** after upload
2. **Retry failed documents** using the process endpoint
3. **Review error messages** in document metadata
4. **Contact support** if retries continue to fail

## Monitoring

### Logging

All AI failures are logged with:
- Document ID
- Error message
- Error type (unavailable vs critical)
- Retry count

### Metrics to Track

- Documents with `status: "failed"`
- Documents with `ai_processing_failed: true`
- Retry success rate
- Average retry count before success

## Future Enhancements

- [ ] Automatic retry with exponential backoff
- [ ] Retry queue for failed documents
- [ ] Email notifications for permanent failures
- [ ] Dashboard for monitoring failed documents
- [ ] Batch retry endpoint

