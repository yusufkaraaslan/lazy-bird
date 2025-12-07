#!/bin/bash
# Stop all Lazy_Bird services

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}Stopping all Lazy_Bird services...${NC}"
echo ""

# Stop systemd services
echo -e "${BLUE}Stopping automation services...${NC}"
systemctl --user stop issue-watcher queue-processor 2>/dev/null || true
echo -e "${GREEN}✓ Stopped issue-watcher and queue-processor${NC}"

# Stop web services
echo -e "${BLUE}Stopping web services...${NC}"
lsof -ti:5000 | xargs kill -9 2>/dev/null || true
lsof -ti:5173 | xargs kill -9 2>/dev/null || true
echo -e "${GREEN}✓ Stopped web backend and frontend${NC}"

echo ""
echo -e "${GREEN}All services stopped${NC}"
