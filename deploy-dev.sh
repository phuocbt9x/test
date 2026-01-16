#!/bin/bash

# =============================================================================
# Deployment Script for Timima Backend API (Development)
# =============================================================================
BRANCH="develop"

git checkout .
git checkout $BRANCH
git pull origin $BRANCH

echo "Cleaning up old Docker networks: ${APP_NAME}_network"
docker network rm "${APP_NAME}_network" 2>/dev/null || echo "No old network to remove"

# Stop and remove old containers to fix docker-compose compatibility
docker compose down 2>/dev/null || docker-compose down 2>/dev/null || warning "No containers to stop"



# Build and start containers (this will automatically install new dependencies)
echo "Building and starting Docker containers..."
docker-compose up -d --build 
echo "Containers started successfully"

# Run database migrations
echo "Running database migrations..."
docker compose exec -T app alembic upgrade head 2>/dev/null || docker-compose exec -T app alembic upgrade head || warning "Migration failed or no migrations to run"

exit 0
