#!/bin/bash
#
# Automated Database Backup Script
# Backs up your Ultrahuman health data daily
#
# Usage: Run manually or add to crontab
#   crontab -e
#   Add line: 0 2 * * * /path/to/scripts/backup.sh
#
# This runs daily at 2 AM
#

set -e  # Exit on error

# Configuration
PROJECT_DIR="/Users/idunnuomisore/Downloads/ultrahuman_agent_02_04"
BACKUP_DIR="$HOME/ultrahuman_backups"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "================================================"
echo "🔄 Ultrahuman Agent Backup Script"
echo "================================================"
echo "Started: $(date)"
echo ""

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"
echo "✅ Backup directory: $BACKUP_DIR"

# Load environment variables to check database type
if [ -f "$PROJECT_DIR/.env" ]; then
    export $(cat "$PROJECT_DIR/.env" | grep -v '^#' | xargs)
fi

# Determine database type and backup accordingly
if [[ "$DATABASE_URL" == sqlite* ]] || [ -f "$PROJECT_DIR/instance/ultrahuman_agent.db" ]; then
    # SQLite backup
    echo "📦 Backing up SQLite database..."

    DB_FILE="$PROJECT_DIR/instance/ultrahuman_agent.db"

    if [ ! -f "$DB_FILE" ]; then
        echo -e "${RED}❌ Error: Database file not found at $DB_FILE${NC}"
        exit 1
    fi

    BACKUP_FILE="$BACKUP_DIR/backup_sqlite_$DATE.db"
    cp "$DB_FILE" "$BACKUP_FILE"

    # Get database size
    DB_SIZE=$(du -h "$DB_FILE" | cut -f1)
    echo -e "${GREEN}✅ SQLite backup created: $BACKUP_FILE ($DB_SIZE)${NC}"

elif [[ "$DATABASE_URL" == postgresql* ]] || [[ "$DATABASE_URL" == postgres* ]]; then
    # PostgreSQL backup
    echo "📦 Backing up PostgreSQL database..."

    BACKUP_FILE="$BACKUP_DIR/backup_postgres_$DATE.sql"

    if command -v pg_dump &> /dev/null; then
        pg_dump "$DATABASE_URL" > "$BACKUP_FILE"
        BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
        echo -e "${GREEN}✅ PostgreSQL backup created: $BACKUP_FILE ($BACKUP_SIZE)${NC}"
    else
        echo -e "${RED}❌ Error: pg_dump not found. Install PostgreSQL client tools.${NC}"
        exit 1
    fi

elif [[ "$DATABASE_URL" == mysql* ]]; then
    # MySQL backup
    echo "📦 Backing up MySQL database..."

    BACKUP_FILE="$BACKUP_DIR/backup_mysql_$DATE.sql"

    if command -v mysqldump &> /dev/null; then
        mysqldump --single-transaction "$DATABASE_URL" > "$BACKUP_FILE"
        BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
        echo -e "${GREEN}✅ MySQL backup created: $BACKUP_FILE ($BACKUP_SIZE)${NC}"
    else
        echo -e "${RED}❌ Error: mysqldump not found. Install MySQL client tools.${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠️  Could not determine database type${NC}"
    echo "DATABASE_URL: $DATABASE_URL"
fi

# Compress backup
echo ""
echo "🗜️  Compressing backup..."
gzip "$BACKUP_FILE"
COMPRESSED_FILE="${BACKUP_FILE}.gz"
COMPRESSED_SIZE=$(du -h "$COMPRESSED_FILE" | cut -f1)
echo -e "${GREEN}✅ Compressed to: $COMPRESSED_FILE ($COMPRESSED_SIZE)${NC}"

# Optional: Upload to cloud storage
# Uncomment and configure based on your cloud provider

# Example: Upload to Dropbox (requires rclone)
# if command -v rclone &> /dev/null; then
#     echo ""
#     echo "☁️  Uploading to Dropbox..."
#     rclone copy "$COMPRESSED_FILE" dropbox:ultrahuman_backups/
#     echo -e "${GREEN}✅ Uploaded to Dropbox${NC}"
# fi

# Example: Upload to Google Drive (requires rclone)
# if command -v rclone &> /dev/null; then
#     echo ""
#     echo "☁️  Uploading to Google Drive..."
#     rclone copy "$COMPRESSED_FILE" gdrive:ultrahuman_backups/
#     echo -e "${GREEN}✅ Uploaded to Google Drive${NC}"
# fi

# Example: Upload to AWS S3
# if command -v aws &> /dev/null; then
#     echo ""
#     echo "☁️  Uploading to AWS S3..."
#     aws s3 cp "$COMPRESSED_FILE" s3://your-bucket/ultrahuman-backups/
#     echo -e "${GREEN}✅ Uploaded to S3${NC}"
# fi

# Clean up old backups (keep last 30 days)
echo ""
echo "🧹 Cleaning up old backups (keeping last $RETENTION_DAYS days)..."
find "$BACKUP_DIR" -name "backup_*" -type f -mtime +$RETENTION_DAYS -delete
REMAINING_COUNT=$(find "$BACKUP_DIR" -name "backup_*" -type f | wc -l | tr -d ' ')
echo -e "${GREEN}✅ Cleanup complete. $REMAINING_COUNT backups remaining${NC}"

# Backup summary
echo ""
echo "================================================"
echo "📊 Backup Summary"
echo "================================================"
echo "Latest backup: $COMPRESSED_FILE"
echo "Size: $COMPRESSED_SIZE"
echo "Total backups: $REMAINING_COUNT"
echo "Oldest backup: $(find "$BACKUP_DIR" -name "backup_*" -type f -printf '%T+ %p\n' | sort | head -1 | cut -d' ' -f2- | xargs basename)"
echo "Newest backup: $(find "$BACKUP_DIR" -name "backup_*" -type f -printf '%T+ %p\n' | sort | tail -1 | cut -d' ' -f2- | xargs basename)"
echo ""
echo -e "${GREEN}✅ Backup completed successfully!${NC}"
echo "Finished: $(date)"
echo "================================================"

# Optional: Send success notification via SMS
# Uncomment to enable

# if [ -n "$BACKUP_NOTIFICATION_PHONE" ]; then
#     cd "$PROJECT_DIR"
#     source venv/bin/activate
#     python -c "
# from services.sms_service import SMSService
# sms = SMSService()
# sms.send_sms(
#     user_id='system',
#     phone_number='$BACKUP_NOTIFICATION_PHONE',
#     message='✅ Backup completed: $COMPRESSED_SIZE @ $(date +%H:%M)',
#     message_type='general'
# )
# "
# fi

exit 0
