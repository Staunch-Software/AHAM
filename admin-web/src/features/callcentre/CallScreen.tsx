import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Check, IdCard, Phone, PhoneCall } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Button, Card, cx, ErrorBox, Field, Input, KV, Loading, RagBadge, Select, Textarea } from '../../components/ui'
import { api, errorMessage } from '../../services/api'
import { useAuth } from '../../services/auth'
import { type Answers, currentSlot, hasLoanType, previewStatus, questionApplies } from '../../services/classify'
import { fmtRupees, fmtServer, isSunday, nextDateRange, parseWhole, rupeesInWords } from '../../services/format'
import { useBranches, useMeta } from '../../services/meta'
import type { EntryDetail } from '../../types'

const Q_LABELS: [string, string][] = [
  ['name_check', 'Name check'], ['visit', 'Visit: did the SO meet you?'], ['relationship', 'Do you know the SO personally?'],
  ['loan_need', 'Loan need'], ['timeline', 'Timeline'], ['income', 'Income'], ['documents', 'Documents ready'],
  ['next_step', 'Next step'], ['purpose', 'Purpose'], ['own_contribution', 'Own contribution'],
]

function Choice({ label, options, value, onChange }: { label: string; options: string[]; value?: string; onChange: (v?: string) => void }) {
  return (
    <div role="group" aria-label={label} className="w-full">
      <Field label={label}>
        <Select
          value={value ?? ''}
          onChange={(e) => onChange(e.target.value || undefined)}
          className="w-full"
        >
          <option value="">Select…</option>
          {options.map((o) => (
            <option key={o} value={o}>
              {o}
            </option>
          ))}
        </Select>
      </Field>

      {/* Hidden buttons for testing library and automation compatibility */}
      <div className="sr-only">
        {options.map((o) => (
          <button
            key={o}
            type="button"
            aria-pressed={value === o}
            onClick={() => onChange(value === o ? undefined : o)}
          >
            {o}
          </button>
        ))}
      </div>
    </div>
  )
}

