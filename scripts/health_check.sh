#!/bin/bash
#
# Simple Health Check Script
# Quickly check if your Ultrahuman agent is healthy
#
# Usage: ./scripts/health_check.sh
#

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

PROJECT_DIR="/Users/idunnuomisore/Downloads/ultrahuman_agent_02_04"

echo ""
echo "================================================"
echo "🏥 Ultrahuman Agent Health Check"
echo "================================================"
echo "Time: $(date)"
echo ""

# Check 1: App Running
echo -n "🔍 Checking if app is running... "
if curl -s http://localhost:5000/ > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Running${NC}"
    APP_RUNNING=true
else
    echo -e "${RED}❌ Not running${NC}"
    APP_RUNNING=false
fi

# Check 2: Database
echo -n "🔍 Checking database... "
if [ -f "$PROJECT_DIR/instance/ultrahuman_agent.db" ]; then
    DB_SIZE=$(du -h "$PROJECT_DIR/instance/ultrahuman_agent.db" | cut -f1)
    echo -e "${GREEN}✅ Present ($DB_SIZE)${NC}"
else
    echo -e "${RED}❌ Not found${NC}"
fi

# Check 3: Recent Errors
echo -n "🔍 Checking for recent errors... "
if [ -f "$PROJECT_DIR/logs/ultrahuman_agent.log" ]; then
    ERROR_COUNT=$(tail -100 "$PROJECT_DIR/logs/ultrahuman_agent.log" | grep -c "ERROR" || echo "0")
    if [ "$ERROR_COUNT" -gt 0 ]; then
        echo -e "${YELLOW}⚠️  $ERROR_COUNT errors in last 100 lines${NC}"
        echo ""
        echo "   Recent errors:"
        tail -100 "$PROJECT_DIR/logs/ultrahuman_agent.log" | grep "ERROR" | tail -3 | while read line; do
            echo -e "   ${RED}• ${line:0:80}...${NC}"
        done
    else
        echo -e "${GREEN}✅ No recent errors${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Log file not found${NC}"
fi

# Check 4: Disk Space
echo -n "🔍 Checking disk space... "
DISK_USAGE=$(df -h "$PROJECT_DIR" | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 80 ]; then
    echo -e "${YELLOW}⚠️  ${DISK_USAGE}% used${NC}"
else
    echo -e "${GREEN}✅ ${DISK_USAGE}% used${NC}"
fi

