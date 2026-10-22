import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CheckCircle2, Flag, History, Send, Undo2 } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Badge, Button, Card, Dialog, EmptyState, ErrorBox, Field, Select, Textarea } from '../../components/ui'
import { api, errorMessage } from '../../services/api'
import { fmtServer } from '../../services/format'
import type { ReviewReason, SubmissionDetail } from '../../types'

/** A report can be sent back only with a reason, and with a comment when that reason demands one. */
export function canReject(reason: ReviewReason | undefined, comment: string): boolean {
  return !!reason && (!reason.requires_comment || comment.trim().length > 0)
}

interface Props {
  d: SubmissionDetail
  flags: Record<string, string>
  onFlagsCleared: () => void
}

export function ReviewPanel({ d, flags, onFlagsCleared }: Props) {
  const qc = useQueryClient()
  const [reasonCode, setReasonCode] = useState('')
  const [comment, setComment] = useState('')
  const [touched, setTouched] = useState(false) // once the reviewer edits the text, stop overwriting it with the default
  const [reopen, setReopen] = useState<string | null>(null)
  const { data: reasons = [] } = useQuery({
    queryKey: ['review-reasons', 'active'],
    queryFn: async () => (await api.get<{ items: ReviewReason[] }>('/review-reasons')).data.items.filter((r) => r.active),
  })
  const reason = reasons.find((r) => r.code === reasonCode)
  const flagList = Object.entries(flags).map(([path, note]) => ({ path, note }))
  const refresh = () => qc.invalidateQueries({ queryKey: ['submissions'] })
  const decide = useMutation({
    mutationFn: (v: { decision: 'approved' | 'rejected' }) =>
      api.post(`/submissions/${d.id}/reviews`, { decision: v.decision, reason_code: v.decision === 'rejected' ? reasonCode : undefined,
        comment: v.decision === 'rejected' ? comment.trim() || undefined : undefined, flags: v.decision === 'rejected' ? flagList : [] }),
    onSuccess: () => { setReasonCode(''); setComment(''); setTouched(false); onFlagsCleared(); refresh() },
  })
  const reopenM = useMutation({
    mutationFn: (text: string) => api.post(`/submissions/${d.id}/reopen`, { comment: text }),
    onSuccess: () => { setReopen(null); refresh() },
  })
  const latest = d.revisions.find((r) => r.is_latest)

  return (
    <Card title="Review" actions={<Badge value={d.review_status} />}>
      <p className="mb-4 text-xs text-slate-500">Revision {d.revision} of {d.revisions.length}</p>

      {!d.is_latest ? (
        <p className="rounded-lg bg-slate-50 p-3 text-sm text-slate-600">
          This is an earlier version, kept for the history. {latest && <>The current version is <Link className="font-medium text-brand-700 underline" to={`/submissions/${latest.id}`}>revision {latest.revision}</Link>.</>}
        </p>
      ) : d.review_status === 'approved' ? (
        <div className="space-y-3">
          <p className="flex items-start gap-2 rounded-lg bg-emerald-50 p-3 text-sm text-emerald-800"><CheckCircle2 size={18} className="mt-0.5 shrink-0" aria-hidden="true" /><span>Approved. This version is final.</span></p>
          <Button variant="secondary" onClick={() => setReopen('')}><Undo2 size={16} aria-hidden="true" />Reopen for review…</Button>
        </div>
      ) : (
        <>
          {d.review_status === 'rejected' && (
            <p className="mb-4 rounded-lg border border-roof-200 bg-roof-50 p-3 text-sm text-roof-700" data-testid="sent-back">
              Sent back for correction{d.review_comment ? `: ${d.review_comment}` : '.'} Waiting for the agent's corrected version.
            </p>
          )}
          <div className="space-y-3">
            <Field label="Reason for sending back">
              <Select value={reasonCode} onChange={(e) => {
                setReasonCode(e.target.value)
                const r = reasons.find((x) => x.code === e.target.value)
                if (!touched) setComment(r?.default_message ?? '')
              }}>
                <option value="">Choose a reason…</option>
                {reasons.map((r) => <option key={r.code} value={r.code}>{r.label}</option>)}
              </Select>
            </Field>
            <Field label={`Message to the agent${reason?.requires_comment ? ' (required)' : ''}`}>
              <Textarea rows={3} maxLength={2000} value={comment} onChange={(e) => { setComment(e.target.value); setTouched(true) }} />
            </Field>
            <div className="rounded-lg bg-slate-50 p-3 text-sm">
              <div className="mb-1 flex items-center gap-1.5 text-xs font-semibold text-slate-700"><Flag size={13} aria-hidden="true" /><span>Flagged items ({flagList.length})</span></div>
              {flagList.length === 0 ? <p className="text-xs text-slate-500">Use "Flag" on a meeting or photo to point the agent at it.</p> : (
                <ul className="list-disc space-y-0.5 pl-5 text-xs text-slate-700">{flagList.map((f) => <li key={f.path}><span className="font-mono">{f.path}</span>: {f.note}</li>)}</ul>
              )}
            </div>
          </div>
          <ErrorBox error={decide.error ? errorMessage(decide.error) : null} />
          <div className="mt-4 grid grid-cols-2 gap-2">
            <Button variant="danger" disabled={decide.isPending || !canReject(reason, comment)} onClick={() => decide.mutate({ decision: 'rejected' })}>
              <Send size={15} aria-hidden="true" />Send back for correction
            </Button>
            <Button disabled={decide.isPending} onClick={() => decide.mutate({ decision: 'approved' })}><CheckCircle2 size={16} aria-hidden="true" />Approve</Button>
          </div>
        </>
      )}

      {reopen !== null && (
        <Dialog title="Reopen for review" onClose={() => setReopen(null)}>
          <p className="mb-3 text-sm text-slate-600">An approved report is final. Reopening is recorded in the history together with your reason.</p>
          <ErrorBox error={reopenM.error ? errorMessage(reopenM.error) : null} />
          <Textarea aria-label="Reason for reopening" rows={3} value={reopen} onChange={(e) => setReopen(e.target.value)} />
          <div className="mt-4 flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setReopen(null)}>Cancel</Button>
            <Button disabled={reopen.trim().length < 3 || reopenM.isPending} onClick={() => reopenM.mutate(reopen.trim())}>Reopen</Button>
          </div>
        </Dialog>
      )}
    </Card>
  )
}

export function ReviewHistory({ d }: { d: SubmissionDetail }) {
  return (
    <Card title="Review history" subtitle="Every decision on every version of this report">
      {d.reviews.length === 0 ? <EmptyState icon={<History size={20} />} title="No review decisions yet." /> : (
        <ol className="space-y-4">
          {d.reviews.map((r) => (
            <li key={r.id} className="rounded-xl border border-slate-200 p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="flex items-center gap-2"><Badge value={r.decision === 'reopened' ? 'reopened' : r.decision} /><span className="text-sm text-slate-500">Revision {r.revision}</span></span>
                <span className="text-xs text-slate-500">{fmtServer(r.created_at)}</span>
              </div>
              <p className="mt-2 text-sm text-slate-500">By <span className="font-medium text-slate-800">{r.reviewer}</span></p>
              {r.reason_label && <p className="mt-2 text-sm"><span className="rounded-md bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700">{r.reason_label}</span></p>}
              {r.comment && <p className="mt-2 text-sm text-slate-700">{r.comment}</p>}
              {r.flags.length > 0 && <p className="mt-2 text-xs text-slate-500">{r.flags.length} flagged item(s)</p>}
            </li>
          ))}
        </ol>
      )}
    </Card>
  )
}
