import { QueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { api, API_BASE } from './api'

export type LiveStatus = 'connecting' | 'live' | 'reconnecting' | 'off'

/**
 * SSE is only a signal that new data exists. On every event, and on every (re)connect, the affected
 * queries are invalidated so the UI refetches authoritative data from the REST API — which also makes
 * duplicates impossible (lists always render the server's response).
 * EventSource cannot send headers, so each connect first trades the bearer token for a 60s ticket.
 */
export function useLiveUpdates(qc: QueryClient, enabled = true): LiveStatus {
  const [status, setStatus] = useState<LiveStatus>(enabled ? 'connecting' : 'off')
  useEffect(() => {
    if (!enabled) { setStatus('off'); return }
    let es: EventSource | null = null
    let timer: ReturnType<typeof setTimeout> | undefined
    let stopped = false
    let attempt = 0
    const refresh = () => {
      for (const key of ['entries', 'dashboard', 'compliance', 'map', 'calls']) qc.invalidateQueries({ queryKey: [key] })
    }
    const retry = () => {
      if (stopped) return
      setStatus('reconnecting')
      const delay = Math.min(30000, 1000 * 2 ** attempt++) * (0.5 + Math.random() / 2)
      timer = setTimeout(connect, delay)
    }
    async function connect() {
      try {
        const { data } = await api.post('/events/ticket')
        if (stopped) return
        es = new EventSource(`${API_BASE}/events/stream?ticket=${encodeURIComponent(data.ticket)}`)
        es.onopen = () => { attempt = 0; setStatus('live'); refresh() }
        es.addEventListener('entry.created', refresh)  // a new entry synced from a Sales Officer's phone
        es.onerror = () => { es?.close(); retry() }
      } catch { retry() }
    }
    connect()
    return () => { stopped = true; clearTimeout(timer); es?.close() }
  }, [qc, enabled])
  return status
}
