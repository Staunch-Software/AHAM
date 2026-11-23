import { Download, FileSpreadsheet } from 'lucide-react'
import { ReactNode, useState } from 'react'
import { Button, ExportBar, Table, Td } from '../../components/ui'
import { download, errorMessage } from '../../services/api'

export type Period = 'TD' | 'MTD' | 'YTD'
export type ProductClass = 'HL' | 'NHL'
export type Level = 'branch' | 'region' | 'company'
export const PERIODS: Period[] = ['TD', 'MTD', 'YTD']
export const PERIOD_LABELS: Record<Period, string> = { TD: 'For the day (TD)', MTD: 'Month to date (MTD)', YTD: 'Year to date (YTD)' }
export const CLASSES: ProductClass[] = ['HL', 'NHL']
export const CLASS_LABELS: Record<ProductClass, string> = { HL: 'Home Loan (HL)', NHL: 'Non-Home Loan / LAP (NHL)' }
export const LEVELS: { value: Level; label: string }[] = [{ value: 'branch', label: 'By branch' }, { value: 'region', label: 'By region' }, { value: 'company', label: 'Company' }]

/** records = "No.": disbursement rows, so a loan paid in two tranches counts twice. */
export interface Cell { records: number; irr: number | null; amount: number }
interface RowBase { label: string; code?: string; region?: string; branch_id?: string; region_id?: string | null; flags: string[] }
/** A column of the TD / MTD / YTD report: one of the three periods, or a chosen date range (BRD 3.1). */
export type ReportPeriod = Period | 'RANGE'
export interface PeriodRow extends RowBase { periods: Partial<Record<ReportPeriod, Cell>> }
export interface ClassRow extends RowBase { classes: Record<ProductClass, Cell> }
export interface PeriodReport {
  as_of: string; product: ProductClass; level: Level; decimals: number; periods: Partial<Record<ReportPeriod, { from: string; to: string; label: string }>>
  rows: PeriodRow[]; total: PeriodRow; warnings: string[]; band: { min: number; max: number } | null; open_exceptions: Partial<Record<ReportPeriod, number>>
}
export interface MonthReport { as_of: string; level: Level; decimals: number; period: { from: string; to: string }; rows: ClassRow[]; total: ClassRow; warnings: string[]; open_exceptions: number }
export interface RowError { row: number; column: string; value: string; message: string }

/** No IRR (a group without disbursements) is a dash, never 0%. */
export const fmtIrr = (v: number | null | undefined, decimals = 2) => (v == null ? '–' : v.toFixed(decimals))
/** "2026-11-05" -> "05-11-2026", the way the register writes dates. */
export const fmtDay = (iso?: string | null) => (iso ? iso.slice(0, 10).split('-').reverse().join('-') : '–')
export const fmtNum = (n: number | null | undefined, max = 2) => (n == null ? '–' : n.toLocaleString('en-IN', { maximumFractionDigits: max }))

/** "Export: CSV · Excel" for a table endpoint that accepts format=csv|xlsx. */
export function ExportButtons({ url, params, name, includeMaster = false }: { url: string; params: Record<string, unknown>; name: string; includeMaster?: boolean }) {
  const [error, setError] = useState<string | null>(null)
  const [downloadingMaster, setDownloadingMaster] = useState(false)

  const go = async (format: 'csv' | 'xlsx') => {
    setError(null)
    try { await download(url, { ...params, format }, `${name}.${format}`) } catch (e) { setError(errorMessage(e)) }
  }
  const goMaster = async () => {
    setError(null)
    setDownloadingMaster(true)
    try {
      const asOf = params.as_of ? String(params.as_of) : undefined
      await download('/irr/export/complete-workbook', { as_of: asOf, region_id: params.region_id, branch_id: params.branch_id }, `IRR_Master_Workbook_${asOf || 'all'}.xlsx`)
    } catch (e) {
      setError(errorMessage(e))
    } finally {
      setDownloadingMaster(false)
    }
  }
  return (
    <div role="group" aria-label="Export" className="flex flex-wrap items-center gap-2">
      <span className="text-xs font-medium text-slate-500">Export</span>
      <Button small variant="secondary" aria-label="Export as CSV" onClick={() => go('csv')}><Download size={14} aria-hidden="true" />CSV</Button>
      <Button small variant="secondary" aria-label="Export as Excel" onClick={() => go('xlsx')}><FileSpreadsheet size={14} aria-hidden="true" />Excel</Button>
      {includeMaster && (
        <Button small variant="secondary" disabled={downloadingMaster} onClick={goMaster} className="border-emerald-300 bg-emerald-50/60 text-emerald-800 hover:bg-emerald-100/70">
          <FileSpreadsheet size={14} className="text-emerald-700" />{downloadingMaster ? 'Generating…' : 'Master Workbook (.xlsx)'}
        </Button>
      )}
      {error && <span role="alert" className="text-xs text-roof-600">{error}</span>}
    </div>
  )
}

/** A table whose columns come in named pairs (for example "For the day (TD)" over No. and IRR). */
export function GroupedTable({ lead, groups, children }: { lead: string[]; groups: { label: string; cols: string[] }[]; children: ReactNode }) {
  const th = 'border-y border-slate-200 px-4 py-2.5 bg-slate-50'
  return (
    <div className="overflow-x-auto overflow-y-auto max-h-[min(520px,65vh)] custom-scrollbar min-h-0">
      <table className="w-full text-left text-sm border-separate border-spacing-0">
        <thead className="sticky top-0 z-20 bg-slate-50 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
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

export const ERROR_HEADER = ['Row', 'Column', 'Value found', 'Problem']
export const errorCells = (errors: RowError[]) => errors.map((e) => [e.row, e.column, e.value, e.message])

/** Every problem of an upload as a table, with CSV and Excel of the same rows to fix the file from. */
export function RowErrors({ errors, name = 'Disbursement register problems' }: { errors: RowError[]; name?: string }) {
  if (!errors.length) return null
  const rows = new Set(errors.map((e) => e.row)).size
  return (
    <div className="mt-3">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <p className="font-medium text-roof-700">{errors.length} problem{errors.length > 1 ? 's' : ''} in {rows} row{rows > 1 ? 's' : ''}. These rows are not saved: correct them in the file and upload it again.</p>
      </div>
      <div className="max-h-80 overflow-y-auto rounded-lg border border-slate-200 bg-white" data-testid="row-errors">
        <Table head={ERROR_HEADER} exportName={name} exportAll={async () => errorCells(errors)}>
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
