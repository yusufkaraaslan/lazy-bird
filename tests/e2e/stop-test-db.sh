#!/bin/bash
# Stop and remove PostgreSQL test database container

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

CONTAINER_NAME="lazy-bird-test-db"

echo -e "${BLUE}╔═══════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Stop Lazy-Bird Test Database            ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════╝${NC}"
echo

# Check if container exists
if ! docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo -e "${YELLOW}[!]${NC} Container $CONTAINER_NAME does not exist"
    exit 0
fi

# Stop container if running
if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo -e "${BLUE}[INFO]${NC} Stopping container..."
    docker stop "$CONTAINER_NAME" >/dev/null
    echo -e "${GREEN}[✓]${NC} Container stopped"
fi

# Remove container
echo -e "${BLUE}[INFO]${NC} Removing container..."
docker rm "$CONTAINER_NAME" >/dev/null
echo -e "${GREEN}[✓]${NC} Container removed"

echo
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}Test database cleaned up successfully!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo
