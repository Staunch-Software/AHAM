import { useQuery } from '@tanstack/react-query'
import { SlidersHorizontal } from 'lucide-react'
import { Button, Field, Input, Select } from '../../components/ui'
import { api } from '../../services/api'
import type { Branch, Employee, Page, PersonTypesPayload } from '../../types'

export const FILTER_KEYS = ['date_from', 'date_to', 'branch_id', 'agent_id', 'form_id', 'status', 'review_status', 'has_location', 'person_type_id', 'latest_only', 'reference'] as const
type FilterKey = (typeof FILTER_KEYS)[number]

export function useLookups() {
  const branches = useQuery({ queryKey: ['branches'], queryFn: async () => (await api.get<Branch[]>('/branches')).data })
  const agents = useQuery({
    queryKey: ['employees', 'agents'],
    queryFn: async () => (await api.get<Page<Employee>>('/employees', { params: { role: 'agent', page_size: 100 } })).data.items,
  })
  const types = useQuery({ queryKey: ['person-types'], queryFn: async () => (await api.get<PersonTypesPayload>('/person-types')).data })
  return { branches: branches.data ?? [], agents: agents.data ?? [], personTypes: types.data?.items ?? [] }
}

interface Props {
  params: URLSearchParams
  onChange: (p: URLSearchParams) => void
  /** Extra controls rendered after the standard ones (for example map-only switches). */
  extra?: React.ReactNode
  showReference?: boolean
  /** Filters that the page offers in another form (for example review-status tabs). They still apply, they are just not repeated here. */
  hide?: FilterKey[]
}

export function Filters({ params, onChange, extra, showReference = true, hide = [] }: Props) {
  const { branches, agents, personTypes } = useLookups()
  const set = (k: string, v: string) => {
    const n = new URLSearchParams(params)
    v ? n.set(k, v) : n.delete(k)
    n.delete('page')
    onChange(n)
  }
  const g = (k: string) => params.get(k) ?? ''
  const active = FILTER_KEYS.filter((k) => params.get(k)).length
  const show = (k: FilterKey) => !hide.includes(k)
  return (
    <form className="mb-5 rounded-2xl border border-slate-200/80 bg-white p-4 shadow-card" onSubmit={(e) => e.preventDefault()} aria-label="Filters">
      <div className="mb-3 flex items-center justify-between gap-2">
        <span className="flex items-center gap-2 text-sm font-semibold text-brand-900">
          <SlidersHorizontal size={16} className="text-brand-600" aria-hidden="true" />Filters
          {active > 0 && <span className="rounded-full bg-brand-700 px-2 py-0.5 text-[11px] font-semibold text-white">{active} active</span>}
        </span>
        <Button type="button" variant="ghost" small disabled={active === 0} onClick={() => onChange(new URLSearchParams())}>Clear filters</Button>
      </div>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-4">
        <Field label="From"><Input type="date" value={g('date_from')} onChange={(e) => set('date_from', e.target.value)} /></Field>
        <Field label="To"><Input type="date" value={g('date_to')} onChange={(e) => set('date_to', e.target.value)} /></Field>
        <Field label="Branch">
          <Select value={g('branch_id')} onChange={(e) => set('branch_id', e.target.value)}>
            <option value="">All</option>{branches.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
          </Select>
        </Field>
        <Field label="Agent">
          <Select value={g('agent_id')} onChange={(e) => set('agent_id', e.target.value)}>
            <option value="">All</option>{agents.map((a) => <option key={a.id} value={a.id}>{a.full_name} ({a.employee_code})</option>)}
          </Select>
        </Field>
        <Field label="Form">
          <Select value={g('form_id')} onChange={(e) => set('form_id', e.target.value)}>
            <option value="">All</option><option value="field_meeting_report">Field Meeting Report</option>
          </Select>
        </Field>
        {show('review_status') && (
          <Field label="Review status">
            <Select value={g('review_status')} onChange={(e) => set('review_status', e.target.value)}>
              <option value="">All</option><option value="pending">Pending review</option><option value="approved">Approved</option><option value="rejected">Needs correction</option>
            </Select>
          </Field>
        )}
        <Field label="Type of person">
          <Select value={g('person_type_id')} onChange={(e) => set('person_type_id', e.target.value)}>
            <option value="">All</option>{personTypes.map((t) => <option key={t.id} value={t.id}>{t.label}{t.active ? '' : ' (inactive)'}</option>)}
          </Select>
        </Field>
        <Field label="Location">
          <Select value={g('has_location')} onChange={(e) => set('has_location', e.target.value)}>
            <option value="">Any</option><option value="true">Available</option><option value="false">Unavailable</option>
          </Select>
        </Field>
        {showReference && <Field label="Reference"><Input placeholder="FS-2026-0042" value={g('reference')} onChange={(e) => set('reference', e.target.value)} /></Field>}
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-x-6 gap-y-2 border-t border-slate-100 pt-3 text-sm text-slate-700">
        <label className="flex cursor-pointer items-center gap-2">
          <input type="checkbox" className="h-4 w-4 rounded border-slate-300 accent-brand-700" checked={g('latest_only') === 'false'} onChange={(e) => set('latest_only', e.target.checked ? 'false' : '')} />
          Include earlier versions
        </label>
        {extra}
      </div>
    </form>
  )
}

export const filterParams = (p: URLSearchParams) => Object.fromEntries(FILTER_KEYS.filter((k) => p.get(k)).map((k) => [k, p.get(k)!]))
