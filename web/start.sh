#!/bin/bash
# Lazy_Bird Web Stack Startup Script
# Starts both backend and frontend servers

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Store PIDs for cleanup
BACKEND_PID=""
FRONTEND_PID=""

# Cleanup function
cleanup() {
    echo -e "\n${YELLOW}Shutting down services...${NC}"

    if [ ! -z "$BACKEND_PID" ]; then
        echo -e "${BLUE}Stopping backend (PID: $BACKEND_PID)...${NC}"
        kill $BACKEND_PID 2>/dev/null || true
    fi

    if [ ! -z "$FRONTEND_PID" ]; then
        echo -e "${BLUE}Stopping frontend (PID: $FRONTEND_PID)...${NC}"
        kill $FRONTEND_PID 2>/dev/null || true
    fi

    # Kill any remaining processes on ports 5000 and 5173
    lsof -ti:5000 | xargs kill -9 2>/dev/null || true
    lsof -ti:5173 | xargs kill -9 2>/dev/null || true

    echo -e "${GREEN}All services stopped${NC}"
    exit 0
}

# Trap Ctrl+C and call cleanup
trap cleanup INT TERM

echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}  Lazy_Bird Web Stack Startup${NC}"
echo -e "${GREEN}======================================${NC}"

# Check if backend venv exists
if [ ! -d "backend/venv" ]; then
    echo -e "${RED}Error: Backend virtual environment not found!${NC}"
    echo -e "${YELLOW}Run: cd backend && python3 -m venv venv && ./venv/bin/pip install -r requirements.txt${NC}"
    exit 1
fi

# Check if frontend node_modules exists
if [ ! -d "frontend/node_modules" ]; then
    echo -e "${RED}Error: Frontend dependencies not installed!${NC}"
    echo -e "${YELLOW}Run: cd frontend && npm install${NC}"
    exit 1
fi

# Start backend
echo -e "\n${BLUE}Starting backend server...${NC}"
cd backend
./venv/bin/python app.py > ../backend.log 2>&1 &
BACKEND_PID=$!
cd ..

echo -e "${GREEN}✓ Backend started (PID: $BACKEND_PID)${NC}"
echo -e "  ${BLUE}URL: http://localhost:5000${NC}"
echo -e "  ${BLUE}Logs: web/backend.log${NC}"

# Wait for backend to start
sleep 2

# Start frontend
echo -e "\n${BLUE}Starting frontend dev server...${NC}"
cd frontend
npm run dev > ../frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

echo -e "${GREEN}✓ Frontend started (PID: $FRONTEND_PID)${NC}"
echo -e "  ${BLUE}URL: http://localhost:5173${NC}"
echo -e "  ${BLUE}Logs: web/frontend.log${NC}"

# Wait for frontend to start
sleep 3

echo -e "\n${GREEN}======================================${NC}"
echo -e "${GREEN}  ✓ All services running!${NC}"
echo -e "${GREEN}======================================${NC}"
echo -e ""
echo -e "  ${BLUE}Frontend:${NC}  http://localhost:5173"
echo -e "  ${BLUE}Backend:${NC}   http://localhost:5000"
echo -e "  ${BLUE}API Docs:${NC}  http://localhost:5000/"
echo -e ""
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"
echo -e ""

# Follow logs in real-time (alternating between both)
tail -f backend.log &
TAIL_PID=$!

# Wait indefinitely
wait
