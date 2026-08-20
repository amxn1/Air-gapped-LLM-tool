#!/bin/bash
# Development startup script for Offline LLM Assistant
# This script helps run the application locally for development purposes

set -e  # Exit on any error

echo "Starting Offline LLM Assistant in development mode..."

# Check if required tools are installed
command -v python3 >/dev/null 2>&1 || { echo "Error: python3 is required but not installed."; exit 1; }
command -v npm >/dev/null 2>&1 || { echo "Error: npm is required but not installed."; exit 1; }

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r apps/api/requirements.txt

# Install Node.js dependencies
echo "Installing Node.js dependencies..."
cd apps/web
npm install
cd ../..

# Start PostgreSQL in Docker (if not already running)
echo "Starting PostgreSQL..."
docker run -d \
  --name offline-llm-postgres \
  -e POSTGRES_USER=offline_llm \
  -e POSTGRES_PASSWORD=secure_password \
  -e POSTGRES_DB=offline_llm \
  -p 5432:5432 \
  postgres:15 || true

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
sleep 5

# Run database migrations (if using Alembic)
echo "Setting up database..."
# In a real implementation, we would run alembic upgrade head here
# For now, we'll just note that the init.sql from docker-compose would handle this

# Start the API server in the background
echo "Starting API server..."
cd apps/api
python main.py &
API_PID=$!
cd ..

# Give the API server a moment to start
sleep 3

# Start the frontend development server
echo "Starting frontend development server..."
cd apps/web
npm start

# If we reach here (npm start exited), kill the API server
echo "Frontend development server stopped. Stopping API server..."
kill $API_PID 2>/dev/null || true
deactivate