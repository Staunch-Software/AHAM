import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { BarChart2, Check, ChevronDown, Languages } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { Button, Card, cx, EmptyState, ErrorBox, Input, Note, PageTitle, Select, Skeleton, Table, Td } from '../../components/ui'
import { api, errorMessage } from '../../services/api'
import { CallerAnalyticsModal } from './CallerAnalyticsModal'

interface CallerRow {
  id: string; name: string; employee_code: string; active: boolean; absent: boolean; languages: string[]
  usual_branches: string[]; today_branches: string[]; load: number; room: number; calls_made: number
}
interface BranchRow { branch_id: string; branch: string; region: string | null; languages: string[]; usual_caller_id: string | null; usual_caller: string | null }
interface CallersPage { day: string; limit: number; languages: string[]; callers: CallerRow[]; branches: BranchRow[] }

const isoToday = () => new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 10)
const speaks = (caller: string[], branch: string[]) => !branch.length || caller.some((l) => branch.includes(l))

/** Modern executive multi-select language dropdown rendered via portal to prevent table clipping */
function LanguageDropdown({ all, on, label, onChange, disabled }: { all: string[]; on: string[]; label: string; onChange: (v: string[]) => void; disabled?: boolean }) {
  const [open, setOpen] = useState(false)
  const triggerRef = useRef<HTMLButtonElement>(null)
  const menuRef = useRef<HTMLDivElement>(null)
  const [coords, setCoords] = useState<{ top?: number; bottom?: number; left: number; width: number } | null>(null)

  useEffect(() => {
    if (!open) return

    const updatePosition = () => {
      if (!triggerRef.current) return
      const rect = triggerRef.current.getBoundingClientRect()
      const spaceBelow = window.innerHeight - rect.bottom
      const spaceAbove = rect.top
      const menuMaxHeight = 190
      const placeAbove = spaceBelow < menuMaxHeight && spaceAbove > spaceBelow
      const margin = 4
      const width = Math.max(rect.width, 224)

      let left = rect.left
      if (left + width > window.innerWidth - 8) {
        left = rect.right - width
      }
      if (left < 8) left = 8

      if (placeAbove) {
        setCoords({
          bottom: window.innerHeight - rect.top + margin,
          left,
          width,
        })
      } else {
        setCoords({
          top: rect.bottom + margin,
          left,
          width,
        })
      }
    }

    updatePosition()

    const handleScroll = (e: Event) => {
      if (menuRef.current && (menuRef.current === e.target || menuRef.current.contains(e.target as Node))) {
        return
      }
      setOpen(false)
    }

    window.addEventListener('resize', handleScroll)
    window.addEventListener('scroll', handleScroll, true)
    return () => {
      window.removeEventListener('resize', handleScroll)
      window.removeEventListener('scroll', handleScroll, true)
    }
  }, [open])

  useEffect(() => {
    if (!open) return
    const onMouseDown = (e: MouseEvent | TouchEvent) => {
      const target = e.target as Node
      if (triggerRef.current?.contains(target) || menuRef.current?.contains(target)) return
      setOpen(false)
    }
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', onMouseDown)
    document.addEventListener('touchstart', onMouseDown)
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('mousedown', onMouseDown)
      document.removeEventListener('touchstart', onMouseDown)
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [open])

  const toggle = (l: string) => {
    onChange(on.includes(l) ? on.filter((x) => x !== l) : [...on, l])
  }

  return (
    <div role="group" aria-label={label} className="relative inline-block w-52 text-left">
      <button
        ref={triggerRef}
        type="button"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={`Languages for ${label}`}
        disabled={disabled}
        onClick={() => setOpen((prev) => !prev)}
        className={cx(
          'flex min-h-[34px] w-full items-center justify-between gap-1.5 rounded-lg border bg-white px-2.5 py-1 text-xs shadow-sm transition hover:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-500/20 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:opacity-50',
          open ? 'border-brand-500 ring-2 ring-brand-500/20' : 'border-slate-300'
        )}
      >
        <div className="flex flex-1 flex-wrap items-center gap-1 overflow-hidden py-0.5">
          <Languages size={13} className="shrink-0 text-slate-400" />
          {!on.length ? (
            <span className="text-xs text-slate-400">Select languages...</span>
          ) : (
            <>
              {on.slice(0, 2).map((l) => (
                <span
                  key={l}
                  className="inline-flex items-center rounded border border-brand-200/80 bg-brand-50 px-1.5 py-0.5 text-[11px] font-medium text-brand-700"
                >
                  {l}
                </span>
              ))}
              {on.length > 2 && (
                <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[11px] font-semibold text-slate-600">
                  +{on.length - 2}
                </span>
              )}
            </>
          )}
        </div>
        <ChevronDown
          size={14}
          className={cx('shrink-0 text-slate-400 transition-transform duration-150', open && 'rotate-180 text-brand-600')}
        />
      </button>

      {open && coords && createPortal(
        <div
          ref={menuRef}
          style={{
            position: 'fixed',
            top: coords.top !== undefined ? `${coords.top}px` : undefined,
            bottom: coords.bottom !== undefined ? `${coords.bottom}px` : undefined,
            left: `${coords.left}px`,
            width: `${coords.width}px`,
            zIndex: 9999,
          }}
          className="rounded-xl border border-slate-200 bg-white p-1.5 shadow-2xl ring-1 ring-black/5 animate-in fade-in zoom-in-95 duration-100"
        >
          <div className="flex items-center justify-between border-b border-slate-100 px-2 py-1.5 text-[11px]">
            <span className="font-semibold text-slate-500">
              Languages ({on.length}/{all.length})
            </span>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => onChange([...all])}
                className="font-medium text-brand-600 hover:text-brand-800 hover:underline"
              >
                All
              </button>
              <span className="text-slate-300">·</span>
              <button
                type="button"
                onClick={() => onChange([])}
                className="font-medium text-slate-500 hover:text-roof-600 hover:underline"
              >
                Clear
              </button>
            </div>
          </div>
          <div className="mt-1 max-h-[136px] space-y-0.5 overflow-y-auto overscroll-contain custom-scrollbar pr-1 py-0.5">
            {all.map((l) => {
              const active = on.includes(l)
              return (
                <button
                  key={l}
                  type="button"
                  aria-pressed={active}
                  onClick={() => toggle(l)}
                  className={cx(
                    'flex w-full items-center justify-between rounded-lg px-2 py-1.5 text-left text-xs transition',
                    active ? 'bg-brand-50/70 font-semibold text-brand-900' : 'font-medium text-slate-700 hover:bg-slate-50'
                  )}
                >
                  <span className="flex items-center gap-2">
                    <span
                      className={cx(
                        'flex h-3.5 w-3.5 shrink-0 items-center justify-center rounded border transition',
                        active ? 'border-brand-600 bg-brand-600 text-white' : 'border-slate-300 bg-white'
                      )}
                    >
                      {active && <Check size={10} strokeWidth={3} />}
                    </span>
                    <span>{l}</span>
                  </span>
                </button>
              )
            })}
          </div>
        </div>,
        document.body
      )}
    </div>
  )
}

