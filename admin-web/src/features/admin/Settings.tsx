import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowDown, ArrowUp, CalendarX, Check, Plus, Save, Trash2 } from 'lucide-react'
import { ReactNode, useEffect, useState } from 'react'
import { Button, Card, cx, ErrorBox, Input, Note, PageTitle, Select, Toggle } from '../../components/ui'
import { api, errorMessage } from '../../services/api'
import { useAuth } from '../../services/auth'
import { useRoles } from '../../services/meta'

type S = Record<string, any>
const NUMBERS: [string, string, string][] = [
  ['repeat_window_days', 'Repeat / spoken-to window', 'days'], ['max_unanswered_lead', 'Maximum unanswered tries (lead)', 'tries'],
  ['tries_per_day_lead', 'Tries per day (lead)', 'tries'], ['tries_per_day_dsa', 'Tries per day (DSA/CP)', 'tries'],
  ['max_slots_per_day', 'Attempts that may be recorded per day', 'slots'], ['first_attempt_target_days', 'First-attempt turnaround target', 'days'],
  ['action_window_days', 'Action list window (non-lead actions)', 'days'], ['correct_number_window_days', '“Correct customer number” window', 'days'],
  ['amber_correction_window_days', 'SO Amber correction window', 'days'], ['branch_date_threshold_days', 'Branch date threshold to the call centre', 'days'],
  ['daily_entry_target', 'Daily entry target per SO (all categories)', 'entries'], ['daily_lead_target', 'Of which Lead/Prospect', 'entries'],
  ['green_channel_construction_limit', 'Green channel: self construction / improvement up to', '₹'], ['green_channel_purchase_limit', 'Green channel: purchase / plot + construction up to', '₹'],
  ['clock_skew_minutes', 'Flag entries whose phone clock is ahead by more than', 'minutes'],
]

