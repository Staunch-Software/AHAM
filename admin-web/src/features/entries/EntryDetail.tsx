import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, Camera, Flag, History, IdCard, MapPin, PhoneCall, TriangleAlert } from 'lucide-react'
import { ReactNode, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { Button, Card, ErrorBox, KV, Loading, RagBadge, StatusText, Table, Td } from '../../components/ui'
import { api, errorMessage } from '../../services/api'
import { useAuth } from '../../services/auth'
import { accuracyLabel, fmtDevice, fmtServer, mapUrl, validCoords } from '../../services/format'
import type { EntryDetail as Detail } from '../../types'
import { AnswerDialog } from '../branch/AnswerDialog'
import { CorrectNumberDialog, CorrectSoDialog, TrackerDialog } from './EntryDialogs'

const LEAD_ACTIONS = ['Visit customer', 'Collect documents', 'Follow up lead']
const yes = (b: boolean) => (b ? 'Yes' : 'No')
/** A history value: lead card changes come as {field: [old, new]}. */
const detailText = (v: unknown): string => {
  if (Array.isArray(v) && v.length === 2) return `${v[0] ?? '—'} → ${v[1] ?? '—'}`
  if (v && typeof v === 'object') return Object.entries(v).map(([k, x]) => `${k.replace(/_/g, ' ')} ${detailText(x)}`).join(', ')
  return String(v)
}

const ANSWER_LABELS: Record<string, string> = {
  dsa_rag: 'RAG given by caller', needs_home_loan: 'Needs a home loan himself', name_check: 'Name check', name_given: 'Name as given',
  visit: 'Did the SO meet you?', relationship: 'Knows the SO personally', loan_need: 'Loan need', timeline: 'Timeline', income: 'Income',
  documents: 'Documents ready', next_step: 'Next step', next_date: 'Next date', purpose: 'Purpose', own_contribution: 'Own contribution', remarks: 'Remarks',
}
const CARD_LABELS: Record<string, string> = {
  age: 'Age', date_of_birth: 'Date of birth', address: 'Address', city: 'City', property_pincode: 'Property pincode', business_pincode: 'Business pincode',
  payslip_or_itr: 'Payslip or ITR', job_profile: 'Job profile', individual_monthly_income: 'Individual monthly income (₹)',
  family_monthly_income: 'Family monthly income (₹)', vehicle: 'Vehicle', vehicle_type: 'Vehicle type', cibil_score: 'CIBIL score',
  bounce_last_6_months: 'EMI / cheque bounce (6 months)', property_owner: 'Property owner', property_area: 'Property area',
  approved_property: 'Approved property', property_type: 'Property type', loan_purpose: 'Purpose of loan',
}
const show = (v: unknown) => (v === true ? 'Yes' : v === false ? 'No' : v == null || v === '' ? '—' : typeof v === 'number' ? v.toLocaleString('en-IN') : String(v))

function Section({ title, icon, children, actions }: { title: string; icon?: ReactNode; children: ReactNode; actions?: ReactNode }) {
  return <Card title={title} actions={actions ?? (icon ? <span className="text-slate-400">{icon}</span> : undefined)}>{children}</Card>
}

export default function EntryDetail() {
  const { id } = useParams()
  const { can, path, me, portal } = useAuth()
  const nav = useNavigate()
  const [dialog, setDialog] = useState<'number' | 'so' | 'tracker' | 'answer' | null>(null)
  const { data: e, isLoading, error } = useQuery({ queryKey: ['entry', id], queryFn: async () => (await api.get<Detail>(`/entries/${id}`)).data })
  if (isLoading) return <Loading />
  if (error || !e) return <ErrorBox error={error ? errorMessage(error) : 'Not found'} />
  const synced = (new Date(e.received_at_server).getTime() - new Date(e.submitted_at_device).getTime()) / 60000
  const loc = e.location
  const canAnswer = can('branch.answer') && (LEAD_ACTIONS.includes(e.so_action ?? '') || e.cc_action === 'Follow-up')
  const onMyList = portal === 'callcentre' && e.on_list_of.some((a) => a.caller_id === me?.id || me?.role === 'master_owner')
  const lastAnswers = [...e.attempts].reverse().find((a) => a.answers && a.outcome === 'Connected')?.answers
  return (
    <>
      <button type="button" onClick={() => nav(-1)} className="mb-4 inline-flex items-center gap-1.5 text-sm font-medium text-slate-500 hover:text-brand-700"><ArrowLeft size={16} aria-hidden="true" />Back</button>
      <div className="mb-6 flex flex-wrap items-start justify-between gap-4 rounded-2xl border border-slate-200/80 bg-white p-5 shadow-card">
        <div className="min-w-0">
          <p className="font-mono text-sm font-semibold text-brand-700" data-testid="entry-code">{e.entry_code}</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight text-brand-900">{e.person_name}</h1>
          <p className="mt-1 text-sm text-slate-500">{e.category_label}{e.cp_subtype_label && ` · ${e.cp_subtype_label}`} · <span className="tabular">{e.phone}</span> · met by {e.so_name} ({e.so_employee_code}), {e.branch_name}</p>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <RagBadge value={e.rag} overridden={e.rag_overridden} />
            <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs"><StatusText status={e.status} selection={e.selection_status} callGroup={e.call_group} /></span>
            {e.priority && <span className="inline-flex items-center gap-1 rounded-full bg-roof-50 px-2.5 py-0.5 text-xs font-semibold text-roof-700"><Flag size={12} aria-hidden="true" />PRIORITY</span>}
            {e.lead_outcome && <span className="rounded-full bg-sky-50 px-2.5 py-0.5 text-xs font-semibold text-sky-700">{e.lead_outcome}</span>}
            {e.sankalp_success && <span className="rounded-full bg-gold-100 px-2.5 py-0.5 text-xs font-semibold text-gold-800">Sankalp success</span>}
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          {onMyList && can('calls.work') && <Link to={path(`calls/${e.id}`)}><Button><PhoneCall size={16} aria-hidden="true" />Open call screen</Button></Link>}
          {canAnswer && <Button onClick={() => setDialog('answer')}>Answer lead</Button>}
          {can('correct.number') && e.so_action === 'Correct customer number' && <Button variant="gold" onClick={() => setDialog('number')}>Correct number</Button>}
          {can('correct.so') && <Button variant="secondary" onClick={() => setDialog('so')}>Correct SO</Button>}
          {can('calls.manage') && <Button variant="secondary" onClick={() => setDialog('tracker')}>Follow-up tracker</Button>}
        </div>
      </div>

      {(e.so_action || e.cc_action) && (
        <div className="mb-6 grid gap-3 sm:grid-cols-2">
          {e.so_action && <div className="rounded-xl border border-brand-200 bg-brand-50 px-4 py-3 text-sm"><span className="text-xs font-semibold uppercase tracking-wider text-brand-600">SO / branch action</span><p className="font-semibold text-brand-900">{e.so_action}{e.so_action_date && ` · ${e.so_action_date}`}</p>{e.so_action_until && <p className="text-xs text-slate-500">Open until {e.so_action_until}</p>}</div>}
          {e.cc_action && <div className="rounded-xl border border-gold-300/70 bg-gold-50 px-4 py-3 text-sm"><span className="text-xs font-semibold uppercase tracking-wider text-gold-700">Call-centre action</span><p className="font-semibold text-brand-900">{e.cc_action}{e.cc_action_date && ` · ${e.cc_action_date}`}</p></div>}
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <Section title="The entry">
          <KV items={[
            ['Sales Officer', `${e.so_name} (${e.so_employee_code})`], ['Entry ID built from Emp ID', e.emp_code],
            ['Branch / region', `${e.branch_name ?? '—'} · ${e.region_name ?? '—'}`], ['Spoke', e.spoke],
            ['Category', e.category_label], ['CP sub-type', e.cp_subtype_label],
            ['Mobile (as typed)', e.phone_raw], ['Keka photo time', e.keka_photo_time?.slice(0, 5)],
          ]} />
          <div className="mt-4 rounded-xl bg-slate-50 p-3 text-sm text-slate-700">{e.description}</div>
        </Section>

        <Section title="When and where" icon={<MapPin size={18} />}>
          {e.device_time_suspect && <p className="mb-3 flex items-center gap-2 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800"><TriangleAlert size={14} aria-hidden="true" />The phone’s clock was ahead of the server when this entry arrived: check the time.</p>}
          <KV items={[
            ['Submit pressed (phone time)', fmtDevice(e.submitted_at_device, e.device_tz_offset_min)],
            ['Received by the server', `${fmtServer(e.received_at_server)}${synced > 5 ? ` · synced ${synced > 120 ? `${Math.round(synced / 60)} h` : `${Math.round(synced)} min`} later` : ''}`],
            ['Entry date', e.entry_date], ['Counts on', e.count_date],
            ['GPS at Submit', validCoords(loc.latitude, loc.longitude) ? <a className="font-medium text-brand-700 underline" href={mapUrl(loc.latitude!, loc.longitude!)} target="_blank" rel="noreferrer noopener">{loc.latitude!.toFixed(5)}, {loc.longitude!.toFixed(5)}</a> : `No fix (${loc.status.replace('_', ' ')})`],
            ['Accuracy', validCoords(loc.latitude, loc.longitude) ? accuracyLabel(loc.accuracy_m) : '—'],
            ['Place', loc.place_name ?? (loc.place_status === 'pending' ? 'Looking up…' : '—')],
          ]} />
        </Section>
      </div>

      {e.photos.length > 0 && (
        <Card title={`Photos (${e.photos.length})`} className="mt-6" actions={<Camera size={18} className="text-slate-400" />}>
          <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {e.photos.map((p) => (
              <li key={p.photo_id} className="overflow-hidden rounded-xl border border-slate-200">
                <a href={p.url} target="_blank" rel="noreferrer noopener"><img src={p.thumb_url} alt="Evidence photo" className="aspect-[4/3] w-full bg-slate-100 object-cover" /></a>
                <div className="space-y-0.5 p-2.5 text-xs text-slate-600">
                  <p>Taken {fmtServer(p.photo_captured_at_device)}</p>
                  <p>{validCoords(p.latitude, p.longitude) ? `${p.latitude!.toFixed(5)}, ${p.longitude!.toFixed(5)} · ${accuracyLabel(p.accuracy_m)}` : 'No GPS'}</p>
                  {p.place_name && <p className="truncate">{p.place_name}</p>}
                </div>
              </li>
            ))}
          </ul>
        </Card>
      )}

      <Card title="Calls" className="mt-6" flush actions={<span className="text-xs text-slate-500">Cycle {e.call_cycle} · {e.unanswered_count} unanswered · first caller {e.first_caller ?? '—'}</span>}>
        {e.attempts.length === 0 ? <p className="px-5 pb-5 text-sm text-slate-500">{e.on_list_of.length ? `On the list of ${e.on_list_of.map((a) => a.caller ?? 'no caller yet').join(', ')} (${e.on_list_of[0]!.kind}).` : 'Not called yet.'}</p> : (
          <Table head={['Date', 'Slot', 'Outcome', 'Status it produced', 'Caller', 'Next date']}>
            {e.attempts.map((a) => (
              <tr key={a.id}><Td className="whitespace-nowrap">{a.call_date}{a.cycle > 1 && <span className="ml-1 text-xs text-slate-400">(cycle {a.cycle})</span>}</Td><Td>{a.slot}</Td><Td>{a.outcome}</Td>
                <Td>{a.row_status}</Td><Td>{a.caller}</Td><Td>{a.next_date ?? (a.answers?.next_date as string) ?? '—'}</Td></tr>
            ))}
          </Table>
        )}
      </Card>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        {lastAnswers && (
          <Section title="Answers on the last connected call">
            <KV items={Object.entries(lastAnswers).map(([k, v]) => [ANSWER_LABELS[k] ?? k, show(v)])} />
          </Section>
        )}
        {e.lead_card && (
          <Section title="Lead card" icon={<IdCard size={18} />}>
            <KV items={[
              ['TCS lead ID', e.lead_card.lead_id], ['Loan requirement (₹)', show(e.lead_card.loan_requirement)],
              ...Object.entries(e.lead_card).filter(([k]) => CARD_LABELS[k]).map(([k, v]) => [CARD_LABELS[k]!, show(v)] as [string, string]),
            ]} />
            <p className="mt-3 text-xs text-slate-500">The lead ID never closes a lead: only the login register does.</p>
          </Section>
        )}
        <Section title="Outcome and flags">
          <KV items={[
            ['Customer validated', yes(e.customer_validated)], ['Validated on', e.validated_on], ['First validation for this number', yes(e.first_validation)],
            ['Lead outcome', e.lead_outcome], ['TCS ID', e.tcs_id ? `${e.tcs_id}${e.login_source === 'manual' ? ' (entered by hand)' : ''}` : null],
            ['Login date', e.login_date], ['Counts as Sankalp success', yes(e.sankalp_success)], ['Category review', e.category_review],
          ]} />
        </Section>
        {e.branch_answers.length > 0 && (
          <Section title="Branch answers">
            <ul className="space-y-2 text-sm">
              {[...e.branch_answers].reverse().map((b) => (
                <li key={b.id} className="rounded-lg bg-slate-50 px-3 py-2">
                  <span className="font-semibold text-brand-900">{b.code}</span> · {b.meaning}{b.answer_date && ` · ${b.answer_date}`}
                  <div className="text-xs text-slate-500">{b.by} on {b.responded_on}{b.green_channel && ` · green channel: ${b.green_channel}`}{b.note && ` · ${b.note}`}</div>
                </li>
              ))}
            </ul>
          </Section>
        )}
        {e.tracker && (
          <Section title="Follow-up tracker">
            <KV items={[['Owner', e.tracker.owner], ['Action', e.tracker.action_type], ['Caller', e.tracker.caller], ['Follow-up date', e.tracker.followup_date],
              ['Outcome', e.tracker.outcome], ['TCS ID', e.tracker.tcs_id], ['RAG override', e.tracker.rag_override], ['Notes', e.tracker.notes]]} />
          </Section>
        )}
        {e.same_number.length > 0 && (
          <Section title="Same number, other entries">
            <ul className="space-y-1.5 text-sm">
              {e.same_number.map((o) => (
                <li key={o.id} className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-1.5">
                  <Link className="font-mono text-xs font-semibold text-brand-700 hover:underline" to={path(`entries/${o.id}`)}>{o.entry_code}</Link>
                  <span className="text-xs text-slate-500">{o.so_name} · {o.entry_date} · {o.category} · {o.status ?? '—'}</span><RagBadge value={o.rag} />
                </li>
              ))}
            </ul>
          </Section>
        )}
      </div>

      <Card title="History" className="mt-6" actions={<History size={18} className="text-slate-400" />}>
        <ol className="relative space-y-3 border-l border-slate-200 pl-5 text-sm">
          {e.history.map((h, i) => (
            <li key={i}>
              <span className="absolute -left-[5px] mt-1.5 h-2.5 w-2.5 rounded-full bg-brand-500" aria-hidden="true" />
              <span className="font-medium text-slate-800">{h.kind.replace('.', ': ').replace(/_/g, ' ')}</span>
              <span className="text-slate-500"> · {fmtServer(h.at)}{h.by && ` · ${h.by}`}</span>
              {h.detail && <div className="text-xs text-slate-500">{Object.entries(h.detail).filter(([, v]) => v != null).map(([k, v]) => `${k.replace(/_/g, ' ')}: ${detailText(v)}`).join(' · ')}</div>}
            </li>
          ))}
        </ol>
      </Card>

      {dialog === 'number' && <CorrectNumberDialog entry={e} onClose={() => setDialog(null)} />}
      {dialog === 'so' && <CorrectSoDialog entry={e} onClose={() => setDialog(null)} />}
      {dialog === 'tracker' && <TrackerDialog entry={e} onClose={() => setDialog(null)} />}
      {dialog === 'answer' && <AnswerDialog entryId={e.id} entryCode={e.entry_code} onClose={() => setDialog(null)} />}
    </>
  )
}