/** Who the call centre has: the languages each caller speaks, the languages of each branch and its usual caller, and
 *  who is absent. Auto-assign on Daily run & allocation works from these; the daily limit is in Settings. */
export default function Callers() {
  const qc = useQueryClient()
  const [day, setDay] = useState(isoToday())
  const [selectedCaller, setSelectedCaller] = useState<{ id: string; name: string } | null>(null)
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
              <Table head={['Caller', 'Languages', 'Usual branches', `On ${day}`, 'List / limit', 'Calls made', 'Analytics']} exportName={`Callers ${day}`}
                exportHeader={['Caller', 'Emp ID', 'Languages', 'Usual branches', 'Absent', 'List', 'Limit', 'Calls made']}
                exportAll={async () => callers.map((c) => [c.name, c.employee_code, c.languages.join(', '), c.usual_branches.join(', '), c.absent ? 'Yes' : 'No', c.load, data!.limit, c.calls_made])}>
                {callers.map((c) => (
                  <tr key={c.id} className={cx(!c.active && 'opacity-60')}>
                    <Td><p className="font-medium text-slate-800">{c.name}</p><p className="text-xs text-slate-400">{c.employee_code}{!c.active && ' · inactive'}</p></Td>
                    <Td>
                      <LanguageDropdown all={data!.languages} on={c.languages} label={`Languages of ${c.name}`} disabled={langs.isPending}
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
                    <Td>
                      <Button
                        variant="ghost"
                        small
                        onClick={() => setSelectedCaller({ id: c.id, name: c.name })}
                        aria-label={`View analytics for ${c.name}`}
                      >
                        <BarChart2 size={14} /> Analytics
                      </Button>
                    </Td>
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
                    <Td><LanguageDropdown all={data!.languages} on={b.languages} label={`Languages of ${b.branch}`} disabled={branch.isPending}
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

      {selectedCaller && (
        <CallerAnalyticsModal
          callerId={selectedCaller.id}
          callerName={selectedCaller.name}
          onClose={() => setSelectedCaller(null)}
        />
      )}
    </>
  )
}
