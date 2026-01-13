log "Pulling latest code from branch: $BRANCH..."
git checkout .
git fetch origin
git reset --hard origin/$BRANCH || { error "Failed to pull code"; exit 1; }

docker compose up -d --build || { error "Failed to start containers"; exit 1; }

# Check if app container is running
if docker compose ps | grep -q "timima_app.*Up"; then
    log "App container is running"
else
    error "App container failed to start"
    docker compose logs app --tail=10
    exit 1
fi


log "Running database migrations..."
docker compose exec -T app alembic upgrade head || warning "Migration failed or no migrations to run"

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
    docker compose logs app --tail=10
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
