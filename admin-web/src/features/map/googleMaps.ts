/// <reference types="google.maps" />

type GMaps = typeof google
let loading: Promise<GMaps> | null = null
const authListeners = new Set<(msg: string) => void>()

/** Called when Google rejects the key AFTER the script loaded (wrong website restriction, API not enabled, billing...). */
export function onMapsAuthFailure(fn: (msg: string) => void): () => void {
  authListeners.add(fn)
  return () => authListeners.delete(fn)
}

export const AUTH_FAILURE_TEXT =
  'Google rejected the map key. Check that "Maps JavaScript API" is enabled, billing is linked, and the key allows this website address.'

/** Loads the Google Maps JavaScript API once. The key is a *browser* key: restrict it to your site's address in Google Cloud. */
export function loadGoogleMaps(apiKey: string): Promise<GMaps> {
  if (typeof window !== 'undefined' && (window as any).google?.maps?.Map) return Promise.resolve((window as any).google as GMaps)
  if (loading) return loading
  loading = new Promise<GMaps>((resolve, reject) => {
    ;(window as any).gm_authFailure = () => authListeners.forEach((fn) => fn(AUTH_FAILURE_TEXT))
    const cb = '__fieldsyncMapsReady'
    ;(window as any)[cb] = () => resolve((window as any).google as GMaps)
    const s = document.createElement('script')
    s.src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(apiKey)}&callback=${cb}&v=weekly`
    s.async = true
    s.onerror = () => { loading = null; reject(new Error('Could not load Google Maps. Check your internet connection.')) }
    document.head.appendChild(s)
  })
  return loading
}
