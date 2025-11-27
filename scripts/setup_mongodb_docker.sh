#!/bin/bash

# MongoDB Docker Setup Script for DocVault AI
# Quick setup using Docker (recommended for development)

set -e

echo "🐳 DocVault AI - MongoDB Docker Setup"
echo "======================================"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed."
    echo "Please install Docker: https://www.docker.com/get-started"
    exit 1
fi

# Check if MongoDB container is already running
if docker ps | grep -q mongodb; then
    echo "✅ MongoDB container is already running"
    docker ps | grep mongodb
    exit 0
fi

# Check if MongoDB container exists but is stopped
if docker ps -a | grep -q mongodb; then
    echo "🔄 Starting existing MongoDB container..."
    docker start mongodb
    echo "✅ MongoDB container started!"
    exit 0
fi

# Create new MongoDB container
echo "📦 Creating MongoDB container..."
docker run -d \
    --name mongodb \
    -p 27017:27017 \
    -v mongodb_data:/data/db \
    mongo:latest

echo "✅ MongoDB container created and started!"
echo ""
echo "Connection string: mongodb://localhost:27017/"
echo "Database name: docvault (default)"
echo ""
echo "To stop MongoDB: docker stop mongodb"
echo "To start MongoDB: docker start mongodb"
echo "To remove MongoDB: docker rm -f mongodb"

