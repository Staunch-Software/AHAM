import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Languages } from 'lucide-react'
import { useState } from 'react'
import { Card, cx, EmptyState, ErrorBox, Input, Note, PageTitle, Select, Skeleton, Table, Td } from '../../components/ui'
import { api, errorMessage } from '../../services/api'

interface CallerRow {
  id: string; name: string; employee_code: string; active: boolean; absent: boolean; languages: string[]
  usual_branches: string[]; today_branches: string[]; load: number; room: number; calls_made: number
}
interface BranchRow { branch_id: string; branch: string; region: string | null; languages: string[]; usual_caller_id: string | null; usual_caller: string | null }
interface CallersPage { day: string; limit: number; languages: string[]; callers: CallerRow[]; branches: BranchRow[] }

const isoToday = () => new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 10)
const speaks = (caller: string[], branch: string[]) => !branch.length || caller.some((l) => branch.includes(l))

/** Language chips: each one switches that language on or off for the row. */
function Chips({ all, on, label, onChange, disabled }: { all: string[]; on: string[]; label: string; onChange: (v: string[]) => void; disabled?: boolean }) {
  return (
    <div role="group" aria-label={label} className="flex flex-wrap gap-1">
      {all.map((l) => {
        const active = on.includes(l)
        return (
          <button key={l} type="button" aria-pressed={active} disabled={disabled}
            onClick={() => onChange(active ? on.filter((x) => x !== l) : [...on, l])}
            className={cx('rounded-full border px-2 py-0.5 text-[11px] font-semibold transition disabled:opacity-50',
              active ? 'border-brand-600 bg-brand-600 text-white' : 'border-slate-200 bg-white text-slate-500 hover:border-brand-300 hover:text-brand-700')}>
            {l}
          </button>
        )
      })}
    </div>
  )
}

/** Who the call centre has: the languages each caller speaks, the languages of each branch and its usual caller, and
 *  who is absent. Auto-assign on Daily run & allocation works from these; the daily limit is in Settings. */
