export type AccuracyClass = 'good' | 'fair' | 'poor' | 'unknown'

export interface MapMarker {
  id: string
  entry_code: string
  lat: number
  lng: number
  accuracy_m: number | null
  so_name: string
  branch: string
  category: string
  person_name: string
  rag: string
  submitted_at_device: string
  place_name: string | null
}

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

export const RAG_COLOR: Record<string, string> = {
  GREEN: '#16a34a', AMBER: '#d97706', RED: '#dc2626', RNR: '#7c3aed', PENDING: '#0284c7', NA: '#64748b',
}

export interface MarkerStyle { color: string; fillOpacity: number; strokeWeight: number; scale: number }

/** Colour = RAG. Imprecise or unknown locations are drawn hollow so they stand out from precise ones. */
export function markerStyle(rag: string, accuracy?: number | null): MarkerStyle {
  const cls = accuracyClass(accuracy)
  const hollow = cls === 'poor' || cls === 'unknown'
  return { color: RAG_COLOR[rag] ?? '#64748b', fillOpacity: hollow ? 0.12 : 0.9, strokeWeight: hollow ? 3 : 1.5, scale: hollow ? 8 : 9 }
}

/** The lines shown in a marker's pop-up (plain text; the map builds DOM nodes from them, never HTML). */
export function popupLines(m: MapMarker): string[] {
  const acc = accuracyClass(m.accuracy_m)
  return [
    m.entry_code,
    `${m.person_name} · ${m.category}`,
    `Sales Officer: ${m.so_name} (${m.branch})`,
    `RAG: ${m.rag}`,
    ...(m.place_name ? [`Place: ${m.place_name}`] : []),
    `Accuracy: ${m.accuracy_m != null ? `±${Math.round(m.accuracy_m)} m` : 'unknown'} (${ACCURACY_TEXT[acc]})`,
  ]
}
