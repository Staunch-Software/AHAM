import { CheckCircle2, Download, FileSpreadsheet } from 'lucide-react'
import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Button, Card, ErrorBox, PageTitle } from '../../components/ui'
import { api, errorMessage } from '../../services/api'
import { csvCell } from '../../services/format'
import type { Page, SubmissionRow } from '../../types'
import { Filters, filterParams } from '../submissions/Filters'

const COLS: [string, (r: SubmissionRow) => unknown][] = [
  ['reference', (r) => r.reference], ['revision', (r) => r.revision], ['submission_id', (r) => r.id], ['type_of_person', (r) => r.person_types.join('; ')], ['agent', (r) => r.agent_name], ['employee_id', (r) => r.employee_code],
  ['branch', (r) => r.branch_name], ['form', (r) => `${r.form_title} v${r.form_version}`],
  ['submitted_at_device', (r) => r.submitted_at_device], ['received_at_server', (r) => r.received_at_server],
  ['accepted_at_server', (r) => r.accepted_at_server], ['status', (r) => r.status], ['review_status', (r) => (r.review_status === 'rejected' ? 'needs correction' : r.review_status)],
  ['photo_count', (r) => r.photo_count], ['has_submission_location', (r) => r.has_location],
]
const MAX_ROWS = 10000

export default function Reports() {
  const [params, setParams] = useSearchParams()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [note, setNote] = useState<string | null>(null)

  async function exportCsv() {
    setBusy(true); setError(null); setNote(null)
    try {
      const rows: SubmissionRow[] = []
      for (let page = 1; rows.length < MAX_ROWS; page++) {
        const { data } = await api.get<Page<SubmissionRow>>('/submissions', { params: { ...filterParams(params), page, page_size: 100 } })
        rows.push(...data.items)
        if (rows.length >= data.total || data.items.length === 0) break
      }
      const csv = [COLS.map(([h]) => h).join(','), ...rows.map((r) => COLS.map(([, f]) => csvCell(f(r))).join(','))].join('\r\n')
      const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }))
      const a = Object.assign(document.createElement('a'), { href: url, download: `submissions-${new Date().toISOString().slice(0, 10)}.csv` })
      a.click(); URL.revokeObjectURL(url)
      setNote(`Exported ${rows.length} row(s)${rows.length >= MAX_ROWS ? ` (capped at ${MAX_ROWS}; narrow the filters)` : ''}.`)
    } catch (e) { setError(errorMessage(e)) } finally { setBusy(false) }
  }

  return (
    <>
      <PageTitle subtitle="Choose what to include, then download it as a spreadsheet.">Reports</PageTitle>
      <Filters params={params} onChange={setParams} />
      <Card title="Export submissions (CSV)">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-start gap-3">
            <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-emerald-50 text-emerald-600" aria-hidden="true"><FileSpreadsheet size={20} /></span>
            <p className="max-w-lg text-sm text-slate-600">Exports the submissions matching the filters above — summary fields only, no photos.</p>
          </div>
          <Button onClick={exportCsv} disabled={busy}><Download size={16} aria-hidden="true" />{busy ? 'Exporting…' : 'Download CSV'}</Button>
        </div>
        <div className="mt-3"><ErrorBox error={error} /></div>
        {note && <p role="status" className="mt-3 inline-flex items-center gap-1.5 text-sm font-medium text-emerald-700"><CheckCircle2 size={16} aria-hidden="true" />{note}</p>}
      </Card>
    </>
  )
}
