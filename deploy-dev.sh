#!/bin/bash

# =============================================================================
# Deployment Script for Timima Backend API (Development)
# =============================================================================
BRANCH="develop"

git checkout .
git checkout $BRANCH
git pull origin $BRANCH

# Stop and remove old containers to fix docker-compose compatibility
docker compose down 2>/dev/null || docker-compose down 2>/dev/null || warning "No containers to stop"

# Build and start containers (this will automatically install new dependencies)
echo "Building and starting Docker containers..."
if command -v docker &> /dev/null && docker compose version &> /dev/null; then
    docker compose up -d --build || { error "Failed to start containers"; exit 1; }
else
    docker-compose up -d --build || { error "Failed to start containers"; exit 1; }
fi
echo "Containers started successfully"

# Wait for containers to be ready
echo "Waiting for containers to be ready..."
sleep 10

# Check if app container is running
if docker compose ps 2>/dev/null | grep -q "app.*Up" || docker-compose ps 2>/dev/null | grep -q "app.*Up"; then
    echo "App container is running"
else
    error "App container failed to start"
    docker compose logs app --tail=10 2>/dev/null || docker-compose logs app --tail=10
    exit 1
fi

# Run database migrations
echo "Running database migrations..."
docker compose exec -T app alembic upgrade head 2>/dev/null || docker-compose exec -T app alembic upgrade head || warning "Migration failed or no migrations to run"

# Health check
echo "Performing health check..."
MAX_RETRIES=10
RETRY_COUNT=0
HEALTH_URL="http://localhost:8000/health"

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -f -s "$HEALTH_URL" > /dev/null 2>&1; then
        echo "Health check passed ✓"
        break
    else
        RETRY_COUNT=$((RETRY_COUNT + 1))
        warning "Health check attempt $RETRY_COUNT/$MAX_RETRIES failed, retrying in 2 seconds..."
        sleep 2
    fi
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    error "Health check failed after $MAX_RETRIES attempts"
    echo "Showing container logs:"
    docker compose logs app --tail=10 2>/dev/null || docker-compose logs app --tail=10
    exit 1
fi

# =============================================================================
# Deployment Complete
# =============================================================================

echo "====================================="
echo "Deployment completed successfully! ✓"
echo "====================================="
echo "App URL: http://localhost:8000"
echo "Health: http://localhost:8000/health"
echo "API Docs: http://localhost:8000/docs"
echo "====================================="

exit 0
