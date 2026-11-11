import { api } from './api'
import { csvCell } from './format'

/** One exported row: plain values in the same order as the header. */
export type Cells = (string | number | boolean | null | undefined)[]

const fileName = (name: string, ext: string) =>
  `${name.replace(/[^\w-]+/g, '_').replace(/^_+|_+$/g, '') || 'export'}_${new Date().toISOString().slice(0, 10)}.${ext}`

function save(blob: Blob, filename: string) {
  const href = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = href
  a.download = filename
  a.click()
  setTimeout(() => URL.revokeObjectURL(href), 1000)
}

/** A CSV that Excel opens with the right characters (₹, –) and without running formulas. */
export function saveCsv(name: string, header: string[], rows: Cells[]) {
  const text = '﻿' + [header, ...rows].map((r) => r.map(csvCell).join(',')).join('\r\n')
  save(new Blob([text], { type: 'text/csv;charset=utf-8' }), fileName(name, 'csv'))
}

/** An Excel file, built by the server from the same rows. */
export async function saveXlsx(name: string, header: string[], rows: Cells[]) {
  const res = await api.post('/exports/xlsx', { name, header, rows: rows.map((r) => r.map((v) => v ?? null)) }, { responseType: 'blob' })
  save(res.data as Blob, fileName(name, 'xlsx'))
}

/** Every page of a paged list endpoint ({items, total}), so an export is never just the page on screen. */
export async function allPages<T>(url: string, params: Record<string, unknown> = {}, pageSize = 100): Promise<T[]> {
  const out: T[] = []
  for (let page = 1; ; page++) {
    const { data } = await api.get<{ items: T[]; total: number }>(url, { params: { ...params, page, page_size: pageSize } })
    out.push(...data.items)
    if (!data.items.length || out.length >= data.total) return out
  }
}

/** The text of a rendered table body, skipping the columns marked false (buttons and the like). Several lines
 *  in one cell (a name above a mobile number) are joined with " · ". */
export function tableCells(table: HTMLTableElement, keep: boolean[]): string[][] {
  return Array.from(table.tBodies[0]?.rows ?? []).filter((tr) => tr.cells.length > 1).map((tr) =>
    Array.from(tr.cells).filter((_, i) => keep[i] !== false).map((td) =>
      (td.innerText || td.textContent || '').split('\n').map((s) => s.trim()).filter(Boolean).join(' · ')))
}
