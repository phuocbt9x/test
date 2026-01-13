#!/bin/bash
cd /var/www/html/timima01/backend

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
