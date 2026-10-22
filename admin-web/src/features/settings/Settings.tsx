import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ChevronDown, ChevronUp, Plus } from 'lucide-react'
import { useState } from 'react'
import { Badge, Button, Card, cx, ErrorBox, Field, Input, PageTitle, Skeleton, Toggle } from '../../components/ui'
import { api, errorMessage } from '../../services/api'
import type { PersonTypesPayload, ReviewReason } from '../../types'

/** New order after moving item `i` by `delta` (-1 up, +1 down). Returns null when it cannot move. */
export function moved<T>(items: T[], i: number, delta: number): T[] | null {
  const j = i + delta
  if (j < 0 || j >= items.length) return null
  const copy = [...items]
  ;[copy[i], copy[j]] = [copy[j], copy[i]]
  return copy
}

function MoveButtons({ index, count, onMove }: { index: number; count: number; onMove: (d: number) => void }) {
  return (
    <span className="inline-flex overflow-hidden rounded-lg ring-1 ring-inset ring-slate-300">
      <button type="button" aria-label="Move up" disabled={index === 0} onClick={() => onMove(-1)}
        className="grid h-8 w-8 place-items-center bg-white text-slate-600 hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-brand-500 disabled:cursor-not-allowed disabled:opacity-40"><ChevronUp size={16} aria-hidden="true" /></button>
      <button type="button" aria-label="Move down" disabled={index === count - 1} onClick={() => onMove(1)}
        className="grid h-8 w-8 place-items-center border-l border-slate-300 bg-white text-slate-600 hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-brand-500 disabled:cursor-not-allowed disabled:opacity-40"><ChevronDown size={16} aria-hidden="true" /></button>
    </span>
  )
}

const rowBase = 'flex flex-wrap items-center justify-between gap-3 px-4 py-3'

