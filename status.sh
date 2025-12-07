#!/bin/bash
# Check status of all Lazy_Bird services

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         Lazy_Bird System Status                   ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════╝${NC}"
echo ""

# Check automation services
echo -e "${BLUE}Automation Services:${NC}"

if systemctl --user is-active --quiet issue-watcher; then
    WATCHER_PID=$(systemctl --user show -p MainPID --value issue-watcher)
    echo -e "  ${GREEN}✓${NC} issue-watcher:   RUNNING (PID: $WATCHER_PID)"
else
    echo -e "  ${RED}✗${NC} issue-watcher:   STOPPED"
fi

if systemctl --user is-active --quiet queue-processor; then
    PROCESSOR_PID=$(systemctl --user show -p MainPID --value queue-processor)
    echo -e "  ${GREEN}✓${NC} queue-processor: RUNNING (PID: $PROCESSOR_PID)"
else
    echo -e "  ${RED}✗${NC} queue-processor: STOPPED"
fi

echo ""
echo -e "${BLUE}Web Services:${NC}"

# Check backend
if lsof -Pi :5000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    BACKEND_PID=$(lsof -Pi :5000 -sTCP:LISTEN -t)
    echo -e "  ${GREEN}✓${NC} Backend (5000):  RUNNING (PID: $BACKEND_PID)"
else
    echo -e "  ${RED}✗${NC} Backend (5000):  STOPPED"
fi

# Check frontend
if lsof -Pi :5173 -sTCP:LISTEN -t >/dev/null 2>&1; then
    FRONTEND_PID=$(lsof -Pi :5173 -sTCP:LISTEN -t)
    echo -e "  ${GREEN}✓${NC} Frontend (5173): RUNNING (PID: $FRONTEND_PID)"
else
    echo -e "  ${RED}✗${NC} Frontend (5173): STOPPED"
fi

echo ""
echo -e "${BLUE}Queue Status:${NC}"
QUEUE_COUNT=$(ls ~/.config/lazy_birtd/queue/*.json 2>/dev/null | wc -l)
echo -e "  Tasks in queue: $QUEUE_COUNT"

echo ""
echo -e "${BLUE}Recent Activity:${NC}"
if [ -f ~/.config/lazy_birtd/logs/issue-watcher.log ]; then
    echo -e "  Last issue check: $(tail -1 ~/.config/lazy_birtd/logs/issue-watcher.log | cut -d' ' -f1-2 2>/dev/null || echo 'N/A')"
fi
if [ -f ~/.config/lazy_birtd/logs/queue-processor.log ]; then
    echo -e "  Last task run:    $(tail -1 ~/.config/lazy_birtd/logs/queue-processor.log | cut -d' ' -f1-2 2>/dev/null || echo 'N/A')"
fi

echo ""
