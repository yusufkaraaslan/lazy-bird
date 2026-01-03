#!/bin/bash
# Start PostgreSQL in Docker for E2E testing

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Container name
CONTAINER_NAME="lazy-bird-test-db"
DB_NAME="lazy_bird_e2e_test"
DB_USER="postgres"
DB_PASSWORD="testpassword123"
DB_PORT="5433"

echo -e "${BLUE}╔═══════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Lazy-Bird E2E Test Database             ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════╝${NC}"
echo

# Check if container already exists
if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo -e "${YELLOW}[!]${NC} Container $CONTAINER_NAME already exists"

    # Check if running
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        echo -e "${GREEN}[✓]${NC} PostgreSQL is already running"
    else
        echo -e "${BLUE}[INFO]${NC} Starting existing container..."
        docker start "$CONTAINER_NAME"
        sleep 3
        echo -e "${GREEN}[✓]${NC} PostgreSQL started"
    fi
else
    echo -e "${BLUE}[INFO]${NC} Creating new PostgreSQL container..."

    docker run -d \
        --name "$CONTAINER_NAME" \
        -e POSTGRES_PASSWORD="$DB_PASSWORD" \
        -e POSTGRES_DB="$DB_NAME" \
        -p "$DB_PORT:5432" \
        postgres:15-alpine

    echo -e "${BLUE}[INFO]${NC} Waiting for PostgreSQL to be ready..."
    sleep 5

    # Wait for PostgreSQL to accept connections
    for i in {1..30}; do
        if docker exec "$CONTAINER_NAME" pg_isready -U postgres >/dev/null 2>&1; then
            echo -e "${GREEN}[✓]${NC} PostgreSQL is ready!"
            break
        fi
        echo -n "."
        sleep 1
    done
    echo
fi

# Get container IP
CONTAINER_IP=$(docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "$CONTAINER_NAME")

echo
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}▶ PostgreSQL Test Database Ready${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo
echo -e "${BLUE}Container:${NC}  $CONTAINER_NAME"
echo -e "${BLUE}Database:${NC}   $DB_NAME"
echo -e "${BLUE}User:${NC}       $DB_USER"
echo -e "${BLUE}Password:${NC}   $DB_PASSWORD"
echo -e "${BLUE}Host Port:${NC}  $DB_PORT"
echo -e "${BLUE}Container IP:${NC} $CONTAINER_IP"
echo
echo -e "${YELLOW}Export this environment variable:${NC}"
echo
echo -e "  ${GREEN}export DATABASE_URL=\"postgresql+asyncpg://$DB_USER:$DB_PASSWORD@localhost:$DB_PORT/$DB_NAME\"${NC}"
echo
echo -e "${BLUE}Or copy-paste this to run E2E test:${NC}"
echo
echo -e "  ${GREEN}export DATABASE_URL=\"postgresql+asyncpg://$DB_USER:$DB_PASSWORD@localhost:$DB_PORT/$DB_NAME\" && ./tests/e2e/test_full_workflow.sh${NC}"
echo
echo -e "${YELLOW}To stop the database:${NC}"
echo -e "  ./tests/e2e/stop-test-db.sh"
echo