export default function Callers() {
  const qc = useQueryClient()
  const [day, setDay] = useState(isoToday())
  const { data, isLoading, error } = useQuery({
    queryKey: ['calls', 'callers', day],
    queryFn: async () => (await api.get<CallersPage>('/calls/callers', { params: { day } })).data,
  })
  const refresh = () => qc.invalidateQueries({ queryKey: ['calls'] })
  const langs = useMutation({ mutationFn: ({ id, languages }: { id: string; languages: string[] }) => api.patch(`/calls/callers/${id}`, { languages }), onSuccess: refresh })
  const absence = useMutation({ mutationFn: ({ id, absent }: { id: string; absent: boolean }) => api.put(`/calls/callers/${id}/absence`, { day, absent }), onSuccess: refresh })
  const branch = useMutation({ mutationFn: ({ id, body }: { id: string; body: { languages?: string[]; usual_caller_id?: string | null } }) => api.put(`/calls/branches/${id}`, body), onSuccess: refresh })
  const err = [error, langs.error, absence.error, branch.error].map((e) => e && errorMessage(e)).find(Boolean) ?? null
  const callers = data?.callers ?? []
  const active = callers.filter((c) => c.active)
  return (
    <>
      <PageTitle subtitle="The languages each caller speaks and each branch needs, the usual caller of each branch, and who is absent. Auto-assign on Daily run & allocation works from these."
        actions={<Input type="date" aria-label="Day" value={day} onChange={(e) => setDay(e.target.value)} className="w-auto" />}>
        Callers
      </PageTitle>
      <ErrorBox error={err} />
      {isLoading ? <Skeleton className="h-64" /> : (
        <>
          <Card flush title="Callers" subtitle={`Absent and the list are for ${day}. The list counts new entries, retries, PRIORITY and follow-ups against the daily limit of ${data?.limit ?? '—'} (Settings).`}>
            {!callers.length ? <EmptyState icon={<Languages size={20} />} title="No callers yet. HR adds them under Users & roles." /> : (
              <Table head={['Caller', 'Languages', 'Usual branches', `On ${day}`, 'List / limit', 'Calls made']} exportName={`Callers ${day}`}
                exportHeader={['Caller', 'Emp ID', 'Languages', 'Usual branches', 'Absent', 'List', 'Limit', 'Calls made']}
                exportAll={async () => callers.map((c) => [c.name, c.employee_code, c.languages.join(', '), c.usual_branches.join(', '), c.absent ? 'Yes' : 'No', c.load, data!.limit, c.calls_made])}>
                {callers.map((c) => (
                  <tr key={c.id} className={cx(!c.active && 'opacity-60')}>
                    <Td><p className="font-medium text-slate-800">{c.name}</p><p className="text-xs text-slate-400">{c.employee_code}{!c.active && ' · inactive'}</p></Td>
                    <Td>
                      <Chips all={data!.languages} on={c.languages} label={`Languages of ${c.name}`} disabled={langs.isPending}
                        onChange={(v) => langs.mutate({ id: c.id, languages: v })} />
                      {!c.languages.length && c.active && <p className="mt-1 text-[11px] text-gold-800">Set languages: not used by auto-assign</p>}
                    </Td>
                    <Td className="max-w-[260px] text-xs text-slate-600">{c.usual_branches.length ? c.usual_branches.join(', ') : <span className="text-slate-400">none</span>}</Td>
                    <Td>
                      {c.active && (
                        <button type="button" aria-pressed={c.absent} aria-label={`${c.name} absent on ${day}`} disabled={absence.isPending}
                          onClick={() => absence.mutate({ id: c.id, absent: !c.absent })}
                          className={cx('rounded-full border px-2.5 py-0.5 text-xs font-semibold',
                            c.absent ? 'border-roof-300 bg-roof-50 text-roof-700' : 'border-emerald-200 bg-emerald-50 text-emerald-700')}>
                          {c.absent ? 'Absent' : 'Present'}
                        </button>
                      )}
                    </Td>
                    <Td className={cx('tabular', c.room < 0 && 'font-semibold text-roof-700')}>{c.load} / {data!.limit}{c.room < 0 && ` (over by ${-c.room})`}</Td>
                    <Td className="tabular">{c.calls_made}</Td>
                  </tr>
                ))}
              </Table>
            )}
          </Card>

          <Card flush className="mt-6" title="Branches" subtitle="A caller can take a branch when they speak one of its languages. The usual caller takes it each day unless absent.">
            <Table head={['Region', 'Branch', 'Languages', 'Usual caller']} exportName="Branch languages and usual callers"
              exportHeader={['Region', 'Branch', 'Languages', 'Usual caller']}
              exportAll={async () => (data?.branches ?? []).map((b) => [b.region ?? '', b.branch, b.languages.join(', '), b.usual_caller ?? ''])}>
              {(data?.branches ?? []).map((b) => {
                const usual = callers.find((c) => c.id === b.usual_caller_id)
                const wrong = usual && usual.languages.length > 0 && !speaks(usual.languages, b.languages)
                // callers who speak the branch's language first
                const order = [...active].sort((x, y) => Number(speaks(y.languages, b.languages)) - Number(speaks(x.languages, b.languages)) || x.name.localeCompare(y.name))
                return (
                  <tr key={b.branch_id}>
                    <Td className="text-xs text-slate-500">{b.region}</Td>
                    <Td className="font-medium">{b.branch}</Td>
                    <Td><Chips all={data!.languages} on={b.languages} label={`Languages of ${b.branch}`} disabled={branch.isPending}
                      onChange={(v) => branch.mutate({ id: b.branch_id, body: { languages: v } })} /></Td>
                    <Td>
                      <Select aria-label={`Usual caller for ${b.branch}`} className="w-48 py-1.5 text-xs" value={b.usual_caller_id ?? ''}
                        onChange={(e) => branch.mutate({ id: b.branch_id, body: { usual_caller_id: e.target.value || null } })}>
                        <option value="">None</option>
                        {order.map((c) => <option key={c.id} value={c.id}>{c.name}{c.languages.length ? ` (${c.languages.join(', ')})` : ''}</option>)}
                      </Select>
                      {wrong && <p className="mt-1 text-[11px] text-roof-700">{usual!.name} does not speak {b.languages.join(' / ')}</p>}
                    </Td>
                  </tr>
                )
              })}
            </Table>
          </Card>
          <Note>Mark a caller absent before the morning run: the run gives them no work, and Daily run & allocation flags their branches with a caller who speaks the language and has room.</Note>
        </>
      )}
    </>
  )
}
