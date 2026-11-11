import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Button, Dialog, ErrorBox, Field, Input, RAG_LABEL, Select, Textarea, Toggle } from '../../components/ui'
import { api, errorMessage } from '../../services/api'
import { useCallers, useMeta, useSalesOfficers } from '../../services/meta'
import type { EntryDetail, Tracker } from '../../types'

const useDone = (id: string, onClose: () => void) => {
  const qc = useQueryClient()
  return () => { qc.invalidateQueries({ queryKey: ['entry', id] }); qc.invalidateQueries({ queryKey: ['entries'] }); onClose() }
}

/** 13.2: the right number, given by the SO through the BM or RTM; the entry is called again with fresh tries. */
export function CorrectNumberDialog({ entry, onClose }: { entry: EntryDetail; onClose: () => void }) {
  const done = useDone(entry.id, onClose)
  const [phone, setPhone] = useState('')
  const m = useMutation({ mutationFn: () => api.post(`/entries/${entry.id}/correct-number`, { phone }), onSuccess: done })
  return (
    <Dialog title="Correct the customer number" onClose={onClose}>
      <p className="mb-4 text-sm text-slate-600">The Entry ID stays. The call centre calls the new number automatically, with a fresh count of tries. Allowed until {entry.so_action_until ?? '15 days after the entry'}.</p>
      <ErrorBox error={m.error ? errorMessage(m.error) : null} />
      <Field label={`Correct mobile number (now ${entry.phone})`}><Input inputMode="tel" autoFocus value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="10 digits, starting 6-9" /></Field>
      <div className="mt-5 flex justify-end gap-2"><Button variant="secondary" onClick={onClose}>Cancel</Button><Button disabled={!phone.trim() || m.isPending} onClick={() => m.mutate()}>Save number</Button></div>
    </Dialog>
  )
}

/** 13.1: the RTM (or the BM of a branch without a cluster) or the monitor confirms the right SO. */
export function CorrectSoDialog({ entry, onClose }: { entry: EntryDetail; onClose: () => void }) {
  const done = useDone(entry.id, onClose)
  const { data: sos } = useSalesOfficers()
  const [so, setSo] = useState('')
  const m = useMutation({ mutationFn: () => api.post(`/entries/${entry.id}/correct-so`, { so_user_id: so }), onSuccess: done })
  return (
    <Dialog title="Correct the Sales Officer" onClose={onClose}>
      <p className="mb-4 text-sm text-slate-600">The Entry ID ({entry.entry_code}) stays. The SO, and with it the branch and region, change; counts and credit follow the new SO.</p>
      <ErrorBox error={m.error ? errorMessage(m.error) : null} />
      <Field label="Right Sales Officer">
        <Select value={so} onChange={(e) => setSo(e.target.value)}>
          <option value="">Choose…</option>
          {sos?.filter((u) => u.id !== entry.so_user_id).map((u) => <option key={u.id} value={u.id}>{u.full_name} · {u.employee_code}</option>)}
        </Select>
      </Field>
      <div className="mt-5 flex justify-end gap-2"><Button variant="secondary" onClick={onClose}>Cancel</Button><Button disabled={!so || m.isPending} onClick={() => m.mutate()}>Move entry</Button></div>
    </Dialog>
  )
}

