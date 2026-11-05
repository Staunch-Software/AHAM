/// <reference types="google.maps" />
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { Info, MapPin, MapPinOff, TriangleAlert } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Avatar, Button, Card, cx, EmptyState, ErrorBox, PageTitle, RagBadge, Segmented, Select, Skeleton, Table, Td } from '../../components/ui'
import { api, errorMessage } from '../../services/api'
import { useAuth } from '../../services/auth'
import { fmtServer } from '../../services/format'
import { useBranches } from '../../services/meta'
import { PERIODS, type Period } from '../dashboard/Dashboard'
import { loadGoogleMaps, onMapsAuthFailure } from './googleMaps'
import { ACCURACY_TEXT, type MapMarker, RAG_COLOR, accuracyClass, markerStyle, popupLines } from './markers'

const MAP_KEY = (import.meta.env.VITE_GOOGLE_MAPS_API_KEY as string | undefined)?.trim()
interface MapData { period: { from: string; to: string }; total: number; shown: number; capped: boolean; limit: number; without_location: number; markers: MapMarker[] }

// Quieter base map: shops and transit stops would compete with the entry markers.
const MAP_STYLES: google.maps.MapTypeStyle[] = [
  { featureType: 'poi', stylers: [{ visibility: 'off' }] },
  { featureType: 'transit', stylers: [{ visibility: 'off' }] },
]

function FieldMap({ apiKey, markers, focusId, onOpen }: { apiKey: string; markers: MapMarker[]; focusId: string | null; onOpen: (id: string) => void }) {
  const el = useRef<HTMLDivElement>(null)
  const map = useRef<google.maps.Map | null>(null)
  const byId = useRef(new Map<string, { marker: google.maps.Marker; m: MapMarker }>())
  const info = useRef<google.maps.InfoWindow | null>(null)
  const ring = useRef<google.maps.Circle | null>(null)
  const things = useRef<google.maps.Marker[]>([])
  const [err, setErr] = useState<string | null>(null)
  const [ready, setReady] = useState(false)

  const open = (g: typeof google, m: MapMarker, marker: google.maps.Marker) => {
    ring.current?.setMap(null)
    if (m.accuracy_m) {
      // the accuracy radius: the real position can be anywhere inside this circle
      ring.current = new g.maps.Circle({ map: map.current!, center: marker.getPosition()!, radius: m.accuracy_m, strokeColor: '#283079', strokeOpacity: 0.6, strokeWeight: 1, fillColor: '#4d58a3', fillOpacity: 0.12 })
    }
    const box = document.createElement('div')
    box.style.cssText = "font:13px/1.45 'Inter Variable',Inter,system-ui,sans-serif;max-width:260px;color:#1e293b"
    popupLines(m).forEach((line, i) => { const p = document.createElement('div'); p.textContent = line; if (i === 0) { p.style.fontWeight = '600'; p.style.color = '#17153a'; p.style.marginBottom = '2px' } box.appendChild(p) })
    const btn = document.createElement('button')
    btn.textContent = 'Open entry'
    btn.style.cssText = 'margin-top:8px;color:#283079;font-weight:600;text-decoration:underline;background:none;border:0;cursor:pointer;padding:0'
    btn.addEventListener('click', () => onOpen(m.id))
    box.appendChild(btn)
    info.current ??= new g.maps.InfoWindow()
    info.current.setContent(box) // DOM node, not an HTML string: SO-entered text can never become markup
    info.current.open({ map: map.current!, anchor: marker })
  }

  useEffect(() => {
    let cancelled = false
    const off = onMapsAuthFailure((m) => !cancelled && setErr(m))
    loadGoogleMaps(apiKey).then((g) => {
      if (cancelled || !el.current) return
      map.current ??= new g.maps.Map(el.current, { center: { lat: 15.5, lng: 79.5 }, zoom: 6, mapTypeControl: false, streetViewControl: false, styles: MAP_STYLES })
      things.current.forEach((t) => t.setMap(null)); things.current = []; byId.current.clear()
      const bounds = new g.maps.LatLngBounds()
      for (const m of markers) {
        const st = markerStyle(m.rag, m.accuracy_m)
        const marker = new g.maps.Marker({
          map: map.current!, position: { lat: m.lat, lng: m.lng }, title: `${m.entry_code} · ${m.so_name}`,
          icon: { path: g.maps.SymbolPath.CIRCLE, scale: st.scale, fillColor: st.color, fillOpacity: st.fillOpacity, strokeColor: st.color, strokeWeight: st.strokeWeight },
        })
        marker.addListener('click', () => open(g, m, marker))
        byId.current.set(m.id, { marker, m }); things.current.push(marker); bounds.extend(marker.getPosition()!)
      }
      if (!bounds.isEmpty()) { map.current!.fitBounds(bounds, 48); g.maps.event.addListenerOnce(map.current!, 'idle', () => { if ((map.current!.getZoom() ?? 0) > 16) map.current!.setZoom(16) }) }
      setReady(true)
    }).catch((e) => !cancelled && setErr(e.message))
    return () => { cancelled = true; off() }
  }, [apiKey, markers])  // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const hit = focusId ? byId.current.get(focusId) : undefined
    if (hit && map.current && (window as any).google) { map.current.panTo(hit.marker.getPosition()!); map.current.setZoom(Math.max(map.current.getZoom() ?? 6, 15)); open((window as any).google, hit.m, hit.marker) }
  }, [focusId, ready])  // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="relative">
      <ErrorBox error={err} />
      <div ref={el} className="h-[420px] w-full overflow-hidden rounded-2xl border border-slate-200/80 bg-slate-100 shadow-card lg:h-[600px]" role="application" aria-label="Map of where entries were made" data-testid="google-map" />
      <ul className="pointer-events-none absolute bottom-3 left-3 hidden flex-wrap gap-x-4 gap-y-1 rounded-xl bg-white/95 px-3 py-2 text-xs text-slate-600 shadow-card ring-1 ring-black/5 sm:flex" aria-label="Map legend">
        {Object.entries(RAG_COLOR).map(([k, c]) => <li key={k}><span className="mr-1 inline-block h-3 w-3 rounded-full align-middle" style={{ background: c }} />{k}</li>)}
        <li>Hollow = poor or unknown GPS accuracy</li>
      </ul>
    </div>
  )
}

