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

const isoOf = (ms: number) => new Date(ms).toISOString().slice(0, 10)
/** The API only returns days that had reports; show a continuous axis (default 14 days) ending on the latest day we know of. */
export function fillDays(trend: { date: string; count: number }[], days = 14, now = new Date()): { date: string; count: number }[] {
  if (trend.length === 0) return []
  const localToday = isoOf(Date.UTC(now.getFullYear(), now.getMonth(), now.getDate()))
  const last = trend.reduce((a, x) => (x.date > a ? x.date : a), localToday)
  const end = Date.parse(`${last}T00:00:00Z`)
  const counts = new Map(trend.map((x) => [x.date, x.count]))
  return Array.from({ length: days }, (_, i) => {
    const d = isoOf(end - (days - 1 - i) * 86_400_000)
    return { date: d, count: counts.get(d) ?? 0 }
  })
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