/** 13.3: the master owner's manual follow-up row (one per entry). */
export function TrackerDialog({ entry, onClose }: { entry: EntryDetail; onClose: () => void }) {
  const done = useDone(entry.id, onClose)
  const { data: meta } = useMeta()
  const { data: callers } = useCallers()
  const t: Partial<Tracker> = entry.tracker ?? {}
  const [v, setV] = useState({
    owner: t.owner ?? '', action_type: t.action_type ?? '', caller_id: t.caller_id ?? '', followup_date: t.followup_date ?? '',
    outcome: t.outcome ?? '', tcs_id: t.tcs_id ?? '', reject_reason: t.reject_reason ?? '', rag_override: t.rag_override ?? '',
    immediate_callback: t.immediate_callback ?? false, notes: t.notes ?? '',
  })
  const set = (k: keyof typeof v) => (e: { target: { value: string } }) => setV({ ...v, [k]: e.target.value })
  const nul = (s: string) => s.trim() || null
  // 11.1: a login counts only with its TCS ID; a rejection needs its reason
  const needTcs = v.outcome === 'Logged in' && !v.tcs_id.trim()
  const needReason = v.outcome === 'Rejected' && !v.reject_reason.trim()
  const m = useMutation({
    mutationFn: () => api.put(`/calls/entries/${entry.id}/tracker`, {
      owner: nul(v.owner), action_type: nul(v.action_type), caller_id: nul(v.caller_id), followup_date: nul(v.followup_date),
      outcome: nul(v.outcome), tcs_id: nul(v.tcs_id), reject_reason: nul(v.reject_reason), rag_override: nul(v.rag_override),
      immediate_callback: v.immediate_callback, notes: nul(v.notes),
    }),
    onSuccess: done,
  })
  return (
    <Dialog title="Follow-up tracker" onClose={onClose} wide>
      <p className="mb-4 text-sm text-slate-600">Where this row and a branch answer disagree, the later date applies. Owner decides whose list shows the entry: <strong>Branch</strong> gives the branch the action type on the follow-up date; <strong>Call centre</strong> puts a follow-up on the call centre's list; <strong>Done</strong> closes it. A TCS ID entered here counts as a login. The RAG override wins over the computed RAG.</p>
      <ErrorBox error={m.error ? errorMessage(m.error) : null} />
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Owner"><Select value={v.owner} onChange={set('owner')}><option value="">—</option>{meta?.tracker.owners.map((o) => <option key={o} value={o}>{o.replace('_', ' ')}</option>)}</Select></Field>
        <Field label="Action type (for the branch when Owner = Branch)"><Select value={v.action_type} onChange={set('action_type')}><option value="">—</option>{meta?.tracker.action_types?.map((o) => <option key={o}>{o}</option>)}</Select></Field>
        <Field label="Caller"><Select value={v.caller_id} onChange={set('caller_id')}><option value="">—</option>{callers?.map((c) => <option key={c.id} value={c.id}>{c.full_name}</option>)}</Select></Field>
        <Field label="Follow-up date"><Input type="date" value={v.followup_date} onChange={set('followup_date')} /></Field>
        <Field label="Outcome"><Select value={v.outcome} onChange={set('outcome')}><option value="">—</option>{meta?.tracker.outcomes.map((o) => <option key={o}>{o}</option>)}</Select></Field>
        <Field label="TCS ID (manual login)" error={needTcs ? 'Type the TCS ID: a login counts only with it' : undefined}><Input value={v.tcs_id} onChange={set('tcs_id')} /></Field>
        <Field label="Reject reason" error={needReason ? 'Give the reject reason' : undefined}><Select value={v.reject_reason} onChange={set('reject_reason')}><option value="">—</option>{meta?.tracker.reject_reasons?.map((o) => <option key={o}>{o}</option>)}</Select></Field>
        <Field label="RAG override"><Select value={v.rag_override} onChange={set('rag_override')}><option value="">None (computed)</option>{['GREEN', 'AMBER', 'RED', 'RNR', 'NA'].map((r) => <option key={r} value={r}>{RAG_LABEL[r]}</option>)}</Select></Field>
      </div>
      {v.outcome === 'Return to branch – green channel' && <p className="mt-3 rounded-lg bg-gold-50 px-3 py-2 text-xs text-slate-700">Returns the branch's green-channel R2/R3 rejection: the lead goes back to the branch to log in (the same as on the Green channel page).</p>}
      <div className="mt-4"><Toggle label="Immediate call-back (shown first, as PRIORITY)" checked={v.immediate_callback} onChange={(c) => setV({ ...v, immediate_callback: c })} /></div>
      <div className="mt-4"><Field label="Notes"><Textarea rows={3} value={v.notes} onChange={set('notes')} /></Field></div>
      <div className="mt-5 flex justify-end gap-2"><Button variant="secondary" onClick={onClose}>Cancel</Button><Button disabled={m.isPending || needTcs || needReason} onClick={() => m.mutate()}>Save</Button></div>
    </Dialog>
  )
}
