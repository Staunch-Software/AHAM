import { Redirect, useLocalSearchParams } from 'expo-router'
import { StatusBar } from 'expo-status-bar'
import { useCallback, useEffect, useState } from 'react'
import { Image, ScrollView, View } from 'react-native'
import { Banner, Button, Card, Pill, RagBadge, Row, T } from '@/components/ui'
import { api } from '@/lib/api'
import { getEntry, type LocalEntry, type LocalPhoto, photosOf } from '@/lib/db'
import { categoryLabel } from '@/lib/rules'
import { useSession } from '@/lib/session'
import { runSync, useSyncStatus } from '@/lib/sync'
import { C } from '@/lib/theme'
import { type ServerRow, STATE_PILL, statusText } from '@/lib/entryView'

interface ServerDetail extends ServerRow { attempts: unknown[]; lead_outcome: string | null; cp_subtype_label: string | null; place_name: string | null }

const KV = ({ k, v }: { k: string; v?: string | null }) => (
  <View style={{ paddingVertical: 6, borderBottomWidth: 1, borderBottomColor: C.line }}>
    <T tone="small">{k}</T>
    <T>{v || '—'}</T>
  </View>
)

/** One entry: what was saved on the phone, how it was delivered, and what the call centre made of it. */
export default function EntryScreen() {
  const { id } = useLocalSearchParams<{ id: string }>()
  const { status, me } = useSession()
  const sync = useSyncStatus()
  const [local, setLocal] = useState<LocalEntry | null>(null)
  const [photos, setPhotos] = useState<LocalPhoto[]>([])
  const [server, setServer] = useState<ServerDetail | null>(null)
  const serverId = id?.startsWith('s:') ? id.slice(2) : local?.server_id
  const load = useCallback(async () => {
    if (!id || id.startsWith('s:')) return
    setLocal(await getEntry(id))
    setPhotos(await photosOf(id))
  }, [id])
  useEffect(() => { load() }, [load, sync.lastRunAt])
  useEffect(() => { if (serverId) api<ServerDetail>('GET', `/entries/${serverId}`).then(setServer).catch(() => {}) }, [serverId])
  if (status !== 'signedIn' || !me) return <Redirect href="/login" />
  const body = local ? JSON.parse(local.body) : null
  const loc = body?.location
  const pill = local ? STATE_PILL[local.state] : null
  return (
    <ScrollView contentContainerStyle={{ padding: 16, gap: 14, paddingBottom: 40 }}>
      <StatusBar style="dark" />
      <Card style={{ gap: 6 }}>
        <T tone="mono">{local?.server_code ?? server?.entry_code ?? local?.entry_code}</T>
        <T tone="title">{local?.person_name ?? server?.person_name}</T>
        <T tone="small">{categoryLabel(local?.category ?? server?.category ?? '')} · Mobile {local?.phone ?? server?.phone}</T>
        <Row style={{ flexWrap: 'wrap', marginTop: 4 }}>
          {pill && <Pill {...pill} />}
          {server && <RagBadge value={server.rag} />}
          {statusText(server ?? undefined) && <Pill text={statusText(server ?? undefined)!} />}
        </Row>
      </Card>

      {local?.state === 'failed' && <Banner tone="error" icon="cloud-alert">The server refused this entry: {local.last_error}. Show it to your BM.</Banner>}
      {local && local.state !== 'accepted' && local.state !== 'failed' && (
        <Banner tone="warn" icon="cloud-clock-outline">Saved on this phone. It is sent automatically when there is a connection{local.last_error ? ` (last try: ${local.last_error})` : ''}.</Banner>
      )}
      {local && local.state !== 'accepted' && <Button title="Send now" icon="cloud-upload-outline" busy={sync.running} onPress={() => runSync(me.id, true).then(load)} />}

      {server?.so_action && <Banner tone="info" icon="flag-outline">Next: {server.so_action}{server.so_action_date ? ` on ${server.so_action_date}` : ''}</Banner>}

      {body && (
        <Card>
          <T tone="h2">What you recorded</T>
          <KV k="Description" v={body.description} />
          {server?.cp_subtype_label && <KV k="CP sub-type" v={server.cp_subtype_label} />}
          <KV k="Keka photo time" v={body.keka_photo_time?.slice(0, 5)} />
          <KV k="Submit pressed" v={new Date(body.submitted_at_device).toLocaleString()} />
          <KV k="GPS at Submit" v={loc?.status === 'obtained' ? `${loc.latitude.toFixed(5)}, ${loc.longitude.toFixed(5)} (±${Math.round(loc.accuracy_m ?? 0)} m)` : `No fix (${String(loc?.status).replace('_', ' ')})`} />
          {server?.place_name && <KV k="Place" v={server.place_name} />}
          {local?.received_at && <KV k="Reached the server" v={new Date(local.received_at).toLocaleString()} />}
        </Card>
      )}
      {photos.length > 0 && (
        <Card>
          <T tone="h2">Photos</T>
          <ScrollView horizontal contentContainerStyle={{ gap: 10, paddingTop: 10 }}>
            {photos.map((p) => (
              <View key={p.id} style={{ width: 120, gap: 4 }}>
                <Image source={{ uri: p.path }} style={{ width: 120, height: 120, borderRadius: 12, backgroundColor: C.navy100 }} />
                <T tone="small">{new Date(p.captured_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} · {p.latitude != null ? 'GPS' : 'no GPS'}{p.uploaded ? ' · sent' : ''}</T>
              </View>
            ))}
          </ScrollView>
        </Card>
      )}
    </ScrollView>
  )
}
