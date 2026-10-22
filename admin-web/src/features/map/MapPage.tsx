/// <reference types="google.maps" />
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { Info, MapPin, MapPinOff, TriangleAlert } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { Avatar, Badge, Button, Card, cx, EmptyState, ErrorBox, PageTitle, Skeleton, Table, Td, Toggle } from '../../components/ui'
import { api, errorMessage } from '../../services/api'
import { fmtServer } from '../../services/format'
import type { MapData, MapReport } from '../../types'
import { Filters, filterParams } from '../submissions/Filters'
import { loadGoogleMaps, onMapsAuthFailure } from './googleMaps'
import { ACCURACY_TEXT, BRANCH_COLOR, PHOTO_COLOR, STATUS_COLOR, accuracyClass, markerStyle, popupLines } from './markers'

const MAP_KEY = (import.meta.env.VITE_GOOGLE_MAPS_API_KEY as string | undefined)?.trim()

// Quieter base map: shops and transit stops would compete with the report markers.
const MAP_STYLES: google.maps.MapTypeStyle[] = [
  { featureType: 'poi', stylers: [{ visibility: 'off' }] },
  { featureType: 'transit', stylers: [{ visibility: 'off' }] },
]

function FieldMap({ apiKey, data, focusId, onOpenReport }: { apiKey: string; data: MapData; focusId: string | null; onOpenReport: (id: string) => void }) {
  const el = useRef<HTMLDivElement>(null)
  const map = useRef<google.maps.Map | null>(null)
  const byId = useRef(new Map<string, { marker: google.maps.Marker; r: MapReport }>())
  const info = useRef<google.maps.InfoWindow | null>(null)
  const ring = useRef<google.maps.Circle | null>(null)
  const things = useRef<(google.maps.Marker | google.maps.Circle)[]>([])
  const [err, setErr] = useState<string | null>(null)
  const [ready, setReady] = useState(false)

  const open = (g: typeof google, r: MapReport, marker: google.maps.Marker) => {
    ring.current?.setMap(null)
    if (r.accuracy_m) {
      // the accuracy radius: the real position can be anywhere inside this circle
      ring.current = new g.maps.Circle({ map: map.current!, center: marker.getPosition()!, radius: r.accuracy_m, strokeColor: '#283079', strokeOpacity: 0.6, strokeWeight: 1, fillColor: '#4d58a3', fillOpacity: 0.12 })
    }
    const box = document.createElement('div')
    box.style.cssText = "font:13px/1.45 'Inter Variable',Inter,system-ui,sans-serif;max-width:260px;color:#1e293b"
    popupLines(r).forEach((line, i) => { const p = document.createElement('div'); p.textContent = line; if (i === 0) { p.style.fontWeight = '600'; p.style.color = '#17153a'; p.style.marginBottom = '2px' } box.appendChild(p) })
    const btn = document.createElement('button')
    btn.textContent = 'Open report'
    btn.style.cssText = 'margin-top:8px;color:#283079;font-weight:600;text-decoration:underline;background:none;border:0;cursor:pointer;padding:0'
    btn.addEventListener('click', () => onOpenReport(r.id))
    box.appendChild(btn)
    info.current ??= new g.maps.InfoWindow()
    info.current.setContent(box) // DOM node, not an HTML string: agent-entered text can never become markup
    info.current.open({ map: map.current!, anchor: marker })
  }

  useEffect(() => {
    let cancelled = false
    const off = onMapsAuthFailure((m) => !cancelled && setErr(m))
    loadGoogleMaps(apiKey).then((g) => {
      if (cancelled || !el.current) return
      map.current ??= new g.maps.Map(el.current, { center: { lat: 20.5937, lng: 78.9629 }, zoom: 5, mapTypeControl: false, streetViewControl: false, styles: MAP_STYLES })
      things.current.forEach((t) => t.setMap(null)); things.current = []; byId.current.clear()
      const bounds = new g.maps.LatLngBounds()
      for (const r of data.reports) {
        const st = markerStyle(r.review_status, r.accuracy_m)
        const marker = new g.maps.Marker({
          map: map.current!, position: { lat: r.latitude, lng: r.longitude }, title: `${r.reference} · ${r.agent_name}`,
          icon: { path: g.maps.SymbolPath.CIRCLE, scale: st.scale, fillColor: st.color, fillOpacity: st.fillOpacity, strokeColor: st.color, strokeWeight: st.strokeWeight },
        })
        marker.addListener('click', () => open(g, r, marker))
        byId.current.set(r.id, { marker, r }); things.current.push(marker); bounds.extend(marker.getPosition()!)
      }
      for (const p of data.photos) {
        const m = new g.maps.Marker({ map: map.current!, position: { lat: p.latitude, lng: p.longitude }, title: `Photo · ${p.reference}`,
          icon: { path: g.maps.SymbolPath.BACKWARD_CLOSED_ARROW, scale: 4, fillColor: PHOTO_COLOR, fillOpacity: 0.9, strokeColor: PHOTO_COLOR, strokeWeight: 1 } })
        m.addListener('click', () => onOpenReport(p.submission_id)); things.current.push(m); bounds.extend(m.getPosition()!)
      }
      for (const b of data.branches) {
        const m = new g.maps.Marker({ map: map.current!, position: { lat: b.latitude, lng: b.longitude }, title: `Branch: ${b.name}`, zIndex: 0,
          icon: { path: 'M -7,-7 7,-7 7,7 -7,7 z', scale: 1, fillColor: BRANCH_COLOR, fillOpacity: 0.85, strokeColor: '#fff', strokeWeight: 1.5 } })
        things.current.push(m); bounds.extend(m.getPosition()!)
      }
      if (!bounds.isEmpty()) { map.current!.fitBounds(bounds, 48); g.maps.event.addListenerOnce(map.current!, 'idle', () => { if ((map.current!.getZoom() ?? 0) > 16) map.current!.setZoom(16) }) }
      setReady(true)
    }).catch((e) => !cancelled && setErr(e.message))
    return () => { cancelled = true; off() }
  }, [apiKey, data])  // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const hit = focusId ? byId.current.get(focusId) : undefined
    if (hit && map.current && (window as any).google) { map.current.panTo(hit.marker.getPosition()!); map.current.setZoom(Math.max(map.current.getZoom() ?? 5, 15)); open((window as any).google, hit.r, hit.marker) }
  }, [focusId, ready])  // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="relative">
      <ErrorBox error={err} />
      <div ref={el} className="h-[420px] w-full overflow-hidden rounded-2xl border border-slate-200/80 bg-slate-100 shadow-card lg:h-[600px]" role="application" aria-label="Map of recorded report locations" data-testid="google-map" />
      <Legend />
    </div>
  )
}

