import type { MapReport } from '../../types'

export type AccuracyClass = 'good' | 'fair' | 'poor' | 'unknown'

/** GPS accuracy is a radius in metres. Over 100 m (or unknown) must not look as precise as a good fix. */
export function accuracyClass(m?: number | null): AccuracyClass {
  if (m == null) return 'unknown'
  if (m <= 30) return 'good'
  if (m <= 100) return 'fair'
  return 'poor'
}

export const ACCURACY_TEXT: Record<AccuracyClass, string> = {
  good: 'precise', fair: 'approximate', poor: 'poor accuracy', unknown: 'accuracy unknown',
}

export const STATUS_COLOR: Record<string, string> = { pending: '#d97706', approved: '#16a34a', rejected: '#dc2626' }
export const PHOTO_COLOR = '#2563eb'
export const BRANCH_COLOR = '#283079'

export interface MarkerStyle { color: string; fillOpacity: number; strokeWeight: number; scale: number }

/** Colour = review status. Imprecise or unknown locations are drawn hollow so they stand out from precise ones. */
export function markerStyle(reviewStatus: string, accuracy?: number | null): MarkerStyle {
  const cls = accuracyClass(accuracy)
  const hollow = cls === 'poor' || cls === 'unknown'
  return { color: STATUS_COLOR[reviewStatus] ?? '#64748b', fillOpacity: hollow ? 0.12 : 0.9, strokeWeight: hollow ? 3 : 1.5, scale: hollow ? 8 : 9 }
}

/** The lines shown in a marker's pop-up (plain text; the map builds DOM nodes from them, never HTML). */
export function popupLines(r: MapReport): string[] {
  const acc = accuracyClass(r.accuracy_m)
  return [
    `${r.reference}${r.revision > 1 ? ` (revision ${r.revision})` : ''}`,
    `Agent: ${r.agent_name} (${r.employee_code})`,
    `Branch: ${r.branch_name ?? '—'}`,
    `Meeting date: ${r.meeting_dates.length ? r.meeting_dates.join(', ') : '—'}`,
    ...(r.person_types.length ? [`Type of person: ${r.person_types.join(', ')}`] : []),
    `Status: ${r.review_status === 'rejected' ? 'needs correction' : r.review_status}`,
    ...(r.place_name ? [`Place: ${r.place_name}`] : []),
    `Accuracy: ${r.accuracy_m != null ? `±${Math.round(r.accuracy_m)} m` : 'unknown'} (${ACCURACY_TEXT[acc]})`,
  ]
}
