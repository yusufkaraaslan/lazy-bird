#!/bin/bash
# Lazy_Bird Web Stack Stop Script
# Stops both backend and frontend servers

# Colors
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Stopping Lazy_Bird Web Stack...${NC}"

# Stop processes on port 5000 (backend)
if lsof -ti:5000 > /dev/null 2>&1; then
    echo -e "${BLUE}Stopping backend (port 5000)...${NC}"
    lsof -ti:5000 | xargs kill -9 2>/dev/null || true
    echo -e "${GREEN}✓ Backend stopped${NC}"
else
    echo -e "${BLUE}Backend not running${NC}"
fi

# Stop processes on port 5173 (frontend)
if lsof -ti:5173 > /dev/null 2>&1; then
    echo -e "${BLUE}Stopping frontend (port 5173)...${NC}"
    lsof -ti:5173 | xargs kill -9 2>/dev/null || true
    echo -e "${GREEN}✓ Frontend stopped${NC}"
else
    echo -e "${BLUE}Frontend not running${NC}"
fi

# Clean up log files
if [ -f "backend.log" ]; then
    rm backend.log
    echo -e "${GREEN}✓ Cleaned up backend.log${NC}"
fi

if [ -f "frontend.log" ]; then
    rm frontend.log
    echo -e "${GREEN}✓ Cleaned up frontend.log${NC}"
fi

echo -e "${GREEN}All services stopped${NC}"
