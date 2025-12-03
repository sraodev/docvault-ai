# Logging Setup Documentation

## Overview

Comprehensive logging has been added to all backend files in DocVault AI. This document describes the logging configuration and usage.

## Logging Configuration

### Centralized Configuration

All logging is configured through `app/core/logging_config.py`:

- **Log Level**: Configurable via `LOG_LEVEL` environment variable (default: INFO)
- **Log Format**: Detailed format with timestamp, module, level, filename, line number, and message
- **Output**: 
  - Console: Simple format for development
  - File: Detailed format saved to `logs/app.log`

### Log Levels

- **DEBUG**: Detailed diagnostic information (development only)
- **INFO**: General informational messages (default)
- **WARNING**: Warning messages for potential issues
- **ERROR**: Error messages with exception details
- **CRITICAL**: Critical errors that may cause application failure

## Usage in Code

### Basic Usage

```python
from ..core.logging_config import get_logger

logger = get_logger(__name__)

# Log messages
logger.debug("Detailed debug information")
logger.info("General information")
logger.warning("Warning message")
logger.error("Error message", exc_info=True)  # Include exception traceback
logger.critical("Critical error")
```

### Examples

```python
# Info logging
logger.info(f"Processing document: {doc_id}")

# Error logging with exception
try:
    result = await process_document(doc_id)
except Exception as e:
    logger.error(f"Failed to process document {doc_id}: {e}", exc_info=True)
    raise

# Debug logging
logger.debug(f"Worker {worker_id} processing task {task_id}")
```

## Files Updated

### Core Files
- ✅ `app/main.py` - Application startup/shutdown, health checks
- ✅ `app/core/logging_config.py` - Centralized logging configuration

### Service Files
- ✅ `app/services/upload_queue.py` - Worker pool and queue management
- ✅ `app/services/file_service.py` - File operations and text extraction
- ✅ `app/services/upload_processor.py` - Individual file upload processing
- ✅ All other service files (57 files total)

### Router Files
- ✅ All router files have logging imports added

### Database & Storage Adapters
- ✅ All database adapters have logging imports added
- ✅ All storage adapters have logging imports added

## Log File Location

Logs are written to:
- **Development**: `backend/logs/app.log`
- **Production**: Configure via `LOG_FILE` environment variable

## Environment Variables

```bash
# Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL=INFO

# Log file path (optional, defaults to logs/app.log)
LOG_FILE=/var/log/docvault/app.log

# Disable file logging (console only)
ENABLE_FILE_LOGGING=false
```

## Best Practices

1. **Use appropriate log levels**:
   - DEBUG: Development debugging
   - INFO: Normal operations, important events
   - WARNING: Recoverable issues, deprecated features
   - ERROR: Exceptions, failures
   - CRITICAL: System failures

2. **Include context**:
   ```python
   # Good
   logger.info(f"Uploaded file: {filename} (size: {size} bytes, doc_id: {doc_id})")
   
   # Bad
   logger.info("File uploaded")
   ```

3. **Use exc_info for exceptions**:
   ```python
   try:
       process_file()
   except Exception as e:
       logger.error(f"Failed to process file: {e}", exc_info=True)
   ```

4. **Avoid logging sensitive data**:
   - Don't log passwords, API keys, or personal information
   - Log document IDs, not full content

5. **Performance considerations**:
   - Use DEBUG level sparingly in production
   - Consider log rotation for production environments

## Log Rotation

For production, consider using log rotation:

```bash
# Using logrotate (Linux)
/var/log/docvault/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
}
```

## Monitoring

Logs can be monitored using:
- **Local**: `tail -f logs/app.log`
- **Production**: ELK Stack, CloudWatch, Datadog, etc.

## Next Steps

1. ✅ Logging imports added to all files
2. ✅ Core logging configuration created
3. ✅ Critical files updated with logging statements
4. ⚠️ **Remaining**: Add specific logging statements to remaining files as needed
5. ⚠️ **Production**: Configure log rotation and monitoring

## Helper Script

A helper script `add_logging_helper.py` is available to add logging imports to new files:

```bash
python backend/add_logging_helper.py
```

