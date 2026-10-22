import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, Building2, Camera, Clock, Flag, MapPin } from 'lucide-react'
import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Avatar, Badge, Button, Card, cx, ErrorBox, Input, Skeleton } from '../../components/ui'
import { api, errorMessage } from '../../services/api'
import { accuracyLabel, fmtDevice, fmtServer, mapUrl, validCoords } from '../../services/format'
import type { FormField, PhotoMeta, SubmissionDetail as SD } from '../../types'
import { ReviewHistory, ReviewPanel } from './ReviewPanel'

function Row({ k, children }: { k: string; children: React.ReactNode }) {
  return <div className="grid grid-cols-[8rem_minmax(0,1fr)] gap-3 py-1.5 text-sm"><dt className="text-slate-500">{k}</dt><dd className="break-words text-slate-800">{children}</dd></div>
}

function Place({ lat, lon, acc, status, placeName, placeStatus }: { lat: number | null; lon: number | null; acc: number | null; status: string; placeName?: string | null; placeStatus?: string }) {
  if (!validCoords(lat, lon)) return <span className="text-slate-500">Unavailable ({status.replace('_', ' ')})</span>
  return (
    <span>
      {placeName ? <strong data-testid="place-name" className="block font-medium text-brand-900">{placeName}</strong>
        : placeStatus === 'pending' ? <span className="block text-slate-500" data-testid="place-pending">Looking up place name…</span> : null}
      {lat!.toFixed(6)}, {lon!.toFixed(6)} · {accuracyLabel(acc)} ·{' '}
      <a className="font-medium text-brand-700 underline decoration-brand-300 underline-offset-2 hover:decoration-brand-700" target="_blank" rel="noreferrer noopener" href={mapUrl(lat!, lon!)}>Open in Google Maps</a>
    </span>
  )
}

/** "Flag" lets the reviewer point the agent at one meeting or photo; flags are sent with a rejection. */
function FlagControl({ path, flags, setFlags, active, sent }: { path: string; flags: Record<string, string>; setFlags: (f: Record<string, string>) => void; active: boolean; sent?: string }) {
  const [open, setOpen] = useState(false)
  const [note, setNote] = useState('')
  if (!active) return sent ? <p className="text-xs font-medium text-roof-700">Flagged: {sent}</p> : null
  if (flags[path]) {
    return (
      <p className="flex items-center gap-2 text-xs font-medium text-roof-700" data-testid="flag-set">
        Flagged: {flags[path]}
        <button type="button" className="font-normal underline" onClick={() => { const { [path]: _drop, ...rest } = flags; void _drop; setFlags(rest) }}>remove</button>
      </p>
    )
  }
  if (!open) {
    return (
      <span className="flex items-center gap-3">
        {sent && <span className="text-xs font-medium text-roof-700">Flagged earlier: {sent}</span>}
        <button type="button" className="inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-xs font-medium text-brand-700 hover:bg-brand-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500" onClick={() => setOpen(true)}>
          <Flag size={12} aria-hidden="true" />Flag
        </button>
      </span>
    )
  }
  return (
    <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); if (note.trim()) { setFlags({ ...flags, [path]: note.trim() }); setNote(''); setOpen(false) } }}>
      <Input aria-label="Flag note" className="text-xs" placeholder="What is wrong here?" value={note} maxLength={300} autoFocus onChange={(e) => setNote(e.target.value)} />
      <Button type="submit" small disabled={!note.trim()}>Add</Button>
      <Button type="button" variant="secondary" small onClick={() => setOpen(false)}>Cancel</Button>
    </form>
  )
}

function PhotoCard({ p, offset, flag }: { p: PhotoMeta; offset: number | null; flag?: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-3" data-testid="photo-card">
      <div className="flex flex-col gap-3 sm:flex-row">
        <a href={p.url} target="_blank" rel="noreferrer noopener" className="shrink-0 self-start overflow-hidden rounded-lg ring-1 ring-slate-200 transition hover:ring-brand-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500">
          <img src={p.thumb_url} alt={`Photo ${p.field_key ?? ''}`} className="h-28 w-28 object-cover" />
        </a>
        <dl className="min-w-0 flex-1">
          <h4 className="mb-1 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-slate-500"><Camera size={13} aria-hidden="true" />Photo capture event</h4>
          <Row k="Captured (device)">{fmtDevice(p.photo_captured_at_device, offset)}</Row>
          <Row k="Captured (EXIF)">{p.exif_captured_at ? `${fmtServer(p.exif_captured_at)} — from file, unverified` : '—'}</Row>
          <Row k="Photo location"><Place lat={p.photo_capture_latitude} lon={p.photo_capture_longitude} acc={p.photo_capture_accuracy_m} status={p.photo_location_status} placeName={p.photo_place_name} placeStatus={p.photo_place_status} /></Row>
          <Row k="Location fix">{fmtDevice(p.photo_location_fix_at_device, offset)}</Row>
          <Row k="Uploaded (server)">{fmtServer(p.upload_completed_at_server)}</Row>
          <Row k="File">{p.mime_type} · {p.size_bytes ?? '?'} bytes · SHA-256 <span className="font-mono text-xs">{p.sha256?.slice(0, 12)}…</span></Row>
        </dl>
      </div>
      {flag}
    </div>
  )
}

