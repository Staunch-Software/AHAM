import * as SQLite from 'expo-sqlite'

/**
 * The on-phone database. An entry is saved here first (one transaction: the entry, its photos, the draft cleared),
 * so nothing is lost when there is no signal; the sync engine then delivers it. Entries belong to the SO who made
 * them: signing out keeps them, and another user's sign-in never sends them.
 */
export type EntryState = 'queued' | 'uploading' | 'sync_pending' | 'accepted' | 'failed'

export interface LocalEntry {
  local_id: string
  owner_id: string
  idempotency_key: string
  entry_code: string
  body: string // the exact JSON sent on every retry (byte-identical, for idempotency)
  person_name: string
  phone: string
  category: string
  submitted_at: string
  entry_day: string // IST date of the Submit press
  state: EntryState
  attempts: number
  next_attempt_at: number
  last_error: string | null
  server_id: string | null
  server_code: string | null
  received_at: string | null
  created_at: number
}

export interface LocalPhoto {
  id: string
  local_id: string
  path: string
  sha256: string
  size: number
  mime: string
  captured_at: string
  latitude: number | null
  longitude: number | null
  accuracy: number | null
  fix_at: string | null
  location_status: string
  uploaded: number
}

const VERSION = 1
let dbPromise: Promise<SQLite.SQLiteDatabase> | null = null

export function getDb(): Promise<SQLite.SQLiteDatabase> {
  dbPromise ??= (async () => {
    const db = await SQLite.openDatabaseAsync('sankalp.db')
    await migrate(db)
    return db
  })()
  return dbPromise
}

async function migrate(db: SQLite.SQLiteDatabase) {
  await db.execAsync('PRAGMA journal_mode = WAL; PRAGMA foreign_keys = ON;')
  const row = await db.getFirstAsync<{ user_version: number }>('PRAGMA user_version')
  if ((row?.user_version ?? 0) >= VERSION) return
  await db.execAsync(`
    CREATE TABLE IF NOT EXISTS entries (
      local_id TEXT PRIMARY KEY NOT NULL, owner_id TEXT NOT NULL, idempotency_key TEXT NOT NULL UNIQUE,
      entry_code TEXT NOT NULL, body TEXT NOT NULL, person_name TEXT NOT NULL, phone TEXT NOT NULL, category TEXT NOT NULL,
      submitted_at TEXT NOT NULL, entry_day TEXT NOT NULL, state TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0, next_attempt_at INTEGER NOT NULL DEFAULT 0,
      last_error TEXT, server_id TEXT, server_code TEXT, received_at TEXT, created_at INTEGER NOT NULL
    );
    CREATE INDEX IF NOT EXISTS ix_entries_owner ON entries(owner_id, state);
    CREATE TABLE IF NOT EXISTS photos (
      id TEXT PRIMARY KEY NOT NULL, local_id TEXT NOT NULL REFERENCES entries(local_id) ON DELETE CASCADE, path TEXT NOT NULL,
      sha256 TEXT NOT NULL, size INTEGER NOT NULL, mime TEXT NOT NULL, captured_at TEXT NOT NULL, latitude REAL, longitude REAL,
      accuracy REAL, fix_at TEXT, location_status TEXT NOT NULL, uploaded INTEGER NOT NULL DEFAULT 0
    );
    CREATE INDEX IF NOT EXISTS ix_photos_entry ON photos(local_id);
    CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY NOT NULL, value TEXT NOT NULL);
    PRAGMA user_version = ${VERSION};
  `)
}

// ---------------------------------------------------------------- key/value cache (profile, lists, summary, draft)
export async function kvGet<T>(key: string): Promise<T | null> {
  const row = await (await getDb()).getFirstAsync<{ value: string }>('SELECT value FROM kv WHERE key = ?', key)
  return row ? (JSON.parse(row.value) as T) : null
}
export async function kvSet(key: string, value: unknown) {
  await (await getDb()).runAsync('INSERT INTO kv (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value', key, JSON.stringify(value))
}
export async function kvDelete(key: string) {
  await (await getDb()).runAsync('DELETE FROM kv WHERE key = ?', key)
}

