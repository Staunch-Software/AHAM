export const fmtServer = (ts?: string | null) => (ts ? new Date(ts).toLocaleString() : '—')

/** Date and time of a server timestamp as two short strings (tables show them on two lines). */
export function fmtParts(ts?: string | null): { date: string; time: string } | null {
  if (!ts) return null
  const d = new Date(ts)
  return { date: d.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' }), time: d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' }) }
}

/** Device-reported time rendered in the agent's own local time when the offset is known. */
export function fmtDevice(ts?: string | null, offsetMin?: number | null): string {
  if (!ts) return '—'
  if (offsetMin == null) return `${new Date(ts).toLocaleString()} (viewer local)`
  const shifted = new Date(new Date(ts).getTime() + offsetMin * 60000)
  const sign = offsetMin >= 0 ? '+' : '-'
  const a = Math.abs(offsetMin)
  const hh = String(Math.floor(a / 60)).padStart(2, '0')
  const mm = String(a % 60).padStart(2, '0')
  return `${shifted.toISOString().replace('T', ' ').slice(0, 19)} (UTC${sign}${hh}:${mm})`
}

/** Unavailable coordinates are null — never treat 0 as "missing", never treat null as 0. */
export const validCoords = (lat?: number | null, lon?: number | null): lat is number =>
  lat != null && lon != null && Math.abs(lat) <= 90 && Math.abs(lon) <= 180

/** Plain Google Maps link (no API key needed). Opens the pin at the exact coordinates. */
export const mapUrl = (lat: number, lon: number) =>
  `https://www.google.com/maps?q=${lat},${lon}`

export function accuracyLabel(m?: number | null): string {
  if (m == null) return 'accuracy unknown'
  return `±${Math.round(m)} m${m > 100 ? ' (poor accuracy)' : ''}`
}

/** Neutralise spreadsheet formula injection in exported cells. */
export function csvCell(v: unknown): string {
  let s = v == null ? '' : String(v)
  if (/^[=+\-@\t\r]/.test(s)) s = `'${s}`
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
}

/** ₹ with Indian digit grouping, e.g. 4000000 → "₹40,00,000". */
export const fmtRupees = (n: number) => `₹${n.toLocaleString('en-IN')}`

/** The same amount in words a caller says, e.g. "40 lakh", "1.25 crore". */
export const rupeesInWords = (n: number) =>
  n >= 1e7 ? `${+(n / 1e7).toFixed(2)} crore` : n >= 1e5 ? `${+(n / 1e5).toFixed(2)} lakh` : ''

/**
 * A whole number typed by a person (commas and spaces allowed), or 'bad' for anything else: "40L", "7 lacks" or
 * "35.5 lakh" are refused, never turned into ₹40, ₹7 or ₹355 (section 7.4 / 15: amounts must be numbers).
 */
export function parseWhole(s?: string | null): number | null | 'bad' {
  const t = (s ?? '').trim()
  if (!t) return null
  if (!/^[\d,\s]+$/.test(t)) return 'bad'
  const n = Number(t.replace(/[,\s]/g, ''))
  return Number.isSafeInteger(n) ? n : 'bad'
}

/** True for a YYYY-MM-DD that falls on a Sunday (dates offered to callers are working days, 7.2). */
export const isSunday = (iso?: string | null) => !!iso && new Date(`${iso}T00:00:00`).getDay() === 0
