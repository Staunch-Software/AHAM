import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Button, Dialog, ErrorBox, Field, Input, Select, Textarea } from '../../components/ui'
import { api, errorMessage } from '../../services/api'
import { useMeta } from '../../services/meta'

/** 12.4: one code and one date per lead. A date more than 14 days out sends the lead to the call centre. */
export function AnswerDialog({ entryId, entryCode, onClose }: { entryId: string; entryCode: string; onClose: () => void }) {
  const qc = useQueryClient()
  const { data: meta } = useMeta()
  const [code, setCode] = useState('')
  const [date, setDate] = useState('')
  const [note, setNote] = useState('')
  const chosen = meta?.branch_codes.find((c) => c.code === code)
  const m = useMutation({
    mutationFn: () => api.post(`/branch/leads/${entryId}/answer`, { code, answer_date: chosen?.date_label ? date : null, note: note.trim() || null }),
    onSuccess: () => { ['branch-leads', 'entries', 'entry'].forEach((k) => qc.invalidateQueries({ queryKey: [k] })); onClose() },
  })
  const groups = [
    ['Closing', ['1', '2', '3']], ['Rejected', ['R1', 'R2', 'R3', 'R4', 'R5', 'R6']],
    ['Documents / login pending', ['A1', 'A2', 'A3', 'A4', 'A5', 'B', 'C1', 'C2', 'C3']], ['Waiting', ['D', 'E1', 'E2', 'F1', 'F2']],
  ] as const
  return (
    <Dialog title={`Answer lead ${entryCode}`} onClose={onClose}>
      <ErrorBox error={m.error ? errorMessage(m.error) : null} />
      <div className="space-y-4">
        <Field label="Code">
          <Select value={code} onChange={(e) => setCode(e.target.value)} autoFocus>
            <option value="">Choose a code…</option>
            {groups.map(([label, codes]) => (
              <optgroup key={label} label={label}>
                {codes.map((c) => { const d = meta?.branch_codes.find((x) => x.code === c); return <option key={c} value={c}>{c} · {d?.meaning}</option> })}
              </optgroup>
            ))}
          </Select>
        </Field>
        {chosen?.date_label && (
          <Field label={chosen.date_label}><Input type="date" value={date} onChange={(e) => setDate(e.target.value)} /></Field>
        )}
        {code === '1' && <p className="rounded-lg bg-sky-50 px-3 py-2 text-xs text-sky-800">The lead closes only when the login register shows the login.</p>}
        {(code === 'R2' || code === 'R3') && <p className="rounded-lg bg-gold-50 px-3 py-2 text-xs text-slate-700">For green-channel loans (small construction or purchase) head office checks this reject before it is accepted.</p>}
        {chosen?.date_label && meta && <p className="text-xs text-slate-500">A date within {meta.limits.branch_date_threshold_days} days keeps the lead with the branch; a later date sends it to the call centre for follow-up on that date.</p>}
        <Field label="Note (optional)"><Textarea rows={2} value={note} onChange={(e) => setNote(e.target.value)} /></Field>
      </div>
      <div className="mt-5 flex justify-end gap-2">
        <Button variant="secondary" onClick={onClose}>Cancel</Button>
        <Button disabled={!code || (!!chosen?.date_label && !date) || m.isPending} onClick={() => m.mutate()}>Save answer</Button>
      </div>
    </Dialog>
  )
}
