import { Download, FileSpreadsheet } from 'lucide-react'
import { ReactNode, useState } from 'react'
import { Button, Table, Td } from '../../components/ui'
import { download, errorMessage } from '../../services/api'
import { csvCell } from '../../services/format'

export type Period = 'TD' | 'MTD' | 'YTD'
export type ProductClass = 'HL' | 'NHL'
export type Level = 'branch' | 'region' | 'company'
export const PERIODS: Period[] = ['TD', 'MTD', 'YTD']
export const PERIOD_LABELS: Record<Period, string> = { TD: 'Today (TD)', MTD: 'Month to date (MTD)', YTD: 'Year to date (YTD)' }
export const CLASSES: ProductClass[] = ['HL', 'NHL']
export const CLASS_LABELS: Record<ProductClass, string> = { HL: 'Home Loan (HL)', NHL: 'Non-Home Loan / LAP (NHL)' }
export const LEVELS: { value: Level; label: string }[] = [{ value: 'branch', label: 'By branch' }, { value: 'region', label: 'By region' }, { value: 'company', label: 'Company' }]

export interface Cell { accounts: number; irr: number | null; amount: number; records: number }
interface RowBase { label: string; code?: string; region?: string; branch_id?: string; region_id?: string | null; flags: string[] }
export interface PeriodRow extends RowBase { periods: Record<Period, Cell> }
export interface ClassRow extends RowBase { classes: Record<ProductClass, Cell> }
export interface PeriodReport {
  as_of: string; product: ProductClass; level: Level; decimals: number; periods: Record<Period, { from: string; to: string }>
  rows: PeriodRow[]; total: PeriodRow; warnings: string[]; band: { min: number; max: number } | null; open_exceptions: Record<Period, number>
}
export interface MonthReport { as_of: string; level: Level; decimals: number; period: { from: string; to: string }; rows: ClassRow[]; total: ClassRow; warnings: string[]; open_exceptions: number }
export interface RowError { row: number; column: string; value: string; message: string }

/** No IRR (a group without disbursements) is a dash, never 0%. */
export const fmtIrr = (v: number | null | undefined, decimals = 2) => (v == null ? '–' : v.toFixed(decimals))
/** "2026-11-05" -> "05-11-2026", the way the register writes dates. */
export const fmtDay = (iso?: string | null) => (iso ? iso.slice(0, 10).split('-').reverse().join('-') : '–')
export const fmtNum = (n: number | null | undefined, max = 2) => (n == null ? '–' : n.toLocaleString('en-IN', { maximumFractionDigits: max }))

/** "Export: CSV · Excel" for a table endpoint that accepts format=csv|xlsx. */
export function ExportButtons({ url, params, name }: { url: string; params: Record<string, unknown>; name: string }) {
  const [error, setError] = useState<string | null>(null)
  const go = async (format: 'csv' | 'xlsx') => {
    setError(null)
    try { await download(url, { ...params, format }, `${name}.${format}`) } catch (e) { setError(errorMessage(e)) }
  }
  return (
    <div role="group" aria-label="Export" className="flex flex-wrap items-center gap-2">
      <span className="text-xs font-medium text-slate-500">Export</span>
      <Button small variant="secondary" aria-label="Export as CSV" onClick={() => go('csv')}><Download size={14} aria-hidden="true" />CSV</Button>
      <Button small variant="secondary" aria-label="Export as Excel" onClick={() => go('xlsx')}><FileSpreadsheet size={14} aria-hidden="true" />Excel</Button>
      {error && <span role="alert" className="text-xs text-roof-600">{error}</span>}
    </div>
  )
}

/** A table whose columns come in named pairs (for example "Today (TD)" over accounts and IRR). */
export function GroupedTable({ lead, groups, children }: { lead: string[]; groups: { label: string; cols: string[] }[]; children: ReactNode }) {
  const th = 'border-y border-slate-200 px-4 py-2.5'
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead className="bg-slate-50/80 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
          <tr>
            {lead.map((h) => <th key={h} scope="col" rowSpan={2} className={`${th} whitespace-nowrap align-bottom`}>{h}</th>)}
            {groups.map((g) => <th key={g.label} scope="colgroup" colSpan={g.cols.length} className={`${th} border-l text-center text-brand-800`}>{g.label}</th>)}
          </tr>
          <tr>{groups.flatMap((g) => g.cols.map((c, i) => <th key={`${g.label}-${c}`} scope="col" className={`${th} text-right normal-case tracking-normal ${i === 0 ? 'border-l' : ''}`}>{c}</th>))}</tr>
        </thead>
        <tbody className="divide-y divide-slate-100 [&>tr]:transition-colors [&>tr:hover]:bg-brand-50/40">{children}</tbody>
      </table>
    </div>
  )
}

export function saveCsv(filename: string, rows: unknown[][]) {
  const blob = new Blob(['﻿' + rows.map((r) => r.map(csvCell).join(',')).join('\n')], { type: 'text/csv' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = filename
  a.click()
}

/** Every problem of an upload as a table, with a CSV of the same rows to fix the file from. */
export function RowErrors({ errors, filename = 'disbursement_register_errors.csv' }: { errors: RowError[]; filename?: string }) {
  if (!errors.length) return null
  const rows = new Set(errors.map((e) => e.row)).size
  const save = () => saveCsv(filename, [['Row', 'Column', 'Value found', 'Problem'], ...errors.map((e) => [e.row, e.column, e.value, e.message])])
  return (
    <div className="mt-3">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <p className="font-medium text-roof-700">{errors.length} problem{errors.length > 1 ? 's' : ''} in {rows} row{rows > 1 ? 's' : ''}. These rows are not saved: correct them in the file and upload it again.</p>
        <Button small variant="secondary" onClick={save}><Download size={14} aria-hidden="true" />Download errors</Button>
      </div>
      <div className="max-h-80 overflow-y-auto rounded-lg border border-slate-200 bg-white" data-testid="row-errors">
        <Table head={['Row', 'Column', 'Value found', 'Problem']}>
          {errors.map((e, i) => (
            <tr key={i}>
              <Td className="tabular">{e.row}</Td>
              <Td className="whitespace-nowrap">{e.column}</Td>
              <Td className="font-mono text-xs">{e.value || <span className="font-sans text-slate-400">(empty)</span>}</Td>
              <Td>{e.message}</Td>
            </tr>
          ))}
        </Table>
      </div>
    </div>
  )
}
