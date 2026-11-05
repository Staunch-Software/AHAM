#!/usr/bin/env bash
# Backs up the production database and photo volume into ./backups (or $1).
#   infrastructure/deployment/backup.sh [target-dir]
# Order matters: the database dump is taken first, then the photos, so every photo the dump references
# exists in the archive. Run from the repository root with the same --env-file you deploy with.
set -euo pipefail

COMPOSE=(docker compose -f docker-compose.prod.yml --env-file "${ENV_FILE:-.env.prod}")
OUT="${1:-backups}"
STAMP="$(date +%Y%m%d-%H%M%S)"
mkdir -p "$OUT"

"${COMPOSE[@]}" exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -Fc "$POSTGRES_DB"' > "$OUT/db-$STAMP.dump"
"${COMPOSE[@]}" exec -T backend tar czf - -C /data/storage . > "$OUT/photos-$STAMP.tgz"

# Fail loudly on an empty/corrupt artifact instead of discovering it at restore time.
[ -s "$OUT/db-$STAMP.dump" ] || { echo "empty database dump" >&2; exit 1; }
tar tzf "$OUT/photos-$STAMP.tgz" > /dev/null
echo "OK: $OUT/db-$STAMP.dump ($(wc -c < "$OUT/db-$STAMP.dump") bytes), $OUT/photos-$STAMP.tgz ($(wc -c < "$OUT/photos-$STAMP.tgz") bytes)"
echo "Copy these off the host. Restore: see docs/backup-restore.md"