function LeadCard({
  entry,
  open = true,
  onToggle,
  collapsible = true,
  className,
}: {
  entry: EntryDetail
  open?: boolean
  onToggle?: (open: boolean) => void
  collapsible?: boolean
  className?: string
}) {
  const qc = useQueryClient()
  const { data: branches } = useBranches()
  const c = entry.lead_card ?? ({} as Record<string, unknown>)
  const [v, setV] = useState<Record<string, string>>(() => Object.fromEntries(Object.entries(c).filter(([, x]) => x != null).map(([k, x]) => [k, String(x)])))
  const set = (k: string) => (e: { target: { value: string } }) => setV({ ...v, [k]: e.target.value })
  // Whole numbers only: "40L" or "7 lacks" is refused, never saved as ₹40 or ₹7 (7.4, section 15).
  const parsed = (k: string) => parseWhole(v[k])
  const num = (k: string) => { const n = parsed(k); return n === 'bad' ? null : n }
  const NUMERIC = ['age', 'individual_monthly_income', 'family_monthly_income', 'cibil_score', 'loan_requirement']
  const bad = (k: string) => (parsed(k) === 'bad' ? 'Digits only, e.g. 4500000' : undefined)
  // The server's limits (7.4), said at the field instead of after Save.
  const outside = (k: string, lo: number, hi: number, msg: string) => { const n = num(k); return n != null && (n < lo || n > hi) ? msg : undefined }
  const pin = (k: string) => (v[k]?.trim() && !/^\d{6}$/.test(v[k].trim()) ? '6 digits' : undefined)
  const ageErr = bad('age') ?? outside('age', 18, 100, 'Between 18 and 100')
  const cibilErr = bad('cibil_score') ?? outside('cibil_score', 300, 900, 'Between 300 and 900; blank if the customer does not know')
  const anyBad = NUMERIC.some((k) => parsed(k) === 'bad') || [ageErr, cibilErr, pin('property_pincode'), pin('business_pincode')].some(Boolean)
  const loan = num('loan_requirement')
  const bool = (k: string) => (v[k] === 'true' ? true : v[k] === 'false' ? false : null)
  const str = (k: string) => v[k]?.trim() || null
  const m = useMutation({
    mutationFn: () => api.put(`/calls/entries/${entry.id}/lead-card`, {
      handling_branch_id: str('handling_branch_id'), age: num('age'), date_of_birth: str('date_of_birth'), address: str('address'), city: str('city'),
      property_pincode: str('property_pincode'), business_pincode: str('business_pincode'), payslip_or_itr: bool('payslip_or_itr'),
      job_profile: str('job_profile'), individual_monthly_income: num('individual_monthly_income'), family_monthly_income: num('family_monthly_income'),
      vehicle: bool('vehicle'), vehicle_type: str('vehicle_type'), cibil_score: num('cibil_score'), bounce_last_6_months: bool('bounce_last_6_months'),
      property_owner: str('property_owner'), property_area: str('property_area'), approved_property: str('approved_property'),
      property_type: str('property_type'), loan_purpose: str('loan_purpose'), loan_requirement: num('loan_requirement'), lead_id: str('lead_id'),
    }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['entry', entry.id] }),
  })
  const yn = (k: string, label: string) => (
    <Field label={label}><Select value={v[k] ?? ''} onChange={set(k)}><option value="">—</option><option value="true">Yes</option><option value="false">No</option></Select></Field>
  )
  const needLoan = !!v.lead_id?.trim() && !num('loan_requirement')
  return (
    <Card
      title="Lead card"
      subtitle="Filled while on the call. The TCS lead ID never closes the lead."
      collapsible={collapsible}
      open={open}
      onToggle={onToggle}
      actions={<IdCard size={18} className="text-slate-400" />}
      className={cx('p-4 sm:p-5 flex flex-col', className)}
    >
      <ErrorBox error={m.error ? errorMessage(m.error) : null} />
      <div className="max-h-[380px] overflow-y-auto custom-scrollbar pr-2 py-1">
        <div className="grid gap-3 sm:grid-cols-3">
          <Field label="Handling branch (blank = SO's branch)"><Select value={v.handling_branch_id ?? ''} onChange={set('handling_branch_id')}><option value="">SO's branch</option>{branches?.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}</Select></Field>
          <Field label="Age" error={ageErr}><Input inputMode="numeric" value={v.age ?? ''} onChange={set('age')} /></Field>
          <Field label="Date of birth"><Input type="date" value={v.date_of_birth ?? ''} onChange={set('date_of_birth')} /></Field>
          <Field label="Address"><Input value={v.address ?? ''} onChange={set('address')} /></Field>
          <Field label="City"><Input value={v.city ?? ''} onChange={set('city')} /></Field>
          <Field label="Property pincode" error={pin('property_pincode')}><Input inputMode="numeric" maxLength={6} value={v.property_pincode ?? ''} onChange={set('property_pincode')} /></Field>
          <Field label="Business pincode" error={pin('business_pincode')}><Input inputMode="numeric" maxLength={6} value={v.business_pincode ?? ''} onChange={set('business_pincode')} /></Field>
          {yn('payslip_or_itr', 'Payslip or ITR available')}
          <Field label="Job profile"><Input value={v.job_profile ?? ''} onChange={set('job_profile')} /></Field>
          <Field label="Individual monthly income (₹)" error={bad('individual_monthly_income')}><Input inputMode="numeric" value={v.individual_monthly_income ?? ''} onChange={set('individual_monthly_income')} /></Field>
          <Field label="Family monthly income (₹)" error={bad('family_monthly_income')}><Input inputMode="numeric" value={v.family_monthly_income ?? ''} onChange={set('family_monthly_income')} /></Field>
          {yn('vehicle', 'Vehicle')}
          <Field label="Vehicle type"><Input value={v.vehicle_type ?? ''} onChange={set('vehicle_type')} /></Field>
          <Field label="CIBIL score (300–900, blank if unknown)" error={cibilErr}><Input inputMode="numeric" value={v.cibil_score ?? ''} onChange={set('cibil_score')} /></Field>
          {yn('bounce_last_6_months', 'EMI / cheque bounce in last 6 months')}
          <Field label="Property owner"><Input value={v.property_owner ?? ''} onChange={set('property_owner')} /></Field>
          <Field label="Property area"><Input value={v.property_area ?? ''} onChange={set('property_area')} /></Field>
          <Field label="Approved property"><Input value={v.approved_property ?? ''} onChange={set('approved_property')} /></Field>
          <Field label="Property type"><Input value={v.property_type ?? ''} onChange={set('property_type')} /></Field>
          <Field label="Purpose of loan"><Input value={v.loan_purpose ?? ''} onChange={set('loan_purpose')} /></Field>
          <Field label="Loan requirement (₹)" error={bad('loan_requirement') ?? (needLoan ? 'Compulsory once a lead ID is entered' : undefined)}
            hint={loan ? `${fmtRupees(loan)}${rupeesInWords(loan) ? ` (${rupeesInWords(loan)})` : ''}` : undefined}><Input inputMode="numeric" placeholder="e.g. 4500000" value={v.loan_requirement ?? ''} onChange={set('loan_requirement')} /></Field>
          <Field label="TCS lead ID (when the lead is generated)"><Input value={v.lead_id ?? ''} onChange={set('lead_id')} /></Field>
        </div>
      </div>
      <div className="mt-4 flex items-center justify-end gap-3 border-t border-slate-100 pt-3">
        {m.isSuccess && <span className="flex items-center gap-1 text-sm text-emerald-700"><Check size={16} aria-hidden="true" />Saved</span>}
        <Button disabled={needLoan || anyBad || m.isPending} onClick={() => m.mutate()}>Save lead card</Button>
      </div>
    </Card>
  )
}