# Check 5: Last Data Sync
echo -n "🔍 Checking last data sync... "
if [ "$APP_RUNNING" = true ]; then
    LAST_SYNC=$(cd "$PROJECT_DIR" && source venv/bin/activate && python -c "
from app import create_app
from app.models import Metric
from utils.database import db
app = create_app()
with app.app_context():
    last_metric = Metric.query.order_by(Metric.timestamp.desc()).first()
    if last_metric:
        from datetime import datetime
        hours_ago = (datetime.utcnow() - last_metric.timestamp).total_seconds() / 3600
        print(f'{hours_ago:.1f} hours ago')
    else:
        print('No data')
" 2>/dev/null || echo "Error")

    if [ "$LAST_SYNC" != "Error" ] && [ "$LAST_SYNC" != "No data" ]; then
        echo -e "${GREEN}✅ $LAST_SYNC${NC}"
    else
        echo -e "${YELLOW}⚠️  $LAST_SYNC${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  App not running${NC}"
fi

# Check 6: Environment Variables
echo -n "🔍 Checking environment variables... "
if [ -f "$PROJECT_DIR/.env" ]; then
    MISSING_VARS=()

    source "$PROJECT_DIR/.env" 2>/dev/null || true

    [ -z "$ANTHROPIC_API_KEY" ] && MISSING_VARS+=("ANTHROPIC_API_KEY")
    [ -z "$TWILIO_ACCOUNT_SID" ] && MISSING_VARS+=("TWILIO_ACCOUNT_SID")
    [ -z "$ULTRAHUMAN_API_KEY" ] && MISSING_VARS+=("ULTRAHUMAN_API_KEY")

    if [ ${#MISSING_VARS[@]} -eq 0 ]; then
        echo -e "${GREEN}✅ All required vars present${NC}"
    else
        echo -e "${YELLOW}⚠️  Missing: ${MISSING_VARS[*]}${NC}"
    fi
else
    echo -e "${RED}❌ .env file not found${NC}"
fi

# Check 7: Backups
echo -n "🔍 Checking backups... "
BACKUP_DIR="$HOME/ultrahuman_backups"
if [ -d "$BACKUP_DIR" ]; then
    BACKUP_COUNT=$(find "$BACKUP_DIR" -name "backup_*" -type f | wc -l | tr -d ' ')
    if [ "$BACKUP_COUNT" -gt 0 ]; then
        LATEST_BACKUP=$(find "$BACKUP_DIR" -name "backup_*" -type f -printf '%T+ %p\n' | sort | tail -1 | cut -d' ' -f1)
        echo -e "${GREEN}✅ $BACKUP_COUNT backups (latest: $LATEST_BACKUP)${NC}"
    else
        echo -e "${YELLOW}⚠️  No backups found${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  No backup directory${NC}"
fi

# Summary
echo ""
echo "================================================"
echo "📊 Health Summary"
echo "================================================"

HEALTH_SCORE=0
TOTAL_CHECKS=7

[ "$APP_RUNNING" = true ] && ((HEALTH_SCORE++))
[ -f "$PROJECT_DIR/instance/ultrahuman_agent.db" ] && ((HEALTH_SCORE++))
[ "$ERROR_COUNT" -eq 0 ] 2>/dev/null && ((HEALTH_SCORE++))
[ "$DISK_USAGE" -lt 80 ] 2>/dev/null && ((HEALTH_SCORE++))
[ "$LAST_SYNC" != "Error" ] && [ "$LAST_SYNC" != "No data" ] && ((HEALTH_SCORE++))
[ ${#MISSING_VARS[@]} -eq 0 ] && ((HEALTH_SCORE++))
[ "$BACKUP_COUNT" -gt 0 ] 2>/dev/null && ((HEALTH_SCORE++))

HEALTH_PERCENT=$((HEALTH_SCORE * 100 / TOTAL_CHECKS))

if [ "$HEALTH_PERCENT" -ge 85 ]; then
    echo -e "${GREEN}Overall Status: ✅ HEALTHY ($HEALTH_SCORE/$TOTAL_CHECKS checks passed)${NC}"
elif [ "$HEALTH_PERCENT" -ge 60 ]; then
    echo -e "${YELLOW}Overall Status: ⚠️  DEGRADED ($HEALTH_SCORE/$TOTAL_CHECKS checks passed)${NC}"
else
    echo -e "${RED}Overall Status: ❌ UNHEALTHY ($HEALTH_SCORE/$TOTAL_CHECKS checks passed)${NC}"
fi

echo ""

# Recommendations
if [ "$HEALTH_SCORE" -lt "$TOTAL_CHECKS" ]; then
    echo "📋 Recommendations:"
    [ "$APP_RUNNING" = false ] && echo "   • Start the app: python app.py"
    [ "$ERROR_COUNT" -gt 0 ] 2>/dev/null && echo "   • Check logs: tail -f logs/ultrahuman_agent.log"
    [ "$DISK_USAGE" -gt 80 ] 2>/dev/null && echo "   • Free up disk space"
    [ ${#MISSING_VARS[@]} -gt 0 ] && echo "   • Add missing env vars to .env"
    [ "$BACKUP_COUNT" -eq 0 ] 2>/dev/null && echo "   • Run backup: ./scripts/backup.sh"
    echo ""
fi

echo "================================================"

exit 0
