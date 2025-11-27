# MongoDB Setup Guide for DocVault AI

This guide will help you set up MongoDB for persistent storage in DocVault AI.

## Quick Start (Docker - Recommended)

The easiest way to get MongoDB running is using Docker:

```bash
# Run the setup script
./scripts/setup_mongodb_docker.sh

# Or manually:
docker run -d --name mongodb -p 27017:27017 -v mongodb_data:/data/db mongo:latest
```

## Manual Installation

### macOS (using Homebrew)

```bash
# Install MongoDB
brew tap mongodb/brew
brew install mongodb-community

# Start MongoDB
brew services start mongodb-community

# Or run manually:
mongod --config /usr/local/etc/mongod.conf
```

### Linux (Ubuntu/Debian)

```bash
# Import MongoDB public key
wget -qO - https://www.mongodb.org/static/pgp/server-7.0.asc | sudo apt-key add -

# Add MongoDB repository
echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list

# Install MongoDB
sudo apt-get update
sudo apt-get install -y mongodb-org

# Start MongoDB
sudo systemctl start mongod
sudo systemctl enable mongod
```

### Windows

1. Download MongoDB Community Server from: https://www.mongodb.com/try/download/community
2. Run the installer
3. MongoDB will start automatically as a Windows service

## Configuration

### Environment Variables

Create a `.env` file in the `backend` directory:

```env
# MongoDB Configuration (optional - defaults shown)
MONGODB_CONNECTION_STRING=mongodb://localhost:27017/
MONGODB_DB_NAME=docvault
```

### Default Settings

- **Host**: localhost
- **Port**: 27017
- **Database**: docvault
- **Connection String**: `mongodb://localhost:27017/`

## Verify Installation

### Check if MongoDB is running:

```bash
# macOS/Linux
pgrep mongod

# Or test connection
mongosh --eval "db.adminCommand('ping')"
```

### Connect to MongoDB:

```bash
mongosh
# or
mongo
```

## Database Structure

### Collections

1. **documents** - Stores document metadata
   - Indexes: `id` (unique), `folder`, `status`, `checksum`, `upload_date`

2. **folders** - Stores folder metadata (for empty folders)
   - Indexes: `folder_path` (unique), `parent_folder`

3. **_migrations** - Tracks database migrations
   - Stores migration history and version

### Sample Document Structure

```json
{
  "id": "uuid",
  "filename": "document.pdf",
  "upload_date": "2025-01-01T00:00:00",
  "modified_date": "2025-01-01T00:00:00",
  "file_path": "/path/to/file",
  "folder": "folder1/subfolder",
  "checksum": "sha256_hash",
  "size": 1024,
  "status": "completed",
  "summary": "AI-generated summary",
  "markdown_path": "/path/to/markdown",
  "upload_progress": 100,
  "created_at": "2025-01-01T00:00:00",
  "updated_at": "2025-01-01T00:00:00"
}
```

## Migrations

Database migrations run automatically on startup. The migration service:

- Tracks database version
- Runs pending migrations in order
- Prevents duplicate migrations
- Updates schema and indexes

### Manual Migration

If you need to run migrations manually:

```python
from app.services.mongodb_service import MongoDBService
from app.services.migration_service import MigrationService
from app.core.config import MONGODB_CONNECTION_STRING, MONGODB_DB_NAME

db_service = MongoDBService(
    connection_string=MONGODB_CONNECTION_STRING,
    db_name=MONGODB_DB_NAME
)
migration_service = MigrationService(db_service)
await migration_service.run_migrations()
```

## Troubleshooting

### MongoDB won't start

1. **Check if port 27017 is in use:**
   ```bash
   lsof -i :27017
   ```

2. **Check MongoDB logs:**
   ```bash
   # macOS
   tail -f /usr/local/var/log/mongodb/mongo.log
   
   # Linux
   tail -f /var/log/mongodb/mongod.log
   ```

3. **Check data directory permissions:**
   ```bash
   # Ensure MongoDB can write to data directory
   sudo chown -R mongodb:mongodb /data/db
   ```

### Connection refused

- Ensure MongoDB is running: `pgrep mongod`
- Check firewall settings
- Verify connection string in `.env` file

### Database not persisting

- Check data directory path
- Verify MongoDB has write permissions
- Check disk space

## Production Considerations

For production deployments:

1. **Use MongoDB Atlas** (cloud-hosted):
   - Free tier available
   - Automatic backups
   - Built-in security

2. **Enable Authentication:**
   ```bash
   # Create admin user
   mongosh admin --eval "db.createUser({user: 'admin', pwd: 'password', roles: ['root']})"
   ```

3. **Configure Replication:**
   - Set up replica sets for high availability
   - Configure automatic failover

4. **Backup Strategy:**
   ```bash
   # Backup database
   mongodump --db docvault --out /backup/path
   
   # Restore database
   mongorestore --db docvault /backup/path/docvault
   ```

## Useful Commands

```bash
# Start MongoDB
brew services start mongodb-community  # macOS
sudo systemctl start mongod            # Linux

# Stop MongoDB
brew services stop mongodb-community   # macOS
sudo systemctl stop mongod             # Linux

# View MongoDB status
brew services list                      # macOS
sudo systemctl status mongod            # Linux

# Connect to MongoDB shell
mongosh

# List databases
mongosh --eval "show dbs"

# Use docvault database
mongosh docvault

# View collections
mongosh docvault --eval "show collections"

# Count documents
mongosh docvault --eval "db.documents.countDocuments()"
```

## Next Steps

1. Install MongoDB (using Docker or manual installation)
2. Install Python dependencies: `pip install pymongo motor`
3. Start the backend: `cd backend && python main.py`
4. Migrations will run automatically on startup

For more information, visit: https://www.mongodb.com/docs/

