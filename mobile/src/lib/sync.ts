import * as Network from 'expo-network'
import { File } from 'expo-file-system'
import { useEffect, useState } from 'react'
import { AppState } from 'react-native'
import { api, ApiError, AuthError, NetworkError } from './api'
import { SYNC_INTERVAL_MS, UPLOAD_TIMEOUT_MS } from './config'
import { countPending, dueEntries, type LocalPhoto, markPhotoUploaded, photosOf, updateEntry } from './db'
import { OffsetMismatch, Permanent, type Report, Retryable, SignedOut, type Store, syncOnce, type Transport } from './syncEngine'

async function wrap<T>(fn: () => Promise<T>): Promise<T> {
  try {
    return await fn()
  } catch (e) {
    if (e instanceof NetworkError) throw new Retryable(e.message)
    if (e instanceof AuthError) throw new SignedOut(e.message)
    if (e instanceof ApiError) {
      const received = e.detail?.received_bytes
      if (e.status === 409 && typeof received === 'number') throw new OffsetMismatch(received)
      if (e.status === 422 && /checksum/i.test(e.message)) throw new Retryable(e.message) // discarded: upload again from 0
      throw new Permanent(e.message)
    }
    throw new Retryable((e as Error)?.message ?? 'Sync failed')
  }
}

const transport: Transport = {
  initiate: (p) => wrap(() => {
    const ph = p as LocalPhoto
    return api('POST', '/uploads/initiate', {
      body: {
        photo_id: ph.id, mime_type: ph.mime, size_bytes: ph.size, sha256: ph.sha256, filename: `${ph.id}.jpg`,
        photo_captured_at_device: ph.captured_at, latitude: ph.latitude, longitude: ph.longitude, accuracy_m: ph.accuracy,
        location_fix_at_device: ph.fix_at, location_status: ph.location_status, location_source: ph.latitude != null ? 'gps' : null,
      },
    })
  }),
  put: (p, offset) => wrap(async () => {
    const ph = p as LocalPhoto
    const bytes = await new File(ph.path).bytes()
    return api('PUT', `/uploads/${ph.id}`, {
      rawBody: bytes.slice(offset) as Uint8Array<ArrayBuffer>, timeoutMs: UPLOAD_TIMEOUT_MS,
      headers: { 'Content-Type': ph.mime, 'Content-Range': `bytes ${offset}-${ph.size - 1}/${ph.size}` },
    })
  }),
  complete: (p) => wrap(() => api('POST', `/uploads/${p.id}/complete`)),
  postEntry: (body) => wrap(() => api('POST', '/entries', { rawBody: body, headers: { 'Content-Type': 'application/json' } })),
}

const storeFor = (ownerId: string): Store => ({
  due: (now, force) => dueEntries(ownerId, now, force),
  photos: (localId) => photosOf(localId),
  photoUploaded: (id) => markPhotoUploaded(id),
  update: (localId, fields) => updateEntry(localId, fields),
})

// ---------------------------------------------------------------- runner + status for the screens
export interface SyncStatus { running: boolean; lastRunAt: number | null; lastReport: Report | null; pending: number; failed: number; error: string | null }
let status: SyncStatus = { running: false, lastRunAt: null, lastReport: null, pending: 0, failed: 0, error: null }
const listeners = new Set<(s: SyncStatus) => void>()
const publish = (s: Partial<SyncStatus>) => { status = { ...status, ...s }; listeners.forEach((l) => l(status)) }
let inFlight: Promise<Report | null> | null = null

export async function refreshCounts(ownerId: string) {
  publish(await countPending(ownerId))
}

/** One sync pass for this SO's entries; concurrent calls share the pass already running. */
export function runSync(ownerId: string, force = false): Promise<Report | null> {
  inFlight ??= (async () => {
    publish({ running: true, error: null })
    try {
      const report = await syncOnce(storeFor(ownerId), transport, { force })
      publish({ lastReport: report, lastRunAt: Date.now(), error: report.stopped === 'signed_out' ? 'Signed out: sign in to send your entries' : null })
      return report
    } catch (e) {
      publish({ error: (e as Error)?.message ?? 'Sync failed' })
      return null
    } finally {
      publish({ running: false, ...(await countPending(ownerId)) })
    }
  })().finally(() => { inFlight = null })
  return inFlight
}

export function useSyncStatus(): SyncStatus {
  const [s, setS] = useState(status)
  useEffect(() => { listeners.add(setS); return () => { listeners.delete(setS) } }, [])
  return s
}

/** Sync when the app starts, when the network comes back, when the app returns to the front, and every minute. */
export function startSyncTriggers(ownerId: string): () => void {
  refreshCounts(ownerId).catch(() => {})
  runSync(ownerId).catch(() => {})
  const net = Network.addNetworkStateListener((st) => { if (st.isConnected && st.isInternetReachable !== false) runSync(ownerId).catch(() => {}) })
  const app = AppState.addEventListener('change', (st) => { if (st === 'active') runSync(ownerId).catch(() => {}) })
  const timer = setInterval(() => { if (AppState.currentState === 'active') runSync(ownerId).catch(() => {}) }, SYNC_INTERVAL_MS)
  return () => { net.remove(); app.remove(); clearInterval(timer) }
}
