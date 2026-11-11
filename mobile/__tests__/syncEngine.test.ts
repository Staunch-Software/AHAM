import { expect, test } from '@jest/globals'
import {
  backoffMs, type EngineEntry, type EnginePhoto, OffsetMismatch, Permanent, Retryable, SignedOut, type Store, syncOnce, type Transport,
} from '../src/lib/syncEngine'

type Row = EngineEntry & Record<string, unknown>

function fakeStore(entries: Row[], photos: Record<string, EnginePhoto[]> = {}) {
  const calls: string[] = []
  const store: Store = {
    due: async () => entries.filter((e) => ['queued', 'uploading', 'sync_pending'].includes(e.state)).map((e) => ({ ...e })),
    photos: async (id) => photos[id] ?? [],
    photoUploaded: async (id) => { calls.push(`uploaded:${id}`); for (const ps of Object.values(photos)) ps.forEach((p) => { if (p.id === id) p.uploaded = true }) },
    update: async (id, f) => { Object.assign(entries.find((e) => e.local_id === id)!, f) },
  }
  return { store, calls }
}

const entry = (id: string, over: Partial<Row> = {}): Row => ({
  local_id: id, idempotency_key: `k-${id}`, state: 'queued', attempts: 0,
  body: JSON.stringify({ idempotency_key: `k-${id}`, submitted_at_device: '2026-10-15T03:37:06.000Z', person_name: id }), ...over,
})

function fakeTransport(over: Partial<Transport> = {}) {
  const log: string[] = []
  const t: Transport = {
    initiate: async (p) => { log.push(`initiate:${p.id}`); return { upload_status: 'pending', received_bytes: 0 } },
    put: async (p, offset) => { log.push(`put:${p.id}@${offset}`); return { upload_status: 'uploading', received_bytes: p.size } },
    complete: async (p) => { log.push(`complete:${p.id}`); return { upload_status: 'complete', received_bytes: p.size } },
    postEntry: async (body) => { log.push(`post:${JSON.parse(body).person_name}`); return { id: `srv-${JSON.parse(body).person_name}`, entry_code: 'EMP-20261015-090706', received_at_server: '2026-10-17T10:00:00Z' } },
    ...over,
  }
  return { t, log }
}

test('photos go up first, then the entry; accepted only on the server receipt', async () => {
  const entries = [entry('a')]
  const { store } = fakeStore(entries, { a: [{ id: 'p1', size: 1000, uploaded: 0 }] })
  const { t, log } = fakeTransport()
  const r = await syncOnce(store, t, { now: 0 })
  expect(log).toEqual(['initiate:p1', 'put:p1@0', 'complete:p1', 'post:a'])
  expect(r).toEqual({ accepted: 1, failed: 0, retrying: 0 })
  expect(entries[0]).toMatchObject({ state: 'accepted', server_id: 'srv-a', server_code: 'EMP-20261015-090706', last_error: null })
})

test('the body sent on a retry is byte-identical (the device time inside never changes)', async () => {
  const entries = [entry('a')]
  const { store } = fakeStore(entries)
  const bodies: string[] = []
  let first = true
  const { t } = fakeTransport({
    postEntry: async (body) => {
      bodies.push(body)
      if (first) { first = false; throw new Retryable('timeout after the server saved it') }
      return { id: 'srv-a', entry_code: 'X', received_at_server: 'later' }
    },
  })
  await syncOnce(store, t, { now: 0 })
  expect(entries[0]).toMatchObject({ state: 'sync_pending', attempts: 1 })
  await syncOnce(store, t, { now: 10 ** 9 })
  expect(bodies).toHaveLength(2)
  expect(bodies[1]).toBe(bodies[0])
  expect(JSON.parse(bodies[1]!).submitted_at_device).toBe('2026-10-15T03:37:06.000Z')
  expect(entries[0]!.state).toBe('accepted')
})

test('offline: the entry waits with backoff and the rest are not tried now', async () => {
  const entries = [entry('a'), entry('b')]
  const { store } = fakeStore(entries)
  const { t, log } = fakeTransport({ postEntry: async () => { log.push('post'); throw new Retryable('No connection to the server') } })
  const r = await syncOnce(store, t, { now: 1000, rand: () => 1 })
  expect(r.stopped).toBe('offline')
  expect(log).toEqual(['post'])
  expect(entries[0]).toMatchObject({ state: 'sync_pending', attempts: 1, next_attempt_at: 1000 + 10000, last_error: 'No connection to the server' })
  expect(entries[1]!.state).toBe('queued')
})

test('an upload resumes where the server stopped, and follows an offset correction', async () => {
  const entries = [entry('a')]
  const { store } = fakeStore(entries, { a: [{ id: 'p1', size: 1000, uploaded: 0 }] })
  let puts = 0
  const { t, log } = fakeTransport({
    initiate: async () => { log.push('initiate'); return { upload_status: 'uploading', received_bytes: 400 } },
    put: async (p, offset) => {
      log.push(`put@${offset}`)
      if (puts++ === 0) throw new OffsetMismatch(600)
      return { upload_status: 'uploading', received_bytes: p.size }
    },
  })
  await syncOnce(store, t, { now: 0 })
  expect(log.filter((x) => x.startsWith('put'))).toEqual(['put@400', 'put@600'])
  expect(entries[0]!.state).toBe('accepted')
})

test('a photo already uploaded is not sent again', async () => {
  const entries = [entry('a')]
  const { store } = fakeStore(entries, { a: [{ id: 'p1', size: 10, uploaded: 1 }, { id: 'p2', size: 10, uploaded: 0 }] })
  const { t, log } = fakeTransport()
  await syncOnce(store, t, { now: 0 })
  expect(log.some((x) => x.includes('p1'))).toBe(false)
  expect(log).toContain('complete:p2')
})

test('a refusal marks only that entry for attention; the next one still goes', async () => {
  const entries = [entry('bad'), entry('good')]
  const { store } = fakeStore(entries)
  const { t } = fakeTransport({
    postEntry: async (body) => {
      if (JSON.parse(body).person_name === 'bad') throw new Permanent('Enter a valid 10-digit mobile number')
      return { id: 'srv-good', entry_code: 'X', received_at_server: 'now' }
    },
  })
  const r = await syncOnce(store, t, { now: 0 })
  expect(r).toEqual({ accepted: 1, failed: 1, retrying: 0 })
  expect(entries[0]).toMatchObject({ state: 'failed', last_error: 'Enter a valid 10-digit mobile number' })
})

test('signed out: stop, keep the entry, and do not count an attempt', async () => {
  const entries = [entry('a', { attempts: 3 }), entry('b')]
  const { store } = fakeStore(entries)
  const { t } = fakeTransport({ postEntry: async () => { throw new SignedOut('Your session has ended') } })
  const r = await syncOnce(store, t, { now: 0 })
  expect(r.stopped).toBe('signed_out')
  expect(entries[0]).toMatchObject({ state: 'sync_pending', attempts: 3 })
  expect(entries[1]!.state).toBe('queued')
})

test('backoff grows and is capped at 15 minutes', () => {
  expect(backoffMs(1, 1)).toBe(10_000)
  expect(backoffMs(3, 1)).toBe(40_000)
  expect(backoffMs(30, 1)).toBe(15 * 60_000)
  expect(backoffMs(30, 0)).toBe(7.5 * 60_000)
})
