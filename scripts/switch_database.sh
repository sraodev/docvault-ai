#!/bin/bash

# Database Switching Helper Script for DocVault AI
# Usage: ./scripts/switch_database.sh [json|memory]

set -e

DB_TYPE=${1:-json}

case "$DB_TYPE" in
    json)
        echo "🔄 Switching to JSON (File-Based)..."
        export DATABASE_TYPE=json
        export JSON_DB_PATH=${JSON_DB_PATH:-"./data/json_db"}
        echo "✅ JSON database configuration set"
        echo ""
        echo "Environment variables:"
        echo "  DATABASE_TYPE=$DATABASE_TYPE"
        echo "  JSON_DB_PATH=$JSON_DB_PATH"
        echo ""
        echo "ℹ️  Note: JSON database stores data in JSON files (persistent, easy to inspect)"
        ;;
    memory)
        echo "🔄 Switching to Memory (In-Memory)..."
        export DATABASE_TYPE=memory
        echo "✅ Memory database configuration set"
        echo ""
        echo "Environment variables:"
        echo "  DATABASE_TYPE=$DATABASE_TYPE"
        echo ""
        echo "ℹ️  Note: Memory database is non-persistent (data lost on restart)"
        ;;
    *)
        echo "❌ Invalid database type: $DB_TYPE"
        echo ""
        echo "Usage: $0 [json|memory]"
        echo ""
        echo "Available options:"
        echo "  json     - JSON database (local demos, file-based JSON, persistent) ⭐ Recommended"
        echo "  memory   - In-memory database (testing, non-persistent)"
        exit 1
        ;;
esac

echo ""
echo "📝 To persist these settings, add them to your .env file:"
echo "   DATABASE_TYPE=$DATABASE_TYPE"
if [ "$DB_TYPE" = "json" ]; then
    echo "   JSON_DB_PATH=$JSON_DB_PATH"
fi