function SankalpSettings() {
  const qc = useQueryClient()
  const { data: roles } = useRoles()
  const { data } = useQuery({ queryKey: ['settings'], queryFn: async () => (await api.get<S>('/settings')).data })
  const [v, setV] = useState<S | null>(null)
  const [newDesig, setNewDesig] = useState({ d: '', r: 'sales_officer' })
  useEffect(() => { if (data) setV(data) }, [data])
  const m = useMutation({ mutationFn: async () => (await api.patch<S>('/settings', v)).data, onSuccess: (d) => { qc.setQueryData(['settings'], d); setV(d) } })
  if (!v) return null
  const set = (k: string, val: unknown) => setV({ ...v, [k]: val })
  const row = (label: string, control: ReactNode, hint?: string) => (
    <div key={label} className="grid items-center gap-2 border-b border-slate-100 py-3 sm:grid-cols-[minmax(0,1fr)_220px]">
      <div><p className="text-sm text-slate-800">{label}</p>{hint && <p className="text-xs text-slate-500">{hint}</p>}</div>{control}
    </div>
  )
  return (
    <Card title="Sankalp settings (section 14)" subtitle="Every window and target the rules use. Changes apply from the next event or daily run."
      actions={<div className="flex items-center gap-3">{m.isSuccess && <span className="flex items-center gap-1 text-xs text-emerald-700"><Check size={14} aria-hidden="true" />Saved</span>}
        <Button small disabled={m.isPending} onClick={() => m.mutate()}><Save size={14} aria-hidden="true" />Save settings</Button></div>}>
      <ErrorBox error={m.error ? errorMessage(m.error) : null} />
      {row('Takeoff start date', <Input type="date" value={v.takeoff_start} onChange={(e) => set('takeoff_start', e.target.value)} />)}
      {row('First entry date the call centre calls', <Input type="date" value={v.first_call_date} onChange={(e) => set('first_call_date', e.target.value)} />)}
      {NUMBERS.map(([k, label, unit]) => row(label, <label className="flex items-center gap-2"><Input type="number" min={0} value={v[k]} onChange={(e) => set(k, Number(e.target.value))} /><span className="w-14 text-xs text-slate-500">{unit}</span></label>))}
      {row('Attendance codes that count as present', <Input value={(v.present_codes as string[]).join(', ')} onChange={(e) => set('present_codes', e.target.value.split(',').map((x) => x.trim()).filter(Boolean))} />)}
      {row('Automatic daily run at', <Input type="time" value={v.auto_selection_time ?? ''} onChange={(e) => set('auto_selection_time', e.target.value || null)} />, 'Leave empty to run it only from the call-centre portal')}

      <h3 className="mt-6 text-xs font-semibold uppercase tracking-wider text-gold-700">Aham to decide</h3>
      <p className="mb-1 text-xs text-slate-500">Open points of the business logic. The defaults are today’s behaviour.</p>
      {row('Allow same-day calling', <Toggle label={v.same_day_calling ? 'On' : 'Off: called from the next day'} checked={v.same_day_calling} onChange={(c) => set('same_day_calling', c)} />)}
      {row('A TCS ID repeated in the login register', <Select value={v.duplicate_tcs_rule} onChange={(e) => set('duplicate_tcs_rule', e.target.value)}><option value="latest">The latest row wins</option><option value="first">The first row wins</option></Select>)}
      {row('A Sales Officer with no attendance row that day', <Select value={v.unmarked_attendance ?? 'present'} onChange={(e) => set('unmarked_attendance', e.target.value)}><option value="present">Counted as present (shown as not marked)</option><option value="absent">Counted as absent (AB)</option></Select>)}

      <h3 className="mt-6 text-xs font-semibold uppercase tracking-wider text-brand-600">Designation to role (roster upload)</h3>
      <div className="mt-2 grid gap-2 sm:grid-cols-2">
        {Object.entries(v.designation_roles as Record<string, string>).map(([d, r]) => (
          <div key={d} className="flex items-center gap-2 rounded-lg bg-slate-50 px-3 py-1.5 text-sm">
            <span className="w-36 truncate font-medium">{d}</span>
            <Select className="py-1 text-xs" value={r} onChange={(e) => set('designation_roles', { ...v.designation_roles, [d]: e.target.value })}>{roles?.roles.filter((x) => x.level > 0).map((x) => <option key={x.key} value={x.key}>{x.label}</option>)}</Select>
            <button type="button" aria-label={`Remove ${d}`} className="text-slate-400 hover:text-roof-600" onClick={() => { const n = { ...v.designation_roles }; delete n[d]; set('designation_roles', n) }}><Trash2 size={14} aria-hidden="true" /></button>
          </div>
        ))}
      </div>
      <div className="mt-2 flex gap-2">
        <Input className="max-w-[180px]" placeholder="New designation" value={newDesig.d} onChange={(e) => setNewDesig({ ...newDesig, d: e.target.value })} />
        <Select className="max-w-[220px]" value={newDesig.r} onChange={(e) => setNewDesig({ ...newDesig, r: e.target.value })}>{roles?.roles.filter((x) => x.level > 0).map((x) => <option key={x.key} value={x.key}>{x.label}</option>)}</Select>
        <Button variant="secondary" disabled={!newDesig.d.trim()} onClick={() => { set('designation_roles', { ...v.designation_roles, [newDesig.d.trim().toUpperCase()]: newDesig.r }); setNewDesig({ d: '', r: 'sales_officer' }) }}><Plus size={14} aria-hidden="true" />Add</Button>
      </div>
    </Card>
  )
}

function Holidays() {
  const qc = useQueryClient()
  const year = new Date().getFullYear()
  const { data } = useQuery({ queryKey: ['holidays'], queryFn: async () => (await api.get<{ id: string; day: string; name: string }[]>('/holidays')).data })
  const [v, setV] = useState({ day: '', name: '' })
  const add = useMutation({ mutationFn: () => api.post('/holidays', v), onSuccess: () => { setV({ day: '', name: '' }); qc.invalidateQueries({ queryKey: ['holidays'] }) } })
  const del = useMutation({ mutationFn: (id: string) => api.delete(`/holidays/${id}`), onSuccess: () => qc.invalidateQueries({ queryKey: ['holidays'] }) })
  return (
    <Card title="Holidays" subtitle="An entry made on a Sunday or a holiday counts on the next working day. The Entry ID keeps the real time.">
      <ErrorBox error={[add.error, del.error].map((e) => e && errorMessage(e)).find(Boolean) ?? null} />
      <div className="flex flex-wrap gap-2">
        <Input type="date" className="w-auto" value={v.day} onChange={(e) => setV({ ...v, day: e.target.value })} aria-label="Holiday date" />
        <Input className="max-w-xs" placeholder="Name, e.g. Diwali" value={v.name} onChange={(e) => setV({ ...v, name: e.target.value })} />
        <Button disabled={!v.day || !v.name.trim() || add.isPending} onClick={() => add.mutate()}><Plus size={14} aria-hidden="true" />Add holiday</Button>
      </div>
      <ul className="mt-4 divide-y divide-slate-100 text-sm">
        {data?.map((h) => (
          <li key={h.id} className={cx('flex items-center justify-between py-2', h.day < `${year}-01-01` && 'text-slate-400')}>
            <span><span className="tabular font-medium">{h.day}</span> · {h.name}</span>
            <Button small variant="ghost" aria-label={`Delete ${h.name}`} onClick={() => del.mutate(h.id)}><Trash2 size={14} aria-hidden="true" /></Button>
          </li>
        ))}
        {!data?.length && <li className="flex items-center gap-2 py-3 text-slate-500"><CalendarX size={16} aria-hidden="true" />No holidays yet.</li>}
      </ul>
    </Card>
  )
}