/** Text shown for an answer. Managed options show the label saved with the report, "other:" shows the typed value. */
export function displayValue(f: FormField, v: unknown, path: string, labels: Record<string, string>): string {
  if (v == null || v === '') return '—'
  if (labels[path]) return typeof v === 'string' && v.startsWith('other:') ? `${labels[path]} (other)` : labels[path]
  if (Array.isArray(v)) return v.join(', ')
  if (typeof v === 'object') return JSON.stringify(v)
  if (typeof v === 'boolean') return v ? 'Yes' : 'No'
  return String(v)
}

function DetailSkeleton() {
  return (
    <div role="status" aria-label="Loading report">
      <Skeleton className="mb-5 h-32" />
      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_380px]"><Skeleton className="h-96" /><Skeleton className="h-96" /></div>
    </div>
  )
}

export default function SubmissionDetail() {
  const { id } = useParams()
  const [flags, setFlags] = useState<Record<string, string>>({})
  const { data, isLoading, error } = useQuery({
    queryKey: ['submissions', 'detail', id],
    queryFn: async () => (await api.get<SD>(`/submissions/${id}`)).data,
    // Photo links are short-lived (5 min): refresh them. While a place name is still being looked up, poll every 4 s.
    refetchInterval: (q) => {
      const d = q.state.data
      // only a position that exists can still be waiting for its name (reports without GPS stay 'pending' forever)
      const pending = d && (
        (d.submission_location.place_status === 'pending' && d.submission_location.latitude != null) ||
        d.photos.some((p) => p.photo_place_status === 'pending' && p.photo_capture_latitude != null)
      )
      return pending ? 4000 : 4 * 60 * 1000
    },
  })
  if (isLoading) return <DetailSkeleton />
  if (error || !data) return <ErrorBox error={errorMessage(error)} />
  const offset = data.device_tz_offset_min
  const byId = new Map(data.photos.map((p) => [p.photo_id, p]))
  const sl = data.submission_location
  const reviewing = data.is_latest && data.review_status !== 'approved'
  // flags the reviewer set when this version was sent back, shown to anyone reading it later
  const sentFlags: Record<string, string> = Object.fromEntries((data.review_status === 'rejected' ? data.review_flags : []).map((f) => [f.path, f.note]))
  const shown = { ...sentFlags, ...flags } // earlier flags stay visible while the reviewer adds new ones
  return (
    <>
      <Link to="/submissions" className="mb-4 inline-flex items-center gap-1.5 text-sm font-medium text-slate-500 hover:text-brand-700"><ArrowLeft size={16} aria-hidden="true" />Submissions</Link>

      <section className="mb-5 rounded-2xl border border-slate-200/80 bg-white p-5 shadow-card">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex flex-wrap items-center gap-3">
              <h1 className="font-mono text-2xl font-semibold tracking-tight text-brand-900">{data.reference}</h1>
              <Badge value={data.review_status} />
            </div>
            <p className="mt-1 text-sm text-slate-500">{data.form_title} · version {data.form_version}</p>
          </div>
          {data.revisions.length > 1 && (
            <nav aria-label="Versions" className="flex flex-wrap gap-2 text-sm">
              {data.revisions.map((r) => r.id === data.id
                ? <span key={r.id} className="rounded-lg bg-brand-700 px-3 py-1.5 font-medium text-white">Revision {r.revision}{r.is_latest ? ' (current)' : ''}</span>
                : <Link key={r.id} className="rounded-lg border border-slate-300 px-3 py-1.5 font-medium text-slate-700 hover:bg-slate-50" to={`/submissions/${r.id}`}>Revision {r.revision}{r.is_latest ? ' (current)' : ''}</Link>)}
            </nav>
          )}
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-x-6 gap-y-2 border-t border-slate-100 pt-4 text-sm text-slate-600">
          <span className="flex items-center gap-2"><Avatar name={data.agent_name} size="sm" /><span><span className="font-medium text-slate-800">{data.agent_name}</span> <span className="text-slate-400">({data.employee_code})</span></span></span>
          <span className="flex items-center gap-1.5"><Building2 size={15} className="text-slate-400" aria-hidden="true" />{data.branch_name ?? 'No branch'}</span>
          <span className="flex items-center gap-1.5"><Clock size={15} className="text-slate-400" aria-hidden="true" />Received {fmtServer(data.received_at_server)}</span>
          <span className="flex items-center gap-1.5"><Camera size={15} className="text-slate-400" aria-hidden="true" />{data.photo_count} {data.photo_count === 1 ? 'photo' : 'photos'}</span>
          <span className={cx('flex items-center gap-1.5', validCoords(sl.latitude, sl.longitude) ? 'text-emerald-700' : 'text-slate-400')}><MapPin size={15} aria-hidden="true" />{validCoords(sl.latitude, sl.longitude) ? 'Location recorded' : 'No location'}</span>
        </div>
      </section>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_380px]">
        <aside className="order-first space-y-5 xl:order-none xl:col-start-2 xl:row-start-1 xl:sticky xl:top-20 xl:self-start">
          <ReviewPanel d={data} flags={flags} onFlagsCleared={() => setFlags({})} />
          <Card title="Report information">
            <dl>
              <Row k="Agent">{data.agent_name} ({data.employee_code})</Row>
              <Row k="Branch">{data.branch_name ?? '—'}</Row>
              <Row k="Form">{data.form_title} v{data.form_version}</Row>
              <Row k="Reference">{data.reference} · revision {data.revision}</Row>
              <Row k="Submission ID"><span className="font-mono text-xs">{data.id}</span></Row>
              <Row k="Device reference"><span className="font-mono text-xs">{data.client_submission_id}</span></Row>
              <Row k="Received (server)">{fmtServer(data.received_at_server)}</Row>
              <Row k="Accepted (server)">{fmtServer(data.accepted_at_server)} <Badge value={data.status} /></Row>
            </dl>
          </Card>
          <Card title="Submission event (when Submit was pressed)">
            <dl>
              <Row k="Submitted (device)">{fmtDevice(data.submitted_at_device, offset)}</Row>
              <Row k="Submission location"><Place lat={sl.latitude} lon={sl.longitude} acc={sl.accuracy_m} status={sl.status} placeName={sl.place_name} placeStatus={sl.place_status} /></Row>
              <Row k="Location fix">{fmtDevice(sl.fix_at_device, offset)}</Row>
            </dl>
            <p className="mt-3 rounded-lg bg-slate-50 p-3 text-xs leading-relaxed text-slate-500">Device times and GPS are reports from the agent's phone, not tamper-proof evidence. Server times are authoritative. A missing or imprecise GPS reading is not by itself a reason to reject.</p>
          </Card>
        </aside>

        <div className="min-w-0 space-y-5 xl:col-start-1 xl:row-start-1">
          {data.schema.sections.map((sec) => {
            const raw = data.answers[sec.id]
            const entries: Record<string, any>[] = sec.repeatable ? raw ?? [] : [raw ?? {}]
            return (
              <Card key={sec.id} title={sec.title ?? sec.id}>
                <div className="space-y-4">
                  {entries.map((entry, i) => {
                    const base = sec.repeatable ? `${sec.id}[${i}]` : sec.id
                    return (
                      <section key={i} aria-label={sec.repeatable ? `Meeting ${i + 1}` : sec.title} className={cx('rounded-xl border p-4', shown[base] ? 'border-roof-300 bg-roof-50/60' : 'border-slate-200')}>
                        {sec.repeatable && (
                          <div className="mb-2 flex items-center justify-between gap-2">
                            <h3 className="flex items-center gap-2 text-sm font-semibold text-brand-900">
                              <span className="grid h-6 w-6 place-items-center rounded-full bg-brand-100 text-xs text-brand-700" aria-hidden="true">{i + 1}</span>Meeting {i + 1}
                            </h3>
                            <FlagControl path={base} flags={flags} setFlags={setFlags} active={reviewing} sent={sentFlags[base]} />
                          </div>
                        )}
                        <dl>
                          {sec.fields.filter((f) => !['heading', 'readonly_text'].includes(f.type)).map((f) => {
                            const v = entry[f.key]
                            const path = `${base}.${f.key}`
                            const photoIds: string[] = f.type === 'photo' ? (v ? [v] : []) : f.type === 'photos' ? v ?? [] : []
                            return (
                              <div key={f.key}>
                                <Row k={f.label}>{photoIds.length ? `${photoIds.length} photo(s)` : displayValue(f, v, path, data.option_labels)}</Row>
                                {photoIds.map((pid) => byId.get(pid)).filter(Boolean).map((p) => (
                                  <div key={p!.photo_id} className="mb-2 mt-1">
                                    <PhotoCard p={p!} offset={offset} flag={<div className="mt-2"><FlagControl path={path} flags={flags} setFlags={setFlags} active={reviewing} sent={sentFlags[path]} /></div>} />
                                  </div>
                                ))}
                              </div>
                            )
                          })}
                        </dl>
                      </section>
                    )
                  })}
                </div>
              </Card>
            )
          })}

          <ReviewHistory d={data} />
          <Card title="Events">
            <ol className="relative ml-2 space-y-3 border-l border-slate-200 pl-5 text-sm">
              {data.events.map((e, i) => (
                <li key={i} className="relative">
                  <span className="absolute -left-[26px] top-1.5 h-2 w-2 rounded-full bg-brand-500 ring-4 ring-white" aria-hidden="true" />
                  <span className="text-slate-500">{fmtServer(e.at)}</span> — <span className="font-medium text-slate-800">{e.type}</span>{e.detail && e.type === 'resubmitted' ? ` (${e.detail})` : ''}
                </li>
              ))}
            </ol>
          </Card>
        </div>
      </div>
    </>
  )
}
