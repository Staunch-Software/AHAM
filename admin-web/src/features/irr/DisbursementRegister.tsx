import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CheckCircle2, Download, FileSpreadsheet, TriangleAlert, Upload } from 'lucide-react'
import { useRef, useState } from 'react'
import { Button, Card, cx, ErrorBox, Input, PageTitle, Select, Table, Td } from '../../components/ui'
import { api, download, errorMessage } from '../../services/api'
import { ExportButtons, fmtDay, fmtIrr, fmtNum, RowError, RowErrors, saveCsv } from './shared'

interface Summary { rows: number; new: number; replaced: number; excluded: number; exceptions: number; errors: number }
interface Result { dry_run: boolean; summary: Summary; errors: RowError[]; columns: Record<string, string>; batch_id?: string }
interface Batch { id: string; filename: string; uploaded_by: string; created_at: string; rows_total: number; rows_error: number; summary: Summary | null; errors: RowError[] }
interface ReconRow { label: string; code?: string; region?: string; rows: number; included: number; excluded: number; exceptions: number; amount: number; accounts: number; irr: number | null }
type MonthRow = ReconRow & { weight: number; weighted_roi: number }
interface Recon { from: string; to: string; decimals: number; branches: ReconRow[]; regions: ReconRow[]; total: ReconRow; months: MonthRow[]; year: MonthRow; checks: { name: string; ok: boolean; detail: string }[] }

const SUMMARY: [keyof Summary, string][] = [
  ['rows', 'Rows in the file'], ['new', 'New disbursements'], ['replaced', 'Replaced (uploaded before)'],
  ['excluded', 'Excluded (cancelled / reversed)'], ['exceptions', 'Exceptions (tenure or ROI missing, zero or negative)'], ['errors', 'Rows with errors (not saved)'],
]
const firstOfMonth = () => { const d = new Date(); return new Date(d.getFullYear(), d.getMonth(), 1, 12).toISOString().slice(0, 10) }
const today = () => new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 10)

function UploadCard() {
  const qc = useQueryClient()
  const input = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [result, setResult] = useState<Result | null>(null)
  const send = useMutation({
    mutationFn: async (dry: boolean) => {
      const fd = new FormData()
      fd.append('file', file!)
      fd.append('dry_run', String(dry))
      return (await api.post<Result>('/irr/disbursements', fd)).data
    },
    onMutate: () => setResult(null),
    onSuccess: (r) => { setResult(r); if (!r.dry_run) qc.invalidateQueries({ queryKey: ['irr'] }) },
  })
  const tooLarge = (send.error as { response?: { status?: number } } | null)?.response?.status === 413
  return (
    <Card title="Upload the Disbursement Register" subtitle="CSV or Excel. One row per disbursement (tranche). Columns: Loan account number, Disbursement reference (optional), Disbursement date, Product, Branch (code or name), Disbursed amount, Tenure in months, ROI %, Status (optional), Customer name (optional). A row uploaded again replaces the earlier copy."
      actions={<div className="flex gap-1">
        <Button variant="ghost" small onClick={() => download('/irr/disbursements/template', { format: 'csv' }, 'disbursement_register_template.csv')}><Download size={14} aria-hidden="true" />Template (CSV)</Button>
        <Button variant="ghost" small onClick={() => download('/irr/disbursements/template', { format: 'xlsx' }, 'disbursement_register_template.xlsx')}><Download size={14} aria-hidden="true" />Template (Excel)</Button>
      </div>}>
      <div className="flex flex-wrap items-center gap-3">
        <input ref={input} type="file" accept=".csv,.xlsx" className="sr-only" aria-label="Disbursement register file" onChange={(e) => { setFile(e.target.files?.[0] ?? null); setResult(null); send.reset() }} />
        <Button variant="secondary" onClick={() => input.current?.click()}><FileSpreadsheet size={16} aria-hidden="true" />{file ? file.name : 'Choose .csv or .xlsx'}</Button>
        <div className="ml-auto flex gap-2">
          <Button variant="secondary" disabled={!file || send.isPending} onClick={() => send.mutate(true)}>Check first</Button>
          <Button disabled={!file || send.isPending} onClick={() => send.mutate(false)}><Upload size={16} aria-hidden="true" />Upload</Button>
        </div>
      </div>
      <div className="mt-4"><ErrorBox error={send.error ? (tooLarge ? 'The file is too large to upload. Split it into smaller files (for example one per month) and upload each.' : errorMessage(send.error)) : null} /></div>
      {result && (
        <div className={cx('rounded-xl p-4 text-sm', result.dry_run ? 'bg-brand-50' : 'bg-emerald-50')} role="status">
          <p className="font-semibold text-brand-900">{result.dry_run ? 'Check only: nothing was saved.' : 'Uploaded.'}</p>
          <dl className="mt-2 grid gap-x-6 gap-y-1 sm:grid-cols-2 lg:grid-cols-3">
            {SUMMARY.map(([k, label]) => (
              <div key={k} className="flex justify-between gap-3"><dt className="text-slate-600">{label}</dt><dd className={cx('tabular font-semibold', k === 'errors' && result.summary.errors > 0 ? 'text-roof-700' : 'text-slate-900')}>{result.summary[k]}</dd></div>
            ))}
          </dl>
          <p className="mt-2 text-xs text-slate-500">Columns read: {Object.entries(result.columns).map(([want, got]) => (want === got ? want : `${want} ← “${got}”`)).join(' · ')}</p>
          <RowErrors errors={result.errors} />
        </div>
      )}
    </Card>
  )
}