function Legend() {
  const dot = (c: string, hollow = false) => <span className="inline-block h-3 w-3 rounded-full align-middle" style={{ background: hollow ? 'transparent' : c, border: `2px solid ${c}` }} />
  return (
    <ul className="pointer-events-none absolute bottom-3 left-3 hidden max-w-[calc(100%-5rem)] flex-wrap gap-x-4 gap-y-1 rounded-xl bg-white/95 px-3 py-2 text-xs text-slate-600 shadow-card ring-1 ring-black/5 sm:flex" aria-label="Map legend">
      <li>{dot(STATUS_COLOR.pending!)} Pending review</li><li>{dot(STATUS_COLOR.approved!)} Approved</li><li>{dot(STATUS_COLOR.rejected!)} Needs correction</li>
      <li>{dot('#64748b', true)} Hollow = poor or unknown GPS accuracy</li>
      <li><span style={{ color: PHOTO_COLOR }}>▲</span> Photo location</li><li><span style={{ color: BRANCH_COLOR }}>■</span> Branch</li>
    </ul>
  )
}

/** Scrollable list beside the map: pick a report to centre the map on it. */
function LocationPanel({ reports, activeId, onPick }: { reports: MapReport[]; activeId: string | null; onPick: (id: string) => void }) {
  return (
    <aside aria-label="Recorded locations" className="flex h-[420px] flex-col overflow-hidden rounded-2xl border border-slate-200/80 bg-white shadow-card lg:h-[600px]">
      <header className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
        <h2 className="text-sm font-semibold text-brand-900">Recorded locations</h2>
        <span className="rounded-full bg-brand-50 px-2 py-0.5 text-xs font-semibold text-brand-700">{reports.length}</span>
      </header>
      {reports.length === 0 ? (
        <EmptyState icon={<MapPinOff size={20} />} title="No reports with a recorded GPS position match these filters." />
      ) : (
        <ul className="flex-1 divide-y divide-slate-100 overflow-y-auto">
          {reports.map((r) => {
            const cls = accuracyClass(r.accuracy_m)
            return (
              <li key={r.id} className={cx('px-4 py-3 transition', activeId === r.id ? 'bg-brand-50/70' : 'hover:bg-slate-50')}>
                <div className="flex items-start gap-3">
                  <Avatar name={r.agent_name} size="sm" />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between gap-2">
                      <Link className="font-mono text-sm font-medium text-brand-700 hover:underline" to={`/submissions/${r.id}`}>{r.reference}</Link>
                      <Badge value={r.review_status} />
                    </div>
                    <p className="truncate text-sm text-slate-700">{r.agent_name} · {r.branch_name ?? 'No branch'}</p>
                    <p className="mt-0.5 text-xs text-slate-500">{r.place_name ?? (r.place_status === 'pending' ? 'Looking up place…' : 'No place name')}</p>
                    <p className={cx('mt-0.5 text-xs', cls === 'poor' || cls === 'unknown' ? 'text-amber-700' : 'text-slate-500')}>
                      {r.accuracy_m != null ? `±${Math.round(r.accuracy_m)} m` : 'accuracy unknown'} · {ACCURACY_TEXT[cls]} · {fmtServer(r.submitted_at_device)}
                    </p>
                    <Button variant="secondary" small className="mt-2" onClick={() => onPick(r.id)}><MapPin size={13} aria-hidden="true" />Show on map</Button>
                  </div>
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </aside>
  )
}

export default function MapPage() {
  const [params, setParams] = useSearchParams()
  const nav = useNavigate()
  const [focus, setFocus] = useState<string | null>(null)
  const photos = params.get('photos') === '1'
  const branches = params.get('branches') !== '0'
  const toggle = (k: string, on: boolean, defaultOn: boolean) => { const n = new URLSearchParams(params); on === defaultOn ? n.delete(k) : n.set(k, on ? '1' : '0'); setParams(n) }
  const { data, isLoading, error } = useQuery({
    queryKey: ['map', Object.fromEntries(params)],
    queryFn: async () => (await api.get<MapData>('/map/markers', { params: { ...filterParams(params), include_photos: photos, include_branches: branches } })).data,
    placeholderData: keepPreviousData,
  })
  return (
    <>
      <PageTitle subtitle="Where reports were submitted, as recorded by the agent's phone.">Field activity map</PageTitle>
      <Filters params={params} onChange={setParams} showReference={false} extra={
        <>
          <Toggle label="Photo locations" checked={photos} onChange={(v) => toggle('photos', v, false)} />
          <Toggle label="Branches" checked={branches} onChange={(v) => toggle('branches', v, true)} />
        </>} />
      <ErrorBox error={error ? errorMessage(error) : null} />
      {isLoading || !data ? (
        <div role="status" aria-label="Loading map"><Skeleton className="mb-4 h-12" /><Skeleton className="h-[420px] lg:h-[600px]" /></div>
      ) : (
        <>
          <p className="mb-4 flex items-start gap-2.5 rounded-xl bg-brand-50 px-4 py-3 text-sm text-brand-800" data-testid="map-summary">
            <Info size={16} className="mt-0.5 shrink-0" aria-hidden="true" />
            <span>
              Showing {data.counts.shown} of {data.counts.with_gps} reports with a recorded GPS position
              {data.counts.without_gps > 0 && <> · <strong>{data.counts.without_gps}</strong> without GPS are not on the map</>}
              {data.counts.truncated && ' · list limited to the newest 2000'}.
              {' '}These are the positions recorded when Submit was pressed (and, if switched on, when photos were taken). The app does not track agents continuously.
            </span>
          </p>
          {MAP_KEY ? (
            <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_360px]">
              <FieldMap apiKey={MAP_KEY} data={data} focusId={focus} onOpenReport={(id) => nav(`/submissions/${id}`)} />
              <LocationPanel reports={data.reports} activeId={focus} onPick={setFocus} />
            </div>
          ) : (
            <>
              <div className="mb-4 flex items-start gap-3 rounded-2xl border border-gold-300/70 bg-gold-50 p-5">
                <TriangleAlert size={20} className="mt-0.5 shrink-0 text-gold-700" aria-hidden="true" />
                <div>
                  <h2 className="text-sm font-semibold text-brand-900">Google Maps is not set up yet</h2>
                  <p className="mt-1 text-sm text-slate-700" data-testid="map-key-missing">
                    Add a Google Maps <strong>browser key</strong> to show the map: put <code>VITE_GOOGLE_MAPS_API_KEY=your-key</code> in <code>admin-web/.env.local</code> and restart the admin web.
                    The key needs the <em>Maps JavaScript API</em> enabled and should be restricted to this website's address. Steps: <code>docs/google-maps-setup.md</code>.
                    The locations are listed below in the meantime, each with a Google Maps link.
                  </p>
                </div>
              </div>
              <Card title={`Locations (${data.reports.length})`} flush>
                <Table head={['Report', 'Agent', 'Branch', 'Review', 'Type of person', 'Place', 'Position', 'Recorded']}>
                  {data.reports.map((r) => {
                    const cls = accuracyClass(r.accuracy_m)
                    return (
                      <tr key={r.id}>
                        <Td className="whitespace-nowrap"><Link className="font-mono font-medium text-brand-700 hover:underline" to={`/submissions/${r.id}`}>{r.reference}</Link></Td>
                        <Td>{r.agent_name}</Td><Td>{r.branch_name ?? '—'}</Td><Td><Badge value={r.review_status} /></Td>
                        <Td>{r.person_types.join(', ') || '—'}</Td>
                        <Td>{r.place_name ?? (r.place_status === 'pending' ? 'Looking up…' : '—')}</Td>
                        <Td>
                          <a className="font-medium text-brand-700 underline decoration-brand-300 underline-offset-2" target="_blank" rel="noreferrer noopener" href={`https://www.google.com/maps?q=${r.latitude},${r.longitude}`}>{r.latitude.toFixed(5)}, {r.longitude.toFixed(5)}</a>
                          <div className={`text-xs ${cls === 'poor' || cls === 'unknown' ? 'text-amber-700' : 'text-slate-500'}`}>{r.accuracy_m != null ? `±${Math.round(r.accuracy_m)} m` : '—'} · {ACCURACY_TEXT[cls]}</div>
                        </Td>
                        <Td>{fmtServer(r.submitted_at_device)}</Td>
                      </tr>
                    )
                  })}
                </Table>
                {data.reports.length === 0 && <EmptyState icon={<MapPinOff size={20} />} title="No reports with a recorded GPS position match these filters." />}
              </Card>
            </>
          )}
        </>
      )}
    </>
  )
}