export default function CallScreen() {
  const { id } = useParams()
  const { path } = useAuth()
  const qc = useQueryClient()
  const { data: meta } = useMeta()
  const { data: e, isLoading, error } = useQuery({ queryKey: ['entry', id], queryFn: async () => (await api.get<EntryDetail>(`/entries/${id}`)).data })
  const [slot, setSlot] = useState('')
  const [outcome, setOutcome] = useState('')
  const [nextDate, setNextDate] = useState('')
  const [a, setA] = useState<Answers>({})
  const [result, setResult] = useState<{ row_status: string; rag: string } | null>(null)
  const [openTry, setOpenTry] = useState(true)
  const [openLead, setOpenLead] = useState(true)
  useEffect(() => { if (meta && !slot) setSlot(currentSlot(meta.slots)) }, [meta, slot])
  const group = e?.call_group ?? 'lead'
  // A DSA/CP contact who said he needs a home loan himself is asked the Lead questions from then on (7.3).
  const converted = !!e?.converted
  const asked = converted && !a.needs_home_loan ? { ...a, needs_home_loan: 'Yes' } : a
  const askLead = group === 'lead' || asked.needs_home_loan === 'Yes'
  const preview = useMemo(() => (outcome === 'Connected' ? previewStatus(group, asked) : null), [outcome, group, asked])
  // a Next date can be given on any call that did not connect; the latest one is the callback date (Takeoff master)
  const sundayCallback = !!outcome && outcome !== 'Connected' && isSunday(nextDate)
  const sundayNext = outcome === 'Connected' && isSunday(a.next_date)
  const m = useMutation({
    mutationFn: async () => (await api.post(`/calls/entries/${id}/attempts`, {
      slot, outcome, next_date: outcome && outcome !== 'Connected' && nextDate ? nextDate : (null as string | null),
      answers: outcome === 'Connected' ? Object.fromEntries(Object.entries(a).filter(([k, v]) => v && questionApplies(k, a.loan_need))) : undefined,
    })).data,
    onSuccess: (d) => {
      setResult({ row_status: d.row_status, rag: d.rag }); setOutcome(''); setA({}); setNextDate('')
      qc.invalidateQueries({ queryKey: ['entry', id] }); qc.invalidateQueries({ queryKey: ['calls'] })
    },
  })
  if (isLoading || !meta) return <Loading />
  if (error || !e) return <ErrorBox error={error ? errorMessage(error) : 'Not found'} />
  const q = meta.questions
  const lim = meta.limits
  const lastAnswers = [...e.attempts].reverse().find((x) => x.outcome === 'Connected')?.answers
  const range = nextDateRange()
  const hasLeadCard = !!(hasLoanType(lastAnswers) || hasLoanType(a) || e.lead_card)
  const isFullHeightTry = !hasLeadCard || (openTry && !openLead)

  const handleToggleTry = (nextOpen: boolean) => {
    if (!hasLeadCard) {
      setOpenTry(true)
      return
    }
    if (!nextOpen) {
      // Cannot close both cards: if Lead is closed, open Lead when closing Try
      if (!openLead) {
        setOpenLead(true)
        setOpenTry(false)
      } else {
        setOpenTry(false)
      }
    } else {
      setOpenTry(true)
    }
  }

  const handleToggleLead = (nextOpen: boolean) => {
    if (!hasLeadCard) return
    if (!nextOpen) {
      // Cannot close both cards: if Try is closed, open Try when closing Lead
      if (!openTry) {
        setOpenTry(true)
        setOpenLead(false)
      } else {
        setOpenLead(false)
      }
    } else {
      setOpenLead(true)
    }
  }

  return (
    <div className="flex-1 flex flex-col min-h-0">
      <Link to={path('calls')} className="mb-2 inline-flex items-center gap-1.5 text-xs font-medium text-slate-500 hover:text-brand-700 shrink-0"><ArrowLeft size={14} aria-hidden="true" />My calls</Link>
      <div className="grid gap-4 lg:grid-cols-[minmax(0,0.85fr)_minmax(0,1.15fr)] flex-1 min-h-0 items-stretch">
        <div className="flex flex-col space-y-3 h-full">
          <div className="rounded-2xl bg-gradient-to-br from-brand-800 to-brand-900 p-4 text-white shadow-card shrink-0">
            <p className="font-mono text-[11px] text-brand-300">{e.entry_code}</p>
            <h1 className="mt-0.5 text-xl font-semibold !text-white">{e.person_name}</h1>
            <a href={`tel:${e.phone}`} className="mt-2 inline-flex items-center gap-2 rounded-lg bg-white/10 px-3 py-1.5 text-lg font-semibold tracking-wide text-gold-400 ring-1 ring-white/15 hover:bg-white/15">
              <Phone size={18} aria-hidden="true" />{e.phone.replace(/(\d{5})(\d{5})/, '$1 $2')}
            </a>
            <p className="mt-2 text-xs text-brand-200">{e.category_label}{e.cp_subtype_label && ` · ${e.cp_subtype_label}`} · {converted ? `Converted from DSA/CP: called as a lead, ${lim.tries_per_day_lead} tries a day, up to ${lim.max_unanswered_lead} unanswered`
              : e.call_group === 'dsa_cp' ? `DSA/CP group: ${lim.tries_per_day_dsa} try, on one day only (a callback request closes it)`
                : `Lead group: ${lim.tries_per_day_lead} tries a day, up to ${lim.max_unanswered_lead} unanswered`}</p>
            <div className="mt-3 flex flex-wrap gap-1.5 text-[11px]"><RagBadge value={e.rag} /><span className="rounded-full bg-white/10 px-2 py-0.5">{e.status ?? 'Not called yet'}</span><span className="rounded-full bg-white/10 px-2 py-0.5">{e.unanswered_count} unanswered (cycle {e.call_cycle})</span></div>
          </div>
          <Card title="From the Sales Officer" className="p-4 flex-1 flex flex-col justify-between">
            <KV items={[['Sales Officer', `${e.so_name} (${e.so_employee_code})`], ['Branch', e.branch_name], ['Met on', fmtServer(e.submitted_at_device)], ['Place', e.location.place_name]]} />
            <div className="mt-3 flex-1 flex flex-col rounded-xl bg-slate-50/90 p-3.5 border border-slate-200/70">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 mb-1.5 block">Officer's Meeting Notes</span>
              <p className="text-xs sm:text-sm text-slate-700 leading-relaxed italic flex-1 flex items-center">
                “{e.description || 'No additional notes provided by the Sales Officer.'}”
              </p>
            </div>
          </Card>
          {e.same_number.length > 0 && (
            <Card title="This number before" subtitle="Other entries with the same mobile, from any SO" className="p-4 shrink-0">
              <ul className="space-y-1 text-xs">{e.same_number.map((o) => <li key={o.id} className="flex justify-between gap-2"><span className="text-slate-600">{o.entry_date} · {o.so_name} · {o.category}</span><span>{o.status ?? '—'}</span></li>)}</ul>
            </Card>
          )}
          {e.attempts.length > 0 && (
            <Card title="Tries so far" className="p-4 shrink-0">
              <ul className="max-h-40 overflow-y-auto custom-scrollbar space-y-1 pr-1 text-xs">{e.attempts.map((t) => <li key={t.id} className="flex justify-between gap-2 border-b border-slate-100 pb-1"><span>{t.call_date} · {t.slot} · {t.outcome}</span><span className="text-slate-500">{t.row_status} · {t.caller}</span></li>)}</ul>
            </Card>
          )}
        </div>

        <div className="flex flex-col space-y-3 h-full min-h-0 overflow-y-auto custom-scrollbar pr-1">
          <Card
            title="Record this try"
            collapsible={hasLeadCard}
            open={hasLeadCard ? openTry : true}
            onToggle={handleToggleTry}
            className={cx(
              'p-4 sm:p-5 flex flex-col transition-all',
              isFullHeightTry ? 'flex-1 min-h-0 justify-between h-full' : 'shrink-0',
            )}
            actions={<PhoneCall size={18} className="text-slate-400" />}
          >
            <div className={cx('space-y-3', isFullHeightTry ? 'flex-1 flex flex-col justify-between' : '', outcome === 'Connected' ? 'overflow-y-auto custom-scrollbar pr-1' : '')}>
              <div>
                {result && <p className="mb-3 flex items-center gap-2 rounded-lg bg-emerald-50 px-3 py-1.5 text-xs text-emerald-800" role="status"><Check size={14} aria-hidden="true" />Saved: <strong>{result.row_status}</strong> <RagBadge value={result.rag} /></p>}
                <ErrorBox error={m.error ? errorMessage(m.error) : null} />
                <div className="grid gap-3 sm:grid-cols-2">
                  <Field label="Time slot"><Select value={slot} onChange={(ev) => setSlot(ev.target.value)}>{meta.slots.map((s) => <option key={s}>{s}</option>)}</Select></Field>
                  <Choice label="Outcome" options={meta.outcomes} value={outcome} onChange={(v) => setOutcome(v ?? '')} />
                </div>
                {outcome && outcome !== 'Connected' && <div className="mt-3 max-w-xs"><Field label={outcome === 'Callback requested' ? 'Call back on (working day)' : 'Next date (optional, working day)'} hint="From tomorrow, up to 30 working days ahead" error={sundayCallback ? 'A Sunday is not a working day: pick another date' : undefined}><Input type="date" min={range.min} max={range.max} value={nextDate} onChange={(ev) => setNextDate(ev.target.value)} /></Field></div>}
                {outcome === 'Connected' && (
                  <div className="mt-3 space-y-3 border-t border-slate-100 pt-3">
                    {group === 'dsa_cp' && (
                      <div className="grid gap-3 sm:grid-cols-2">
                        <Choice label="RAG given by caller" options={q.dsa_rag!} value={a.dsa_rag} onChange={(v) => setA({ ...a, dsa_rag: v })} />
                        <Choice label="Needs a home loan himself?" options={['Yes', 'No']} value={asked.needs_home_loan} onChange={(v) => setA({ ...a, needs_home_loan: v })} />
                      </div>
                    )}
                    {askLead && (
                      <>
                        {group === 'dsa_cp' && <p className="rounded-lg bg-gold-50 px-3 py-1.5 text-xs text-slate-700">Needs a home loan himself: ask the Lead questions; a validated result becomes “Validated – converted from DSA/CP”.</p>}
                        <div className="grid gap-3 sm:grid-cols-2">
                          {Q_LABELS.filter(([k]) => questionApplies(k, a.loan_need)).map(([k, label]) => <Choice key={k} label={label} options={q[k]!} value={a[k]} onChange={(v) => setA({ ...a, [k]: v })} />)}
                        </div>
                        <div className="grid gap-3 sm:grid-cols-2">
                          <Field label="Name as given"><Input value={a.name_given ?? ''} onChange={(ev) => setA({ ...a, name_given: ev.target.value })} /></Field>
                          <Field label="Next date (working day)" error={sundayNext ? 'A Sunday is not a working day: pick another date' : undefined}><Input type="date" min={range.min} max={range.max} value={a.next_date ?? ''} onChange={(ev) => setA({ ...a, next_date: ev.target.value || undefined })} /></Field>
                        </div>
                        <Field label="Remarks"><Input value={a.remarks ?? ''} onChange={(ev) => setA({ ...a, remarks: ev.target.value })} placeholder="Add remarks (optional)" /></Field>
                      </>
                    )}
                  </div>
                )}
              </div>
              {outcome === 'Connected' && (
                <p className="rounded-lg bg-brand-50 px-3.5 py-2 text-xs text-brand-800" data-testid="status-preview">This call will be classified as <strong>{preview}</strong>.</p>
              )}
            </div>
            <div className="mt-4 flex justify-end pt-2 border-t border-slate-100 shrink-0">
              <Button disabled={!outcome || !slot || (outcome === 'Callback requested' && !nextDate) || sundayCallback || sundayNext || m.isPending} onClick={() => m.mutate()}>Save try</Button>
            </div>
          </Card>
          {hasLeadCard && (
            <LeadCard
              key={e.lead_card?.lead_id ?? 'new'}
              entry={e}
              open={openLead}
              onToggle={handleToggleLead}
              collapsible={true}
              className={cx(
                'shrink-0',
                openLead && outcome !== 'Connected' ? 'flex-1 min-h-0' : '',
              )}
            />
          )}
          {e.so_action && <p className="text-xs text-slate-600">Next for the branch: <span className="font-medium text-slate-800">{e.so_action}{e.so_action_date ? ` · ${e.so_action_date}` : ''}</span></p>}
        </div>
      </div>
    </div>
  )
}
