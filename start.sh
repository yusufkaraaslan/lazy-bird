#!/bin/bash
# Lazy_Bird Complete System Startup Script
# Starts all services: issue-watcher, queue-processor, web backend, web frontend

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}╔════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║       Lazy_Bird Complete System Startup           ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════╝${NC}"
echo ""

# 1. Start systemd services (issue-watcher, queue-processor)
echo -e "${BLUE}[1/4] Checking automation services...${NC}"

if systemctl --user is-active --quiet issue-watcher; then
    echo -e "${GREEN}  ✓ issue-watcher already running${NC}"
else
    echo -e "${YELLOW}  ⟳ Starting issue-watcher...${NC}"
    systemctl --user start issue-watcher
    echo -e "${GREEN}  ✓ issue-watcher started${NC}"
fi

if systemctl --user is-active --quiet queue-processor; then
    echo -e "${GREEN}  ✓ queue-processor already running${NC}"
else
    echo -e "${YELLOW}  ⟳ Starting queue-processor...${NC}"
    systemctl --user start queue-processor
    echo -e "${GREEN}  ✓ queue-processor started${NC}"
fi

# 2. Check if web services are needed
echo ""
echo -e "${BLUE}[2/4] Checking web services...${NC}"

# Check if backend is running
BACKEND_RUNNING=false
if lsof -Pi :5000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    BACKEND_RUNNING=true
    BACKEND_PID=$(lsof -Pi :5000 -sTCP:LISTEN -t)
    echo -e "${GREEN}  ✓ Backend already running (PID: $BACKEND_PID)${NC}"
fi

# Check if frontend is running
FRONTEND_RUNNING=false
if lsof -Pi :5173 -sTCP:LISTEN -t >/dev/null 2>&1; then
    FRONTEND_RUNNING=true
    FRONTEND_PID=$(lsof -Pi :5173 -sTCP:LISTEN -t)
    echo -e "${GREEN}  ✓ Frontend already running (PID: $FRONTEND_PID)${NC}"
fi

# 3. Start web backend if needed
echo ""
echo -e "${BLUE}[3/4] Web Backend (Flask API)...${NC}"

if [ "$BACKEND_RUNNING" = true ]; then
    echo -e "${GREEN}  ✓ Backend already running on http://localhost:5000${NC}"
else
    if [ ! -d "web/backend/venv" ]; then
        echo -e "${RED}  ✗ Backend venv not found${NC}"
        echo -e "${YELLOW}  → Run: cd web/backend && python3 -m venv venv && ./venv/bin/pip install -r requirements.txt${NC}"
    else
        echo -e "${YELLOW}  ⟳ Starting backend...${NC}"
        cd web/backend
        nohup ./venv/bin/python app.py > backend.log 2>&1 &
        BACKEND_PID=$!
        cd ../..
        sleep 2
        echo -e "${GREEN}  ✓ Backend started (PID: $BACKEND_PID)${NC}"
        echo -e "${GREEN}  ✓ URL: http://localhost:5000${NC}"
    fi
fi

# 4. Start web frontend if needed
echo ""
echo -e "${BLUE}[4/4] Web Frontend (Vue.js)...${NC}"

if [ "$FRONTEND_RUNNING" = true ]; then
    echo -e "${GREEN}  ✓ Frontend already running on http://localhost:5173${NC}"
else
    if [ ! -d "web/frontend/node_modules" ]; then
        echo -e "${RED}  ✗ Frontend dependencies not installed${NC}"
        echo -e "${YELLOW}  → Run: cd web/frontend && npm install${NC}"
    else
        echo -e "${YELLOW}  ⟳ Starting frontend...${NC}"
        cd web/frontend
        nohup npm run dev > frontend.log 2>&1 &
        FRONTEND_PID=$!
        cd ../..
        sleep 3
        echo -e "${GREEN}  ✓ Frontend started (PID: $FRONTEND_PID)${NC}"
        echo -e "${GREEN}  ✓ URL: http://localhost:5173${NC}"
    fi
fi

# Summary
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              All Services Running                  ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Automation Services:${NC}"
echo -e "  • issue-watcher:    $(systemctl --user is-active issue-watcher)"
echo -e "  • queue-processor:  $(systemctl --user is-active queue-processor)"
echo ""
echo -e "${BLUE}Web Services:${NC}"
echo -e "  • Backend API:      http://localhost:5000"
echo -e "  • Frontend UI:      http://localhost:5173"
echo ""
echo -e "${BLUE}Logs:${NC}"
echo -e "  • issue-watcher:    journalctl --user -u issue-watcher -f"
echo -e "  • queue-processor:  journalctl --user -u queue-processor -f"
echo -e "  • backend:          tail -f web/backend/backend.log"
echo -e "  • frontend:         tail -f web/frontend/frontend.log"
echo ""
echo -e "${BLUE}Management:${NC}"
echo -e "  • Stop all:         ./stop.sh"
echo -e "  • Restart all:      ./restart.sh"
echo -e "  • Status:           ./status.sh"
echo ""
