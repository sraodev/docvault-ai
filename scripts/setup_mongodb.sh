#!/bin/bash

# MongoDB Setup Script for DocVault AI
# This script helps set up MongoDB for the application

set -e

echo "🚀 DocVault AI - MongoDB Setup"
echo "================================"
echo ""

# Detect OS
OS="$(uname -s)"
case "${OS}" in
    Linux*)     OS_TYPE=linux;;
    Darwin*)    OS_TYPE=macos;;
    *)          OS_TYPE=unknown;;
esac

echo "Detected OS: $OS_TYPE"
echo ""

# Function to check if MongoDB is installed
check_mongodb() {
    if command -v mongod &> /dev/null; then
        return 0
    else
        return 1
    fi
}

# Function to check if MongoDB is running
check_mongodb_running() {
    if pgrep -x "mongod" > /dev/null; then
        return 0
    else
        return 1
    fi
}

# Install MongoDB based on OS
install_mongodb() {
    echo "📦 Installing MongoDB..."
    
    if [ "$OS_TYPE" = "macos" ]; then
        if command -v brew &> /dev/null; then
            echo "Installing MongoDB via Homebrew..."
            brew tap mongodb/brew
            brew install mongodb-community
            echo "✅ MongoDB installed successfully!"
        else
            echo "❌ Homebrew not found. Please install Homebrew first:"
            echo "   /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
            exit 1
        fi
    elif [ "$OS_TYPE" = "linux" ]; then
        echo "Installing MongoDB on Linux..."
        echo "Please follow the official MongoDB installation guide:"
        echo "https://www.mongodb.com/docs/manual/installation/"
        echo ""
        echo "Or use Docker:"
        echo "  docker run -d -p 27017:27017 --name mongodb mongo:latest"
        exit 1
    else
        echo "❌ Unsupported OS. Please install MongoDB manually."
        echo "   Visit: https://www.mongodb.com/try/download/community"
        exit 1
    fi
}

# Start MongoDB
start_mongodb() {
    echo "🔄 Starting MongoDB..."
    
    if [ "$OS_TYPE" = "macos" ]; then
        if command -v brew &> /dev/null; then
            brew services start mongodb-community
            echo "✅ MongoDB started!"
        else
            echo "Starting MongoDB manually..."
            mongod --config /usr/local/etc/mongod.conf --fork
        fi
    else
        echo "Please start MongoDB manually:"
        echo "  sudo systemctl start mongod"
        echo "  or"
        echo "  mongod --fork --logpath /var/log/mongodb/mongod.log"
    fi
}

# Create data directory
create_data_dir() {
    echo "📁 Creating data directory..."
    mkdir -p ~/data/db
    echo "✅ Data directory created: ~/data/db"
}

# Test MongoDB connection
test_connection() {
    echo "🧪 Testing MongoDB connection..."
    sleep 2  # Wait for MongoDB to start
    
    if mongosh --eval "db.adminCommand('ping')" --quiet > /dev/null 2>&1; then
        echo "✅ MongoDB connection successful!"
        return 0
    else
        echo "❌ MongoDB connection failed. Please check if MongoDB is running."
        return 1
    fi
}

# Main execution
main() {
    # Check if MongoDB is installed
    if ! check_mongodb; then
        echo "MongoDB is not installed."
        read -p "Do you want to install MongoDB? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            install_mongodb
        else
            echo "Please install MongoDB manually and run this script again."
            exit 1
        fi
    else
        echo "✅ MongoDB is already installed"
        mongod --version
    fi
    
    # Check if MongoDB is running
    if ! check_mongodb_running; then
        echo "MongoDB is not running."
        read -p "Do you want to start MongoDB? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            start_mongodb
        else
            echo "Please start MongoDB manually and run this script again."
            exit 1
        fi
    else
        echo "✅ MongoDB is already running"
    fi
    
    # Create data directory if it doesn't exist
    if [ ! -d ~/data/db ]; then
        create_data_dir
    fi
    
    # Test connection
    if test_connection; then
        echo ""
        echo "🎉 MongoDB setup complete!"
        echo ""
        echo "Connection string: mongodb://localhost:27017/"
        echo "Database name: docvault (default)"
        echo ""
        echo "You can now start the backend server:"
        echo "  cd backend && python main.py"
    else
        echo ""
        echo "⚠️  MongoDB setup incomplete. Please check the errors above."
    fi
}

# Run main function
main

