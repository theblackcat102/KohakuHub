#!/bin/bash

# Copy documentation files to frontend public directory
echo "Copying documentation files..."
mkdir -p ./src/kohaku-hub-ui/public/docs
cp docs/API.md ./src/kohaku-hub-ui/public/docs/API.md
cp docs/CLI.md ./src/kohaku-hub-ui/public/docs/CLI.md
cp docs/TODO.md ./src/kohaku-hub-ui/public/docs/TODO.md
cp CONTRIBUTING.md ./src/kohaku-hub-ui/public/CONTRIBUTING.md

# Install dependencies and build frontend
echo "Installing frontend dependencies..."
npm install --prefix ./src/kohaku-hub-ui

echo "Building frontend..."
npm run build --prefix ./src/kohaku-hub-ui

# Start Docker services
echo "Starting Docker services..."
docker-compose up -d --build