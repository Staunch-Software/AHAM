import { useFocusEffect } from 'expo-router'
import { useCallback, useEffect, useState } from 'react'
import { api } from './api'
import { kvGet, kvSet } from './db'

/**
 * Server data that the app also needs offline: shows the last copy saved on the phone at once, then refreshes it
 * from the server whenever the screen is shown (and keeps the old copy if the phone is offline).
 */
export function useCached<T>(key: string | null, path: string) {
  const [data, setData] = useState<T | null>(null)
  const [fresh, setFresh] = useState(false)
  const [loading, setLoading] = useState(true)
  useEffect(() => {
    if (!key) return
    kvGet<T>(key).then((v) => { if (v) setData(v) }).finally(() => setLoading(false))
  }, [key])
  const refresh = useCallback(async () => {
    if (!key) return
    try {
      const v = await api<T>('GET', path)
      setData(v)
      setFresh(true)
      await kvSet(key, v)
    } catch {
      setFresh(false)
    } finally {
      setLoading(false)
    }
  }, [key, path])
  useFocusEffect(useCallback(() => { refresh() }, [refresh]))
  return { data, fresh, loading, refresh }
}
