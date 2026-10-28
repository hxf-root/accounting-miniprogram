#!/usr/bin/env bash
# Consistent SQLite backup using Python's SQLite backup API, including WAL.
set -euo pipefail
umask 077
PROJECT_DIR="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"
DB_PATH="${PROJECT_DIR}/backend/baobaoji.db"
BACKUP_DIR="${PROJECT_DIR}/backend/backups"
LOG_DIR="${PROJECT_DIR}/backend/logs"
mkdir -p "${LOG_DIR}"
if output="$(python3 "${PROJECT_DIR}/deploy/backup_sqlite.py" --database "${DB_PATH}" --backup-dir "${BACKUP_DIR}" --retention 30 2>&1)"; then
    printf '[%s] [INFO] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "${output}" >> "${LOG_DIR}/backup.log"
else
    printf '[%s] [ERROR] Backup failed.\n' "$(date '+%Y-%m-%d %H:%M:%S')" >> "${LOG_DIR}/backup.log"
    exit 1
fi
