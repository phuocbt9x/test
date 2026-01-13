#!/bin/bash

# =============================================================================
# Deployment Script for Timima Backend API (Development)
# =============================================================================

set -e  # Exit on error

# Configuration
BRANCH="develop"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
}

warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

# =============================================================================
# Main Deployment Process
# =============================================================================

log "Starting deployment process..."

# Pull latest code
log "Pulling latest code from branch: $BRANCH..."
git checkout .
git fetch origin
git reset --hard origin/$BRANCH || { error "Failed to pull code"; exit 1; }
log "Code updated successfully"

# Stop and remove old containers to fix docker-compose compatibility
log "Stopping old containers..."
docker compose down 2>/dev/null || docker-compose down 2>/dev/null || warning "No containers to stop"

# Build and start containers (this will automatically install new dependencies)
log "Building and starting Docker containers..."
if command -v docker &> /dev/null && docker compose version &> /dev/null; then
    docker compose up -d --build || { error "Failed to start containers"; exit 1; }
else
    docker-compose up -d --build || { error "Failed to start containers"; exit 1; }
fi
log "Containers started successfully"

# Wait for containers to be ready
log "Waiting for containers to be ready..."
sleep 10

# Check if app container is running
if docker compose ps 2>/dev/null | grep -q "app.*Up" || docker-compose ps 2>/dev/null | grep -q "app.*Up"; then
    log "App container is running"
else
    error "App container failed to start"
    docker compose logs app --tail=10 2>/dev/null || docker-compose logs app --tail=10
    exit 1
fi

# Run database migrations
log "Running database migrations..."
docker compose exec -T app alembic upgrade head 2>/dev/null || docker-compose exec -T app alembic upgrade head || warning "Migration failed or no migrations to run"

# Health check
log "Performing health check..."
MAX_RETRIES=10
RETRY_COUNT=0
HEALTH_URL="http://localhost:8000/health"

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -f -s "$HEALTH_URL" > /dev/null 2>&1; then
        log "Health check passed ✓"
        break
    else
        RETRY_COUNT=$((RETRY_COUNT + 1))
        warning "Health check attempt $RETRY_COUNT/$MAX_RETRIES failed, retrying in 2 seconds..."
        sleep 2
    fi
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    error "Health check failed after $MAX_RETRIES attempts"
    log "Showing container logs:"
    docker compose logs app --tail=10 2>/dev/null || docker-compose logs app --tail=10
    exit 1
fi

# =============================================================================
# Deployment Complete
# =============================================================================

log "====================================="
log "Deployment completed successfully! ✓"
log "====================================="
log "App URL: http://localhost:8000"
log "Health: http://localhost:8000/health"
log "API Docs: http://localhost:8000/docs"
log "====================================="

exit 0
