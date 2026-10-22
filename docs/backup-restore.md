# Backup and restore

Back up two things together: the **PostgreSQL database** and the **photo storage volume** (`STORAGE_ROOT`,
`/data/storage` in Docker). Photo rows reference files by key; a database restored without its files shows broken
images, and files without the database are unreferenced.

> Production: `infrastructure/deployment/backup.sh` runs both steps below (database first, then photos) and checks the
> artifacts. Verified: the dump restored with identical row counts and the photo archive listed all files.

## Database
```bash
# backup (custom format, compressed)
docker compose exec -T db pg_dump -U fieldsync -Fc fieldsync > fieldsync-$(date +%F).dump
# restore into a fresh database
docker compose exec -T db createdb -U fieldsync fieldsync_restore
docker compose exec -T db pg_restore -U fieldsync -d fieldsync_restore --no-owner < fieldsync-2026-10-16.dump
```
Verified on the development database: 403 submissions / 121 photos / 22 users and the Alembic version were identical
after restore. To switch the app to the restored copy, point `DATABASE_URL` at it, or restore over the original after
stopping the backend.

## Photos
Back up the volume with whatever the host provides (volume snapshot, `rsync`, or):
```bash
docker run --rm -v fieldsync_storage:/data -v "$PWD":/backup alpine tar czf /backup/storage-$(date +%F).tgz -C /data .
```
Take the database dump first, then the photos: every photo referenced by the dump will then exist in the archive.
(The photo archive command is documented but has not been rehearsed.)

## Schedule and retention
Nightly dump + photo archive, keep 14 daily / 8 weekly, copy off the host, rehearse a restore quarterly.
Define retention for photos and location data with the data owner.
