/**
 * Build-time settings. EXPO_PUBLIC_* variables are inlined when the app is bundled, so the API address is built into
 * the APK: build with EXPO_PUBLIC_API_BASE_URL=http://<your-pc-ip>:8000 for a phone on the same Wi-Fi.
 * The default reaches the PC from the Android emulator.
 */
export const BUILT_IN_SERVER = (process.env.EXPO_PUBLIC_API_BASE_URL || 'http://10.0.2.2:8000').replace(/\/+$/, '')
/**
 * A plain-http build talks to a PC on the Wi-Fi, whose address can change from day to day, so the sign-in and Me
 * screens let the user type the PC's current address. An https build (production) always uses its own server.
 */
export const SERVER_EDITABLE = !BUILT_IN_SERVER.startsWith('https://')

/** Longest wait for a GPS fix at Submit; saving never waits longer than this. */
export const GPS_TIMEOUT_MS = 8000
/** Shorter wait when a photo is taken (the camera already took time). */
export const PHOTO_GPS_TIMEOUT_MS = 5000
export const MAX_PHOTOS = 5
export const REQUEST_TIMEOUT_MS = 20000
export const UPLOAD_TIMEOUT_MS = 90000
/** Foreground sync interval while the app is open. */
export const SYNC_INTERVAL_MS = 60000
/** Give up retrying an entry automatically after this many failed attempts (it stays saved; "Sync now" retries). */
export const MAX_AUTO_ATTEMPTS = 50