export default function MapPage() {
  const { path } = useAuth()
  const nav = useNavigate()
  const { data: branches } = useBranches()
  const [period, setPeriod] = useState<Period>('week')
  const [branch, setBranch] = useState('')
  const [focus, setFocus] = useState<string | null>(null)
  const { data, isLoading, error } = useQuery({
    queryKey: ['map', period, branch],
    queryFn: async () => (await api.get<MapData>('/map/entries', { params: { period, branch_id: branch || undefined } })).data,
    placeholderData: keepPreviousData,
  })
  const openEntry = (id: string) => nav(path(`entries/${id}`))
  return (
    <>
      <PageTitle subtitle="Where entries were made: the GPS fix recorded when Submit was pressed on the phone."
        actions={<>
          <Select aria-label="Branch" value={branch} onChange={(e) => setBranch(e.target.value)} className="w-auto">
            <option value="">All my branches</option>{branches?.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
          </Select>
          <Segmented label="Period" options={PERIODS} value={period} onChange={setPeriod} />
        </>}>
        Field map
      </PageTitle>
      <ErrorBox error={error ? errorMessage(error) : null} />
      {isLoading || !data ? (
        <div role="status" aria-label="Loading map"><Skeleton className="mb-4 h-12" /><Skeleton className="h-[420px] lg:h-[600px]" /></div>
      ) : (
        <>
          <p className="mb-4 flex items-start gap-2.5 rounded-xl bg-brand-50 px-4 py-3 text-sm text-brand-800" data-testid="map-summary">
            <Info size={16} className="mt-0.5 shrink-0" aria-hidden="true" />
            {data.capped && <span className="mb-1 block font-medium text-roof-700" role="status">The map shows the newest {data.limit.toLocaleString('en-IN')} of {data.total.toLocaleString('en-IN')} entries in this period: pick fewer days, a branch or an SO to see the rest.</span>}
            <span>{data.markers.length} of {data.capped ? data.shown : data.total} entries have a GPS position{data.without_location > 0 && <> · <strong>{data.without_location}</strong> without GPS are not on the map</>}. These are recorded positions, not live tracking.</span>
          </p>
          {MAP_KEY ? (
            <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_360px]">
              <FieldMap apiKey={MAP_KEY} markers={data.markers} focusId={focus} onOpen={openEntry} />
              <aside aria-label="Recorded locations" className="flex h-[420px] flex-col overflow-hidden rounded-2xl border border-slate-200/80 bg-white shadow-card lg:h-[600px]">
                <header className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
                  <h2 className="text-sm font-semibold text-brand-900">Recorded locations</h2>
                  <span className="rounded-full bg-brand-50 px-2 py-0.5 text-xs font-semibold text-brand-700">{data.markers.length}</span>
                </header>
                {data.markers.length === 0 ? <EmptyState icon={<MapPinOff size={20} />} title="No entries with a GPS position in this period." /> : (
                  <ul className="flex-1 divide-y divide-slate-100 overflow-y-auto">
                    {data.markers.map((m) => {
                      const cls = accuracyClass(m.accuracy_m)
                      return (
                        <li key={m.id} className={cx('px-4 py-3 transition', focus === m.id ? 'bg-brand-50/70' : 'hover:bg-slate-50')}>
                          <div className="flex items-start gap-3">
                            <Avatar name={m.so_name} size="sm" />
                            <div className="min-w-0 flex-1">
                              <div className="flex items-center justify-between gap-2"><Link className="truncate font-mono text-xs font-semibold text-brand-700 hover:underline" to={path(`entries/${m.id}`)}>{m.entry_code}</Link><RagBadge value={m.rag} /></div>
                              <p className="truncate text-sm text-slate-700">{m.person_name} · {m.so_name}</p>
                              <p className={cx('mt-0.5 text-xs', cls === 'poor' || cls === 'unknown' ? 'text-amber-700' : 'text-slate-500')}>{m.place_name ?? m.branch} · {ACCURACY_TEXT[cls]} · {fmtServer(m.submitted_at_device)}</p>
                              <Button variant="secondary" small className="mt-2" onClick={() => setFocus(m.id)}><MapPin size={13} aria-hidden="true" />Show on map</Button>
                            </div>
                          </div>
                        </li>
                      )
                    })}
                  </ul>
                )}
              </aside>
            </div>
          ) : (
            <>
              <div className="mb-4 flex items-start gap-3 rounded-2xl border border-gold-300/70 bg-gold-50 p-5">
                <TriangleAlert size={20} className="mt-0.5 shrink-0 text-gold-700" aria-hidden="true" />
                <div>
                  <h2 className="text-sm font-semibold text-brand-900">Google Maps is not set up yet</h2>
                  <p className="mt-1 text-sm text-slate-700" data-testid="map-key-missing">
                    Add a Google Maps <strong>browser key</strong> to show the map: put <code>VITE_GOOGLE_MAPS_API_KEY=your-key</code> in <code>admin-web/.env.local</code> and restart the web app (steps in <code>docs/google-maps-setup.md</code>). The locations are listed below in the meantime.
                  </p>
                </div>
              </div>
              <Card title={`Locations (${data.markers.length})`} flush>
                <Table head={['Entry', 'Person', 'Sales Officer', 'RAG', 'Place', 'Position', 'Made']}>
                  {data.markers.map((m) => (
                    <tr key={m.id}>
                      <Td className="whitespace-nowrap"><Link className="font-mono text-xs font-semibold text-brand-700 hover:underline" to={path(`entries/${m.id}`)}>{m.entry_code}</Link></Td>
                      <Td>{m.person_name}</Td><Td>{m.so_name}<div className="text-xs text-slate-500">{m.branch}</div></Td><Td><RagBadge value={m.rag} /></Td>
                      <Td>{m.place_name ?? '—'}</Td>
                      <Td><a className="font-medium text-brand-700 underline" target="_blank" rel="noreferrer noopener" href={`https://www.google.com/maps?q=${m.lat},${m.lng}`}>{m.lat.toFixed(5)}, {m.lng.toFixed(5)}</a>
                        <div className="text-xs text-slate-500">{m.accuracy_m != null ? `±${Math.round(m.accuracy_m)} m` : '—'} · {ACCURACY_TEXT[accuracyClass(m.accuracy_m)]}</div></Td>
                      <Td>{fmtServer(m.submitted_at_device)}</Td>
                    </tr>
                  ))}
                </Table>
                {data.markers.length === 0 && <EmptyState icon={<MapPinOff size={20} />} title="No entries with a GPS position in this period." />}
              </Card>
            </>
          )}
        </>
      )}
    </>
  )
}