function PersonTypes() {
  const qc = useQueryClient()
  const [newLabel, setNewLabel] = useState('')
  const [editing, setEditing] = useState<{ id: string; label: string } | null>(null)
  const [error, setError] = useState<string | null>(null)
  const { data, isLoading } = useQuery({ queryKey: ['person-types'], queryFn: async () => (await api.get<PersonTypesPayload>('/person-types')).data })
  const done = (p: PersonTypesPayload) => { qc.setQueryData(['person-types'], p); setError(null) }
  const fail = (e: unknown) => setError(errorMessage(e))
  const add = useMutation({ mutationFn: async (label: string) => (await api.post<PersonTypesPayload>('/person-types', { label })).data, onSuccess: (p) => { done(p); setNewLabel('') }, onError: fail })
  const patch = useMutation({
    mutationFn: async (v: { id: string; label?: string; active?: boolean }) => (await api.patch<PersonTypesPayload>(`/person-types/${v.id}`, { label: v.label, active: v.active })).data,
    onSuccess: (p) => { done(p); setEditing(null) }, onError: fail,
  })
  const order = useMutation({ mutationFn: async (ids: string[]) => (await api.put<PersonTypesPayload>('/person-types/order', { ids })).data, onSuccess: done, onError: fail })
  const settings = useMutation({ mutationFn: async (v: { required?: boolean; allow_other?: boolean }) => (await api.patch<PersonTypesPayload>('/person-types/settings', v)).data, onSuccess: done, onError: fail })
  if (isLoading || !data) return <Skeleton className="mb-6 h-80" />
  const items = data.items
  return (
    <Card title="Type of person (dropdown options)" subtitle="The choices agents see when they record a meeting." className="mb-6">
      <p className="mb-4 text-sm text-slate-600">
        Agents choose from the <strong>active</strong> options. Changes reach their phones on the next sync; phones keep the last list they downloaded when offline.
        Renaming or deactivating an option never changes reports already submitted: they keep the name they were saved with.
      </p>
      <ErrorBox error={error} />
      <div className="mb-4 flex flex-wrap gap-x-8 gap-y-3 rounded-xl bg-slate-50 px-4 py-3">
        <Toggle label="Agents must choose a type" checked={data.settings.required} onChange={(v) => settings.mutate({ required: v })} />
        <Toggle label={'Allow "Other" with a custom value'} checked={data.settings.allow_other} onChange={(v) => settings.mutate({ allow_other: v })} />
      </div>
      <ul className="divide-y divide-slate-100 overflow-hidden rounded-xl border border-slate-200" aria-label="Person types">
        {items.map((t, i) => (
          <li key={t.id} className={cx(rowBase, !t.active && 'bg-slate-50/70')}>
            <div className="flex min-w-0 flex-1 items-center gap-3">
              <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-brand-50 text-xs font-semibold text-brand-700" aria-hidden="true">{i + 1}</span>
              {editing?.id === t.id ? (
                <form className="flex flex-1 flex-wrap gap-2" onSubmit={(e) => { e.preventDefault(); patch.mutate({ id: t.id, label: editing.label }) }}>
                  <Input aria-label="New name" className="max-w-xs flex-1" value={editing.label} maxLength={100} autoFocus onChange={(e) => setEditing({ id: t.id, label: e.target.value })} />
                  <Button type="submit" small disabled={patch.isPending || !editing.label.trim()}>Save</Button>
                  <Button type="button" variant="secondary" small onClick={() => setEditing(null)}>Cancel</Button>
                </form>
              ) : (
                <div className="min-w-0">
                  <span className={t.active ? 'font-medium text-slate-900' : 'text-slate-400 line-through'}>{t.label}</span>{' '}
                  {!t.active && <Badge value="inactive" />}
                  <div className="text-xs text-slate-500">{t.times_used} meeting{t.times_used === 1 ? '' : 's'} so far</div>
                </div>
              )}
            </div>
            <div className="flex items-center gap-2">
              <MoveButtons index={i} count={items.length} onMove={(d) => { const m = moved(items, i, d); if (m) order.mutate(m.map((x) => x.id)) }} />
              <Button variant="secondary" small onClick={() => setEditing({ id: t.id, label: t.label })}>Rename</Button>
              <Button variant="secondary" small disabled={patch.isPending} onClick={() => patch.mutate({ id: t.id, active: !t.active })}>{t.active ? 'Deactivate' : 'Activate'}</Button>
            </div>
          </li>
        ))}
      </ul>
      <form className="mt-4 flex flex-wrap items-end gap-3 rounded-xl border border-dashed border-slate-300 p-4" onSubmit={(e) => { e.preventDefault(); if (newLabel.trim()) add.mutate(newLabel.trim()) }}>
        <div className="min-w-[14rem] flex-1 sm:max-w-sm"><Field label="Add a new type"><Input placeholder="e.g. Government Official" value={newLabel} maxLength={100} onChange={(e) => setNewLabel(e.target.value)} /></Field></div>
        <Button type="submit" disabled={add.isPending || !newLabel.trim()}><Plus size={16} aria-hidden="true" />Add type</Button>
      </form>
    </Card>
  )
}

