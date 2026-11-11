/**
 * Rules the phone applies before the server sees an entry. They mirror the backend exactly
 * (backend/app/services/phone.py and calendar.py), so the Entry ID shown offline is the one the server builds.
 */

/** Section 4.3: strip non-digits, then drop a leading 0 (11 digits) or 91 (12 digits). */
export function cleanPhone(raw: string): string {
  let digits = raw.trim().replace(/\.0+$/, '').replace(/[^0-9]/g, '')
  if (digits.length === 11 && digits.startsWith('0')) digits = digits.slice(1)
  else if (digits.length === 12 && digits.startsWith('91')) digits = digits.slice(2)
  return digits
}

export const isValidPhone = (cleaned: string) => /^[6-9]\d{9}$/.test(cleaned)

export function phoneProblem(raw: string): string | null {
  if (!raw.trim()) return 'Enter the mobile (WhatsApp) number'
  const c = cleanPhone(raw)
  if (c.length !== 10) return 'A mobile number has 10 digits'
  if (!isValidPhone(c)) return 'A mobile number starts with 6, 7, 8 or 9'
  return null
}

/** India has one time zone with no daylight saving: IST = UTC+05:30. */
const IST_OFFSET_MS = 330 * 60 * 1000
const p2 = (n: number) => String(n).padStart(2, '0')

function istParts(d: Date) {
  const t = new Date(d.getTime() + IST_OFFSET_MS)
  return { y: t.getUTCFullYear(), mo: t.getUTCMonth() + 1, d: t.getUTCDate(), h: t.getUTCHours(), mi: t.getUTCMinutes(), s: t.getUTCSeconds() }
}

/** Section 4.2: <EmpID>-<YYYYMMDD>-<HHMMSS> in IST, truncated (not rounded) to the second. */
export function entryCode(empId: string, submittedAt: Date): string {
  const t = istParts(submittedAt)
  return `${empId.toUpperCase()}-${t.y}${p2(t.mo)}${p2(t.d)}-${p2(t.h)}${p2(t.mi)}${p2(t.s)}`
}

/** The entry date (IST) as YYYY-MM-DD. */
export function istDate(d: Date): string {
  const t = istParts(d)
  return `${t.y}-${p2(t.mo)}-${p2(t.d)}`
}

/** "HH:MM" -> "HH:MM:00", or null when blank. Throws for a time that is not a real time. */
export function kekaTime(raw: string): string | null {
  const v = raw.trim()
  if (!v) return null
  const m = /^([01]?\d|2[0-3]):([0-5]\d)$/.exec(v)
  if (!m) throw new Error('Use 24-hour HH:MM, e.g. 09:15')
  return `${p2(Number(m[1]))}:${m[2]}:00`
}

export const CATEGORIES = [
  { key: 'lead', label: 'Lead', hint: 'Wants a home loan' },
  { key: 'prospect', label: 'Prospect', hint: 'May need one later' },
  { key: 'dsa_connector', label: 'DSA/Connector', hint: 'Brings customers' },
  { key: 'contact_point', label: 'Contact Point', hint: 'Shop or local contact' },
  { key: 'existing_customer', label: 'Existing Customer', hint: 'Already has a loan' },
  { key: 'existing_applicant', label: 'Existing Applicant', hint: 'Applied already' },
] as const
export type CategoryKey = (typeof CATEGORIES)[number]['key']
export const categoryLabel = (k: string) => CATEGORIES.find((c) => c.key === k)?.label ?? k
export const LEAD_CATEGORIES = new Set<string>(['lead', 'prospect'])

/** YYYY-MM-DD plus n days. */
export const addDaysIso = (iso: string, n: number) => new Date(Date.parse(`${iso}T00:00:00Z`) + n * 86400000).toISOString().slice(0, 10)

/**
 * Section 4.4: the day an entry counts on: its own day, or the next working day when made on a Sunday or a holiday
 * (checked again until one is found). Mirrors backend calendar.count_date.
 */
export function countDate(isoDay: string, holidays: ReadonlySet<string>): string {
  let d = isoDay
  while (new Date(`${d}T00:00:00Z`).getUTCDay() === 0 || holidays.has(d)) d = addDaysIso(d, 1)
  return d
}
