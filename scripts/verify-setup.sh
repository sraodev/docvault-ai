#!/bin/bash

# DocVault AI - Setup Verification Script
# This script verifies that the local development environment is set up correctly

set -e

echo "🔍 Verifying DocVault AI Development Setup..."
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Python
echo "Checking Python..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo -e "${GREEN}✓${NC} Python found: $PYTHON_VERSION"
else
    echo -e "${RED}✗${NC} Python3 not found. Please install Python 3.11+"
    exit 1
fi

# Check Node.js
echo "Checking Node.js..."
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    echo -e "${GREEN}✓${NC} Node.js found: $NODE_VERSION"
else
    echo -e "${RED}✗${NC} Node.js not found. Please install Node.js 18+"
    exit 1
fi

# Check npm
echo "Checking npm..."
if command -v npm &> /dev/null; then
    NPM_VERSION=$(npm --version)
    echo -e "${GREEN}✓${NC} npm found: $NPM_VERSION"
else
    echo -e "${RED}✗${NC} npm not found. Please install npm"
    exit 1
fi

echo ""
echo "Checking Backend..."

# Check backend virtual environment
if [ -d "backend/venv" ]; then
    echo -e "${GREEN}✓${NC} Backend virtual environment exists"
else
    echo -e "${YELLOW}⚠${NC} Backend virtual environment not found. Run: cd backend && python3 -m venv venv"
fi

# Check backend dependencies
if [ -f "backend/requirements.txt" ]; then
    echo -e "${GREEN}✓${NC} Backend requirements.txt found"
else
    echo -e "${RED}✗${NC} Backend requirements.txt not found"
    exit 1
fi

# Try importing backend app
cd backend
if source venv/bin/activate 2>/dev/null; then
    if python -c "from app.main import app" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} Backend app imports successfully"
    else
        echo -e "${RED}✗${NC} Backend app import failed. Check dependencies: pip install -r requirements.txt"
        exit 1
    fi
    deactivate
else
    echo -e "${YELLOW}⚠${NC} Could not activate virtual environment. Skipping import test"
fi
cd ..

echo ""
echo "Checking Frontend..."

# Check frontend node_modules
if [ -d "frontend/node_modules" ]; then
    echo -e "${GREEN}✓${NC} Frontend node_modules exists"
else
    echo -e "${YELLOW}⚠${NC} Frontend node_modules not found. Run: cd frontend && npm install"
fi

# Check frontend package.json
if [ -f "frontend/package.json" ]; then
    echo -e "${GREEN}✓${NC} Frontend package.json found"
else
    echo -e "${RED}✗${NC} Frontend package.json not found"
    exit 1
fi

# Try building frontend
cd frontend
if npm run build > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Frontend builds successfully"
else
    echo -e "${RED}✗${NC} Frontend build failed. Check dependencies: npm install"
    exit 1
fi
cd ..

echo ""
echo -e "${GREEN}✓${NC} All checks passed! Development environment is ready."
echo ""
echo "To start development:"
echo "  Backend:  cd backend && source venv/bin/activate && uvicorn app.main:app --reload"
echo "  Frontend: cd frontend && npm start"