// ---------------------------------------------------------------- entries
/** Saves an entry and its photos and clears the draft, all or nothing. */
export async function saveEntry(e: Omit<LocalEntry, 'attempts' | 'next_attempt_at' | 'last_error' | 'server_id' | 'server_code' | 'received_at' | 'state'>, photos: Omit<LocalPhoto, 'uploaded' | 'local_id'>[], draftKey: string) {
  const db = await getDb()
  await db.withExclusiveTransactionAsync(async (tx) => {
    await tx.runAsync(
      `INSERT INTO entries (local_id, owner_id, idempotency_key, entry_code, body, person_name, phone, category, submitted_at, entry_day, state, created_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'queued', ?)`,
      e.local_id, e.owner_id, e.idempotency_key, e.entry_code, e.body, e.person_name, e.phone, e.category, e.submitted_at, e.entry_day, e.created_at)
    for (const p of photos) {
      await tx.runAsync(
        `INSERT INTO photos (id, local_id, path, sha256, size, mime, captured_at, latitude, longitude, accuracy, fix_at, location_status)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
        p.id, e.local_id, p.path, p.sha256, p.size, p.mime, p.captured_at, p.latitude, p.longitude, p.accuracy, p.fix_at, p.location_status)
    }
    await tx.runAsync('DELETE FROM kv WHERE key = ?', draftKey)
  })
}

export async function listEntries(ownerId: string, limit = 200): Promise<LocalEntry[]> {
  return (await getDb()).getAllAsync<LocalEntry>('SELECT * FROM entries WHERE owner_id = ? ORDER BY submitted_at DESC LIMIT ?', ownerId, limit)
}

export async function getEntry(localId: string): Promise<LocalEntry | null> {
  return (await getDb()).getFirstAsync<LocalEntry>('SELECT * FROM entries WHERE local_id = ?', localId)
}

export async function dueEntries(ownerId: string, now: number, force: boolean): Promise<LocalEntry[]> {
  return (await getDb()).getAllAsync<LocalEntry>(
    `SELECT * FROM entries WHERE owner_id = ? AND state IN ('queued', 'uploading', 'sync_pending'${force ? ", 'failed'" : ''})
     AND (? OR next_attempt_at <= ?) ORDER BY submitted_at`, ownerId, force ? 1 : 0, now)
}

export async function countPending(ownerId: string): Promise<{ pending: number; failed: number }> {
  const r = await (await getDb()).getFirstAsync<{ pending: number; failed: number }>(
    `SELECT SUM(state IN ('queued','uploading','sync_pending')) AS pending, SUM(state = 'failed') AS failed FROM entries WHERE owner_id = ?`, ownerId)
  return { pending: r?.pending ?? 0, failed: r?.failed ?? 0 }
}

export async function photosOf(localId: string): Promise<LocalPhoto[]> {
  return (await getDb()).getAllAsync<LocalPhoto>('SELECT * FROM photos WHERE local_id = ? ORDER BY captured_at', localId)
}

export async function markPhotoUploaded(id: string) {
  await (await getDb()).runAsync('UPDATE photos SET uploaded = 1 WHERE id = ?', id)
}

export async function updateEntry(localId: string, fields: Partial<LocalEntry>) {
  const keys = Object.keys(fields)
  if (!keys.length) return
  await (await getDb()).runAsync(`UPDATE entries SET ${keys.map((k) => `${k} = ?`).join(', ')} WHERE local_id = ?`,
    ...keys.map((k) => (fields as any)[k]), localId)
}

export interface DayCount { entry_day: string; category: string; unsent: number; n: number }

/** Entries on this phone since a day, per day and category, split into sent / not yet sent (for the count date). */
export async function localDayCounts(ownerId: string, sinceDay: string): Promise<DayCount[]> {
  return (await getDb()).getAllAsync<DayCount>(
    `SELECT entry_day, category, (state != 'accepted') AS unsent, COUNT(*) AS n FROM entries
     WHERE owner_id = ? AND entry_day >= ? GROUP BY entry_day, category, unsent`, ownerId, sinceDay)
}