function ReviewReasons() {
  const qc = useQueryClient()
  const [error, setError] = useState<string | null>(null)
  const [draft, setDraft] = useState({ label: '', message: '', requires: false })
  const [editing, setEditing] = useState<{ id: string; label: string; message: string } | null>(null)
  const { data, isLoading } = useQuery({ queryKey: ['review-reasons', 'all'], queryFn: async () => (await api.get<{ items: ReviewReason[] }>('/review-reasons')).data.items })
  const done = (r: { items: ReviewReason[] }) => { qc.setQueryData(['review-reasons', 'all'], r.items); qc.invalidateQueries({ queryKey: ['review-reasons', 'active'] }); setError(null) }
  const fail = (e: unknown) => setError(errorMessage(e))
  const add = useMutation({
    mutationFn: async () => (await api.post<{ items: ReviewReason[] }>('/review-reasons', { label: draft.label.trim(), default_message: draft.message.trim() || null, requires_comment: draft.requires })).data,
    onSuccess: (r) => { done(r); setDraft({ label: '', message: '', requires: false }) }, onError: fail,
  })
  const patch = useMutation({
    mutationFn: async (v: { id: string } & Partial<Pick<ReviewReason, 'label' | 'default_message' | 'requires_comment' | 'active'>>) => { const { id, ...b } = v; return (await api.patch<{ items: ReviewReason[] }>(`/review-reasons/${id}`, b)).data },
    onSuccess: (r) => { done(r); setEditing(null) }, onError: fail,
  })
  const order = useMutation({ mutationFn: async (ids: string[]) => (await api.put<{ items: ReviewReason[] }>('/review-reasons/order', { ids })).data, onSuccess: done, onError: fail })
  if (isLoading || !data) return <Skeleton className="h-80" />
  return (
    <Card title="Rejection reasons" subtitle="What reviewers can tell an agent when sending a report back.">
      <p className="mb-4 text-sm text-slate-600">
        Reviewers pick one of these when sending a report back. The message is pre-filled and can be edited. A missing GPS location
        is not a rejection reason unless your business process says so.
      </p>
      <ErrorBox error={error} />
      <ul className="divide-y divide-slate-100 overflow-hidden rounded-xl border border-slate-200" aria-label="Rejection reasons">
        {data.map((r, i) => (
          <li key={r.id} className={cx('px-4 py-3', !r.active && 'bg-slate-50/70')}>
            {editing?.id === r.id ? (
              <form className="grid gap-2 md:grid-cols-[1fr_2fr_auto]" onSubmit={(e) => { e.preventDefault(); patch.mutate({ id: r.id, label: editing.label, default_message: editing.message || null }) }}>
                <Input aria-label="Reason name" value={editing.label} maxLength={100} onChange={(e) => setEditing({ ...editing, label: e.target.value })} />
                <Input aria-label="Pre-filled message" value={editing.message} maxLength={500} onChange={(e) => setEditing({ ...editing, message: e.target.value })} />
                <div className="flex gap-2"><Button type="submit" small disabled={!editing.label.trim()}>Save</Button><Button type="button" variant="secondary" small onClick={() => setEditing(null)}>Cancel</Button></div>
              </form>
            ) : (
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex min-w-0 flex-1 items-start gap-3">
                  <span className="mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-full bg-gold-100 text-xs font-semibold text-gold-700" aria-hidden="true">{i + 1}</span>
                  <div className="min-w-0">
                    <span className={r.active ? 'font-medium text-slate-900' : 'text-slate-400 line-through'}>{r.label}</span> {!r.active && <Badge value="inactive" />}
                    {r.requires_comment && <span className="ml-2 rounded-md bg-slate-100 px-1.5 py-0.5 text-xs text-slate-600">comment required</span>}
                    <div className="text-xs text-slate-500">{r.default_message ?? 'No pre-filled message'}</div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <MoveButtons index={i} count={data.length} onMove={(d) => { const m = moved(data, i, d); if (m) order.mutate(m.map((x) => x.id)) }} />
                  <Button variant="secondary" small onClick={() => setEditing({ id: r.id, label: r.label, message: r.default_message ?? '' })}>Edit</Button>
                  <Button variant="secondary" small onClick={() => patch.mutate({ id: r.id, active: !r.active })}>{r.active ? 'Deactivate' : 'Activate'}</Button>
                </div>
              </div>
            )}
          </li>
        ))}
      </ul>
      <form className="mt-4 grid gap-3 rounded-xl border border-dashed border-slate-300 p-4 md:grid-cols-[1fr_2fr]" onSubmit={(e) => { e.preventDefault(); if (draft.label.trim()) add.mutate() }}>
        <Field label="New reason"><Input value={draft.label} maxLength={100} onChange={(e) => setDraft({ ...draft, label: e.target.value })} /></Field>
        <Field label="Pre-filled message (optional)"><Input value={draft.message} maxLength={500} onChange={(e) => setDraft({ ...draft, message: e.target.value })} /></Field>
        <div className="flex flex-wrap items-center gap-4 md:col-span-2">
          <label className="flex cursor-pointer items-center gap-2 text-sm text-slate-700"><input type="checkbox" className="h-4 w-4 rounded border-slate-300 accent-brand-700" checked={draft.requires} onChange={(e) => setDraft({ ...draft, requires: e.target.checked })} /> Needs a comment</label>
          <Button type="submit" disabled={add.isPending || !draft.label.trim()}><Plus size={16} aria-hidden="true" />Add reason</Button>
        </div>
      </form>
    </Card>
  )
}

export default function Settings() {
  return (
    <>
      <PageTitle subtitle="Manage the dropdown options and rejection reasons used by the field app and by reviewers.">Settings</PageTitle>
      <PersonTypes />
      <ReviewReasons />
    </>
  )
}
