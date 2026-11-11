/**
 * Offline sync engine. No React, SQLite or network imports, so it is unit-tested with fakes (__tests__/syncEngine).
 *
 * Delivery is at least once with idempotent processing (same design as the Flutter app it replaces):
 *  - photos have a stable id chosen on the phone and a resumable upload, so re-sending never duplicates;
 *  - the entry is sent with the same idempotency key and byte-identical body on every retry, so a timeout after the
 *    server saved it just returns the existing record;
 *  - an entry is "accepted" only after the server acknowledges it.
 * The time and place of the entry are inside the stored body: syncing later never changes them.
 */
export type State = 'queued' | 'uploading' | 'sync_pending' | 'accepted' | 'failed'

export interface EngineEntry { local_id: string; idempotency_key: string; body: string; state: State; attempts: number }
export interface EnginePhoto { id: string; size: number; uploaded: boolean | number }
export interface UploadState { upload_status: string; received_bytes: number }
export interface Receipt { id: string; entry_code: string; received_at_server: string }

export interface Transport {
  initiate(p: EnginePhoto): Promise<UploadState>
  /** Sends the file from `offset` to its end (Content-Range). */
  put(p: EnginePhoto, offset: number): Promise<UploadState>
  complete(p: EnginePhoto): Promise<UploadState>
  postEntry(body: string): Promise<Receipt>
}

export interface Store {
  due(now: number, force: boolean): Promise<EngineEntry[]>
  photos(localId: string): Promise<EnginePhoto[]>
  photoUploaded(photoId: string): Promise<void>
  update(localId: string, fields: Record<string, unknown>): Promise<void>
}

/** Try again later (no signal, timeout, server busy). */
export class Retryable extends Error {}
/** Refused for good (validation): needs a person to look at it. */
export class Permanent extends Error {}
/** Signed out on the server: stop, keep everything, do not count an attempt. */
export class SignedOut extends Error {}
/** The server holds a different number of bytes than we sent: ask it where to resume. */
export class OffsetMismatch extends Error { constructor(public received: number) { super('offset mismatch') } }

export interface Report { accepted: number; failed: number; retrying: number; stopped?: 'offline' | 'signed_out' }

export const backoffMs = (attempts: number, rand = Math.random()) =>
  Math.min(15 * 60_000, 5000 * 2 ** Math.min(attempts, 10)) * (0.5 + rand / 2)

async function uploadPhoto(t: Transport, p: EnginePhoto): Promise<void> {
  let st = await t.initiate(p)
  for (let round = 0; round < 4 && st.upload_status !== 'complete'; round++) {
    try {
      if (st.received_bytes < p.size) st = await t.put(p, st.received_bytes)
      st = await t.complete(p)
    } catch (e) {
      if (e instanceof OffsetMismatch) { st = { upload_status: 'uploading', received_bytes: e.received }; continue }
      throw e
    }
  }
  if (st.upload_status !== 'complete') throw new Retryable('Photo upload did not finish')
}

/** One pass over the entries that are due. Stops early when the phone is offline or signed out. */
export async function syncOnce(store: Store, t: Transport, opts: { now?: number; force?: boolean; rand?: () => number } = {}): Promise<Report> {
  const now = opts.now ?? Date.now()
  const report: Report = { accepted: 0, failed: 0, retrying: 0 }
  for (const e of await store.due(now, !!opts.force)) {
    try {
      await store.update(e.local_id, { state: 'uploading' })
      for (const p of await store.photos(e.local_id)) {
        if (p.uploaded) continue
        await uploadPhoto(t, p)
        await store.photoUploaded(p.id)
      }
      const r = await t.postEntry(e.body)
      await store.update(e.local_id, { state: 'accepted', server_id: r.id, server_code: r.entry_code, received_at: r.received_at_server, last_error: null })
      report.accepted++
    } catch (err) {
      if (err instanceof SignedOut) {
        await store.update(e.local_id, { state: 'sync_pending' })
        report.stopped = 'signed_out'
        return report
      }
      if (err instanceof Permanent) {
        await store.update(e.local_id, { state: 'failed', attempts: e.attempts + 1, last_error: err.message })
        report.failed++
        continue
      }
      const attempts = e.attempts + 1
      await store.update(e.local_id, {
        state: 'sync_pending', attempts, next_attempt_at: now + backoffMs(attempts, opts.rand?.()), last_error: (err as Error)?.message ?? 'Sync failed',
      })
      report.retrying++
      if (err instanceof Retryable) { report.stopped = 'offline'; return report }  // no point trying the rest now
    }
  }
  return report
}