function History() {
  const history = useQuery({ queryKey: ['irr', 'uploads'], queryFn: async () => (await api.get<Batch[]>('/irr/uploads')).data })
  return (
    <Card title="Upload history" className="mt-6" flush>
      <Table head={['When', 'File', 'By', 'Rows', 'New', 'Replaced', 'Excluded', 'Exceptions', 'Rows with errors', '']}>
        {history.data?.map((b) => (
          <tr key={b.id}>
            <Td className="whitespace-nowrap">{new Date(b.created_at).toLocaleString()}</Td>
            <Td className="max-w-[220px] truncate">{b.filename}</Td>
            <Td>{b.uploaded_by}</Td>
            <Td className="tabular">{b.rows_total}</Td>
            <Td className="tabular">{b.summary?.new ?? '–'}</Td>
            <Td className="tabular">{b.summary?.replaced ?? '–'}</Td>
            <Td className="tabular">{b.summary?.excluded ?? '–'}</Td>
            <Td className="tabular">{b.summary?.exceptions ?? '–'}</Td>
            <Td className={cx('tabular', b.rows_error > 0 && 'font-semibold text-roof-600')}>{b.rows_error}</Td>
            <Td>{b.errors.length > 0 && (
              <Button small variant="ghost" onClick={() => saveCsv(`errors_${b.filename}.csv`, [['Row', 'Column', 'Value found', 'Problem'], ...b.errors.map((e) => [e.row, e.column, e.value, e.message])])}>
                <Download size={14} aria-hidden="true" />Download errors
              </Button>
            )}</Td>
          </tr>
        ))}
        {history.data?.length === 0 && <tr><Td className="text-slate-500">No uploads yet.</Td></tr>}
      </Table>
    </Card>
  )
}