interface Sub { id: string; label: string; active: boolean; sort_order: number; times_used: number }
function CpSubtypes() {
  const qc = useQueryClient()
  const { data } = useQuery({ queryKey: ['cp-subtypes'], queryFn: async () => (await api.get<{ items: Sub[] }>('/cp-subtypes')).data.items })
  const [label, setLabel] = useState('')
  const [rename, setRename] = useState<Record<string, string>>({})
  const done = (d: { data: { items: Sub[] } }) => qc.setQueryData(['cp-subtypes'], d.data.items)
  const add = useMutation({ mutationFn: () => api.post('/cp-subtypes', { label }), onSuccess: (d) => { setLabel(''); done(d) } })
  const patch = useMutation({ mutationFn: ({ id, body }: { id: string; body: object }) => api.patch(`/cp-subtypes/${id}`, body), onSuccess: done })
  const order = useMutation({ mutationFn: (ids: string[]) => api.put('/cp-subtypes/order', { ids }), onSuccess: done })
  const move = (i: number, dir: -1 | 1) => { const ids = (data ?? []).map((s) => s.id); [ids[i], ids[i + dir]] = [ids[i + dir]!, ids[i]!]; order.mutate(ids) }
  return (
    <Card title="CP sub-types" subtitle="Asked only when Category = Contact Point. Entries keep the label they were saved with; retire an option instead of deleting it.">
      <ErrorBox error={[add.error, patch.error, order.error].map((e) => e && errorMessage(e)).find(Boolean) ?? null} />
      <ul className="divide-y divide-slate-100">
        {data?.map((s, i) => (
          <li key={s.id} className="flex flex-wrap items-center gap-2 py-2">
            <div className="flex flex-col">
              <button type="button" aria-label={`Move ${s.label} up`} disabled={i === 0} className="text-slate-400 hover:text-brand-700 disabled:opacity-30" onClick={() => move(i, -1)}><ArrowUp size={14} /></button>
              <button type="button" aria-label={`Move ${s.label} down`} disabled={i === (data?.length ?? 0) - 1} className="text-slate-400 hover:text-brand-700 disabled:opacity-30" onClick={() => move(i, 1)}><ArrowDown size={14} /></button>
            </div>
            <Input className={cx('max-w-xs flex-1', !s.active && 'text-slate-400 line-through')} value={rename[s.id] ?? s.label} onChange={(e) => setRename({ ...rename, [s.id]: e.target.value })}
              onBlur={() => rename[s.id] !== undefined && rename[s.id] !== s.label && patch.mutate({ id: s.id, body: { label: rename[s.id] } })} aria-label={`Name of ${s.label}`} />
            <span className="text-xs text-slate-500">{s.times_used} entries</span>
            <div className="ml-auto"><Toggle label={s.active ? 'Active' : 'Retired'} checked={s.active} onChange={(c) => patch.mutate({ id: s.id, body: { active: c } })} /></div>
          </li>
        ))}
      </ul>
      <div className="mt-3 flex gap-2">
        <Input className="max-w-xs" placeholder="New sub-type, e.g. Cement dealer" value={label} onChange={(e) => setLabel(e.target.value)} />
        <Button variant="secondary" disabled={!label.trim() || add.isPending} onClick={() => add.mutate()}><Plus size={14} aria-hidden="true" />Add</Button>
      </div>
    </Card>
  )
}

export default function Settings() {
  const { can } = useAuth()
  return (
    <>
      <PageTitle subtitle="Settings live in the database: no code change is needed to move a window or a target.">Settings</PageTitle>
      {!can('settings.manage') && <Note>Only the system admin changes the Sankalp settings.</Note>}
      <div className="space-y-6">
        {can('settings.manage') && <SankalpSettings />}
        <div className="grid gap-6 lg:grid-cols-2">
          {can('reference.import') && <Holidays />}
          {can('cp_subtypes.manage') && <CpSubtypes />}
        </div>
      </div>
    </>
  )
}
