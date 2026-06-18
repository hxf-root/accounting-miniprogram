#!/usr/bin/env bash
#
# backup.sh — Daily SQLite backup script for baobaoji.db
#
# Creates timestamped gzip-compressed copies of the database and prunes
# old backups, keeping only the most recent 30.
#
# Idempotent: safe to run multiple times.
#

set -euo pipefail

# ---------- Paths ----------
PROJECT_DIR="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"
DB_PATH="${PROJECT_DIR}/backend/baobaoji.db"
BACKUP_DIR="${PROJECT_DIR}/backend/backups"
LOG_DIR="${PROJECT_DIR}/backend/logs"
LOG_FILE="${LOG_DIR}/backup.log"
RETENTION=30

# ---------- Setup ----------
mkdir -p "${BACKUP_DIR}"
mkdir -p "${LOG_DIR}"

TIMESTAMP="$(date '+%Y%m%d_%H%M%S')"
BACKUP_FILE="${BACKUP_DIR}/baobaoji_${TIMESTAMP}.db.gz"

# ---------- Logging ----------
log() {
    local level="$1"
    shift
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [${level}] $*" >> "${LOG_FILE}"
}

# ---------- Preflight ----------
if [ ! -f "${DB_PATH}" ]; then
    log "ERROR" "Database not found at ${DB_PATH}. Aborting."
    exit 1
fi

# ---------- Backup ----------
# Use sqlite3 .backup for a safe, consistent snapshot, then gzip it.
# If sqlite3 is not available, fall back to cp + gzip.
SNAPSHOT="$(mktemp)"

if command -v sqlite3 &>/dev/null; then
    sqlite3 "${DB_PATH}" ".backup '${SNAPSHOT}'"
else
    cp "${DB_PATH}" "${SNAPSHOT}"
fi

gzip -c "${SNAPSHOT}" > "${BACKUP_FILE}"
rm -f "${SNAPSHOT}"

log "INFO" "Created backup: ${BACKUP_FILE} ($(du -h "${BACKUP_FILE}" | cut -f1))"

# ---------- Prune old backups ----------
pruned=0
while [ "$(find "${BACKUP_DIR}" -maxdepth 1 -name 'baobaoji_*.db.gz' | wc -l)" -gt "${RETENTION}" ]; do
    oldest="$(find "${BACKUP_DIR}" -maxdepth 1 -name 'baobaoji_*.db.gz' -type f -printf '%T@ %p\n' | sort -n | head -1 | awk '{print $2}')"
    if [ -n "${oldest}" ]; then
        rm -f "${oldest}"
        log "INFO" "Pruned old backup: ${oldest}"
        ((pruned++))
    fi
done

if [ "${pruned}" -eq 0 ]; then
    log "INFO" "No backups pruned (${RETENTION} or fewer retained)"
fi

exit 0
