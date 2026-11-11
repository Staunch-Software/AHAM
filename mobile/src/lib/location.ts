import * as Location from 'expo-location'

export type LocationStatus = 'obtained' | 'permission_denied' | 'services_disabled' | 'timeout' | 'unavailable'
export interface Fix {
  status: LocationStatus
  latitude: number | null
  longitude: number | null
  accuracy_m: number | null
  fix_at: string | null
}

const none = (status: LocationStatus): Fix => ({ status, latitude: null, longitude: null, accuracy_m: null, fix_at: null })
const from = (l: Location.LocationObject): Fix => ({
  status: 'obtained', latitude: l.coords.latitude, longitude: l.coords.longitude,
  accuracy_m: l.coords.accuracy ?? null, fix_at: new Date(l.timestamp).toISOString(),
})

/**
 * A GPS fix for "now", waiting at most `timeoutMs`. Never throws: without a fix the status says why, and the caller
 * saves anyway (a missing location never blocks an entry).
 */
export async function getFix(timeoutMs: number): Promise<Fix> {
  try {
    let perm = await Location.getForegroundPermissionsAsync()
    if (!perm.granted && perm.canAskAgain) perm = await Location.requestForegroundPermissionsAsync()
    if (!perm.granted) return none('permission_denied')
    if (!(await Location.hasServicesEnabledAsync())) return none('services_disabled')
    const timeout = new Promise<null>((r) => setTimeout(() => r(null), timeoutMs))
    const current = Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.High }).catch(() => null)
    const got = await Promise.race([current, timeout])
    if (got) return from(got)
    // no fresh fix in time: a recent one (2 min, within 200 m) is still the right place
    const last = await Location.getLastKnownPositionAsync({ maxAge: 120_000, requiredAccuracy: 200 }).catch(() => null)
    return last ? from(last) : none('timeout')
  } catch {
    return none('unavailable')
  }
}
