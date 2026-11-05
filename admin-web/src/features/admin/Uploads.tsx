import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Download, FileSpreadsheet, KeyRound, Upload } from 'lucide-react'
import { useRef, useState } from 'react'
import { Button, Card, cx, ErrorBox, PageTitle, Table, Td, Toggle } from '../../components/ui'
import { api, download, errorMessage } from '../../services/api'
import { useAuth } from '../../services/auth'
import { csvCell } from '../../services/format'

type Kind = 'roster' | 'attendance' | 'login-register'
interface Result { dry_run: boolean; summary: Record<string, number | string | null>; errors: { row: number; emp_code?: string; tcs_id?: string; message: string }[]; credentials?: { emp_code: string; name: string; temporary_password: string }[]; batch_id?: string }
interface Batch { id: string; kind: string; filename: string; uploaded_by: string; created_at: string; rows_total: number; rows_ok: number; rows_error: number }

const KINDS: { kind: Kind; title: string; perm: string; template: string; hint: string }[] = [
  { kind: 'roster', title: 'Employee roster (FOS Spoke)', perm: 'reference.import', template: 'roster', hint: 'Emp ID, Name, Designation, Region, Cluster, Branch, Spoke, Joining date, Exit date. The only source of who a Sales Officer is: the branch on an entry comes from here.' },
  { kind: 'attendance', title: 'Daily attendance', perm: 'reference.import', template: 'attendance', hint: 'Emp ID, Date, Status (or one column per date). P, P(MS), P(R) and P(MS)(R) count as present; anything else is absent.' },
  { kind: 'login-register', title: 'Login register (MIS)', perm: 'login_register.upload', template: 'login_register', hint: 'TCS ID, Customer contact (up to 3 numbers), Login date, Product, Final status, Source, Emp code. Logins are matched on every number; the latest row wins for a repeated TCS ID.' },
]

function UploadCard({ k }: { k: (typeof KINDS)[number] }) {
  const qc = useQueryClient()
  const input = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [issue, setIssue] = useState(false)
  const [result, setResult] = useState<Result | null>(null)
  const send = useMutation({
    mutationFn: async (dry: boolean) => {
      const fd = new FormData()
      fd.append('file', file!)
      fd.append('dry_run', String(dry))
      if (k.kind === 'roster') fd.append('issue_passwords', String(issue))
      return (await api.post<Result>(`/imports/${k.kind}`, fd)).data
    },
    onSuccess: (r) => { setResult(r); if (!r.dry_run) { qc.invalidateQueries({ queryKey: ['imports'] }); qc.invalidateQueries({ queryKey: ['entries'] }) } },
  })
  const saveCredentials = () => {
    const rows = [['Emp ID', 'Name', 'Temporary password'], ...(result?.credentials ?? []).map((c) => [c.emp_code, c.name, c.temporary_password])]
    const blob = new Blob([rows.map((r) => r.map(csvCell).join(',')).join('\n')], { type: 'text/csv' })
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'temporary_passwords.csv'; a.click()
  }
  return (
    <Card title={k.title} subtitle={k.hint} actions={<Button variant="ghost" small onClick={() => download(`/imports/templates/${k.template}`, {}, `${k.template}_template.csv`)}><Download size={14} aria-hidden="true" />Template</Button>}>
      <div className="flex flex-wrap items-center gap-3">
        <input ref={input} type="file" accept=".csv,.xlsx" className="sr-only" aria-label={`${k.title} file`} onChange={(e) => { setFile(e.target.files?.[0] ?? null); setResult(null) }} />
        <Button variant="secondary" onClick={() => input.current?.click()}><FileSpreadsheet size={16} aria-hidden="true" />{file ? file.name : 'Choose .csv or .xlsx'}</Button>
        {k.kind === 'roster' && <Toggle label="Give new people a temporary password" checked={issue} onChange={setIssue} />}
        <div className="ml-auto flex gap-2">
          <Button variant="secondary" disabled={!file || send.isPending} onClick={() => send.mutate(true)}>Check first</Button>
          <Button disabled={!file || send.isPending} onClick={() => send.mutate(false)}><Upload size={16} aria-hidden="true" />Upload</Button>
        </div>
      </div>
      <div className="mt-4"><ErrorBox error={send.error ? errorMessage(send.error) : null} /></div>
      {result && (
        <div className={cx('rounded-xl p-4 text-sm', result.dry_run ? 'bg-brand-50' : 'bg-emerald-50')} role="status">
          <p className="font-semibold text-brand-900">{result.dry_run ? 'Check only: nothing was saved.' : 'Uploaded.'}</p>
          <p className="mt-1 text-slate-700">{Object.entries(result.summary).filter(([, v]) => v != null).map(([key, v]) => `${key.replace(/_/g, ' ')}: ${v}`).join(' · ')}</p>
          {result.errors.length > 0 && (
            <details className="mt-2"><summary className="cursor-pointer font-medium text-roof-700">{result.errors.length} row problem{result.errors.length > 1 ? 's' : ''}</summary>
              <ul className="mt-2 max-h-48 space-y-1 overflow-y-auto text-xs text-slate-700">{result.errors.map((e, i) => <li key={i}>Row {e.row}{e.emp_code && ` · ${e.emp_code}`}{e.tcs_id && ` · ${e.tcs_id}`}: {e.message}</li>)}</ul>
            </details>
          )}
          {!!result.credentials?.length && (
            <div className="mt-3 flex flex-wrap items-center gap-3 rounded-lg border border-gold-300 bg-gold-50 p-3">
              <KeyRound size={16} className="text-gold-700" aria-hidden="true" />
              <span className="text-slate-700">{result.credentials.length} temporary passwords. They are shown only now: save them and hand them over privately.</span>
              <Button small variant="gold" onClick={saveCredentials}>Download passwords</Button>
            </div>
          )}
        </div>
      )}
    </Card>
  )
}

export default function Uploads() {
  const { can } = useAuth()
  const kinds = KINDS.filter((k) => can(k.perm))
  const history = useQuery({ queryKey: ['imports'], queryFn: async () => (await api.get<Batch[]>('/imports')).data })
  return (
    <>
      <PageTitle subtitle="Check a file first to see what would change; then upload. Every upload is kept in the history below.">Uploads</PageTitle>
      <div className="space-y-6">{kinds.map((k) => <UploadCard key={k.kind} k={k} />)}</div>
      <Card title="Upload history" className="mt-6" flush>
        <Table head={['When', 'What', 'File', 'By', 'Rows', 'Problems']}>
          {history.data?.map((b) => (
            <tr key={b.id}><Td>{new Date(b.created_at).toLocaleString()}</Td><Td>{b.kind.replace('_', ' ')}</Td><Td className="max-w-[220px] truncate">{b.filename}</Td>
              <Td>{b.uploaded_by}</Td><Td className="tabular">{b.rows_ok}/{b.rows_total}</Td><Td className={cx('tabular', b.rows_error > 0 && 'text-roof-600')}>{b.rows_error}</Td></tr>
          ))}
        </Table>
      </Card>
    </>
  )
}