function Reconciliation() {
  const [range, setRange] = useState({ from: firstOfMonth(), to: today() })
  const [product, setProduct] = useState('')
  const params = { date_from: range.from, date_to: range.to, product: product || undefined }
  const { data, error } = useQuery({
    queryKey: ['irr', 'reconciliation', params], enabled: !!range.from && !!range.to,
    queryFn: async () => (await api.get<Recon>('/irr/reconciliation', { params })).data,
  })
  const line = (r: ReconRow, strong = false) => (
    <>
      <Td className="tabular text-right">{r.rows}</Td><Td className="tabular text-right">{r.included}</Td><Td className="tabular text-right">{r.excluded}</Td>
      <Td className={cx('tabular text-right', r.exceptions > 0 && 'text-amber-700')}>{r.exceptions}</Td>
      <Td className="tabular text-right">{fmtNum(r.amount)}</Td><Td className="tabular text-right">{r.accounts}</Td>
      <Td className={cx('tabular text-right', strong && 'font-semibold')}>{fmtIrr(r.irr, data?.decimals)}</Td>
    </>
  )
  return (
    <Card title="Reconciliation" className="mt-6" flush
      subtitle="What was uploaded for the period and what the IRR uses. Branch, region and company totals are each worked out from the disbursements, so they must agree."
      actions={<ExportButtons url="/irr/reconciliation" params={params} name={`irr_reconciliation_${range.from}_${range.to}`} />}>
      <div className="flex flex-wrap items-end gap-3 px-5 pb-4">
        <label className="text-xs text-slate-500">Disbursed from<Input type="date" value={range.from} onChange={(e) => setRange({ ...range, from: e.target.value })} /></label>
        <label className="text-xs text-slate-500">to<Input type="date" value={range.to} onChange={(e) => setRange({ ...range, to: e.target.value })} /></label>
        <label className="text-xs text-slate-500">Product<Select value={product} onChange={(e) => setProduct(e.target.value)}><option value="">HL and NHL</option><option value="HL">HL</option><option value="NHL">NHL</option></Select></label>
        {data?.checks.map((c) => (
          <span key={c.name} className={cx('inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium', c.ok ? 'bg-emerald-50 text-emerald-700' : 'bg-roof-50 text-roof-700')}>
            {c.ok ? <CheckCircle2 size={14} aria-hidden="true" /> : <TriangleAlert size={14} aria-hidden="true" />}{c.name}: {c.detail}
          </span>
        ))}
      </div>
      <div className="px-5"><ErrorBox error={error ? errorMessage(error) : null} /></div>
      {data && (
        <Table head={['Branch / region', 'Rows uploaded', 'Included', 'Excluded', 'Exceptions', 'Included amount (₹)', 'Number of loan accounts', 'Weighted average IRR (%)']}>
          {data.branches.map((r) => <tr key={`b-${r.label}`}><Td>{r.label} <span className="text-xs text-slate-500">{r.code} · {r.region}</span></Td>{line(r)}</tr>)}
          {data.regions.map((r) => <tr key={`r-${r.label}`} className="bg-slate-50/60"><Td className="font-medium">Region: {r.label}</Td>{line(r)}</tr>)}
          <tr className="bg-slate-50"><Td className="font-semibold text-brand-900">{data.total.label}</Td>{line(data.total, true)}</tr>
        </Table>
      )}
      {data && <p className="px-5 py-3 text-xs text-slate-500">{fmtDay(data.from)} to {fmtDay(data.to)}. Rows with errors are never saved, so they are not counted here; see the upload history.</p>}
      {data && data.months.length > 0 && (
        <div className="border-t border-slate-100 pt-3">
          <p className="px-5 text-sm font-semibold text-brand-900">Year to date, month by month</p>
          <p className="px-5 pb-2 text-xs text-slate-500">The year's numerator (Σ amount × tenure × ROI) and denominator (Σ amount × tenure) must equal the sum of the months. A loan disbursed in tranches in two months counts once in the year, so loan accounts do not add up.</p>
          <Table head={['Month', 'Included rows', 'Included amount (₹)', 'Number of loan accounts', 'Denominator: Σ amount × tenure', 'Numerator: Σ amount × tenure × ROI', 'Weighted average IRR (%)']} exportName="IRR year to date by month">
            {[...data.months, data.year].map((m, i) => (
              <tr key={m.label} className={cx(i === data.months.length && 'bg-slate-50 font-semibold')}>
                <Td>{m.label}</Td><Td className="tabular text-right">{m.included}</Td><Td className="tabular text-right">{fmtNum(m.amount)}</Td>
                <Td className="tabular text-right">{m.accounts}</Td><Td className="tabular text-right">{fmtNum(m.weight)}</Td><Td className="tabular text-right">{fmtNum(m.weighted_roi)}</Td>
                <Td className="tabular text-right">{fmtIrr(m.irr, data.decimals)}</Td>
              </tr>
            ))}
          </Table>
        </div>
      )}
    </Card>
  )
}

export default function DisbursementRegister() {
  return (
    <>
      <PageTitle subtitle="Check a file first to see what would change and every problem, row by row; then upload. The IRR report uses what is uploaded here.">Disbursement register</PageTitle>
      <UploadCard />
      <History />
      <Reconciliation />
    </>
  )
}
