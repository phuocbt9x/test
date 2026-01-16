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

# Health check
echo "Performing health check..."
MAX_RETRIES=5
RETRY_COUNT=0
HEALTH_URL="http://localhost:8000/health"

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -f -s "$HEALTH_URL" > /dev/null 2>&1; then
        echo "Health check passed ✓"
        break
    else
        RETRY_COUNT=$(($RETRY_COUNT + 1))
        echo "Health check attempt $RETRY_COUNT/$MAX_RETRIES failed, retrying in 1 seconds..."
        sleep 1
    fi
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "Health check failed after $MAX_RETRIES attempts."
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
