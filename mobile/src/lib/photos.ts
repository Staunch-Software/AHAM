import * as Crypto from 'expo-crypto'
import { Directory, File, Paths } from 'expo-file-system'
import * as ImagePicker from 'expo-image-picker'
import { PHOTO_GPS_TIMEOUT_MS } from './config'
import { getFix } from './location'

/** A photo taken for the entry being written. Saved in app storage; uploaded with the entry. */
export interface DraftPhoto {
  id: string
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
}

const dir = () => {
  const d = new Directory(Paths.document, 'photos')
  if (!d.exists) d.create({ intermediates: true })
  return d
}

const hex = (buf: ArrayBuffer) => Array.from(new Uint8Array(buf), (b) => b.toString(16).padStart(2, '0')).join('')

export class CameraDenied extends Error {}

/**
 * Opens the camera (no gallery: evidence must be taken now). The capture time and GPS are those of the moment the
 * camera returns, recorded separately from the entry's own time and place.
 */
export async function takePhoto(): Promise<DraftPhoto | null> {
  const perm = await ImagePicker.requestCameraPermissionsAsync()
  if (!perm.granted) throw new CameraDenied('Allow camera access to take evidence photos')
  const res = await ImagePicker.launchCameraAsync({ mediaTypes: ['images'], quality: 0.6, exif: false })
  if (res.canceled || !res.assets?.length) return null
  const capturedAt = new Date().toISOString()
  const fix = await getFix(PHOTO_GPS_TIMEOUT_MS)
  const id = Crypto.randomUUID()
  const target = new File(dir(), `${id}.jpg`)
  await new File(res.assets[0]!.uri).copy(target)
  const bytes = await target.bytes()
  return {
    id, path: target.uri, size: bytes.byteLength, mime: res.assets[0]!.mimeType ?? 'image/jpeg',
    sha256: hex(await Crypto.digest(Crypto.CryptoDigestAlgorithm.SHA256, bytes)),
    captured_at: capturedAt, latitude: fix.latitude, longitude: fix.longitude, accuracy: fix.accuracy_m, fix_at: fix.fix_at,
    location_status: fix.status,
  }
}

export function deletePhotoFile(path: string) {
  try { const f = new File(path); if (f.exists) f.delete() } catch { /* already gone */ }
}

/** Removes photo files that belong to no saved entry and no draft (e.g. the app was closed mid-form long ago). */
export function cleanOrphans(keep: Set<string>) {
  try {
    for (const item of dir().list()) {
      if (item instanceof File && !keep.has(item.uri)) item.delete()
    }
  } catch { /* best effort */ }
}
