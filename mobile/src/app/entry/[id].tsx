import { Redirect, useLocalSearchParams } from 'expo-router'
import { StatusBar } from 'expo-status-bar'
import { useCallback, useEffect, useState } from 'react'
import { Image, Linking, ScrollView, StyleSheet, View } from 'react-native'
import { Banner, Button, Card, Icon, Pill, RagBadge, Row, T } from '@/components/ui'
import { api } from '@/lib/api'
import { getEntry, type LocalEntry, type LocalPhoto, photosOf } from '@/lib/db'
import { categoryLabel } from '@/lib/rules'
import { useSession } from '@/lib/session'
import { runSync, useSyncStatus } from '@/lib/sync'
import { C, F } from '@/lib/theme'
import { type ServerDetail, STATE_PILL, statusText } from '@/lib/entryView'

const KV = ({ k, v }: { k: string; v?: string | null }) => (
  <View style={st.kv}>
    <T tone="small">{k}</T>
    <T style={{ marginTop: 2, fontFamily: F.medium, color: C.navy900 }}>{v || '—'}</T>
  </View>
)

const formatCurrency = (amt?: number | null) => {
  if (amt == null || isNaN(amt)) return null
  return '₹' + amt.toLocaleString('en-IN')
}

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
  useEffect(() => {
    if (serverId) api<ServerDetail>('GET', `/entries/${serverId}`).then(setServer).catch(() => {})
  }, [serverId])

  if (status !== 'signedIn' || !me) return <Redirect href="/login" />

  const body = local ? JSON.parse(local.body) : null
  const loc = body?.location ?? server?.location
  const pill = local ? STATE_PILL[local.state] : STATE_PILL.accepted

  const personName = local?.person_name ?? server?.person_name ?? '—'
  const phone = local?.phone ?? server?.phone ?? ''
  const entryCode = local?.server_code ?? server?.entry_code ?? local?.entry_code ?? '—'
  const category = local?.category ?? server?.category ?? ''
  const attempts = server?.attempts ?? []
  const connectedAttempt = attempts.slice().reverse().find((a) => a.outcome === 'Connected' && a.answers)
  const latestAttempt = attempts[attempts.length - 1]
  const answers = connectedAttempt?.answers ?? latestAttempt?.answers
  const leadCard = server?.lead_card
  const tcsId = leadCard?.lead_id ?? server?.tcs_id
  const loanReq = leadCard?.loan_requirement

  return (
    <ScrollView contentContainerStyle={{ padding: 16, gap: 14, paddingBottom: 40 }}>
      <StatusBar style="dark" />

      {/* Header Hero Card */}
      <Card style={{ gap: 8 }}>
        <Row style={{ justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <View style={{ flex: 1, marginRight: 8 }}>
            <T tone="mono" style={{ fontSize: 12 }}>{entryCode}</T>
            <T tone="title" style={{ marginTop: 2 }}>{personName}</T>
          </View>
          {server && <RagBadge value={server.rag} />}
        </Row>

        <T tone="small">
          {categoryLabel(category)} · Mobile {phone}
        </T>

        <Row style={{ flexWrap: 'wrap', gap: 6, marginTop: 4 }}>
          {pill && <Pill {...pill} />}
          {statusText(server ?? undefined) && <Pill text={statusText(server ?? undefined)!} />}
          {server?.customer_validated && <Pill text="Customer Validated" color={C.green700} bg={C.green50} icon="check-circle-outline" />}
          {server?.sankalp_success && <Pill text="Sankalp Success" color={C.gold700} bg={C.gold100} icon="trophy-outline" />}
        </Row>

        {!!phone && (
          <Button
            title={`Call Customer (${phone})`}
            icon="phone"
            variant="gold"
            onPress={() => Linking.openURL(`tel:${phone}`)}
            style={{ marginTop: 8 }}
          />
        )}
      </Card>

      {/* Local sync statuses */}
      {local?.state === 'failed' && (
        <Banner tone="error" icon="cloud-alert">
          The server refused this entry: {local.last_error}. Show it to your BM.
        </Banner>
      )}
      {local && local.state !== 'accepted' && local.state !== 'failed' && (
        <Banner tone="warn" icon="cloud-clock-outline">
          Saved on this phone. It is sent automatically when there is a connection{local.last_error ? ` (last try: ${local.last_error})` : ''}.
        </Banner>
      )}
      {local && local.state !== 'accepted' && (
        <Button title="Send now" icon="cloud-upload-outline" busy={sync.running} onPress={() => runSync(me.id, true).then(load)} />
      )}

      {/* Sales Officer Action Banner */}
      {server?.so_action && (
        <Banner tone="warn" icon="flag-outline">
          Action required: {server.so_action}{server.so_action_date ? ` (Due: ${server.so_action_date})` : ''}
        </Banner>
      )}

      {/* TCS Lead Handoff Card */}
      {(tcsId || loanReq != null) && (
        <Card style={{ gap: 6 }}>
          <Row style={{ justifyContent: 'space-between' }}>
            <T tone="h2">TCS Lead Details</T>
            <Pill text="Handoff" color={C.sky700} bg={C.sky50} icon="file-document-outline" />
          </Row>
          {tcsId && <KV k="TCS Lead ID" v={tcsId} />}
          {loanReq != null && <KV k="Loan Requirement" v={formatCurrency(loanReq)} />}
          {leadCard?.city && <KV k="Handling City / Branch" v={leadCard.city} />}
          {leadCard?.cibil_score != null && <KV k="CIBIL Score" v={String(leadCard.cibil_score)} />}
        </Card>
      )}

      {/* Call Centre Verification Card */}
      <Card style={{ gap: 6 }}>
        <Row style={{ justifyContent: 'space-between' }}>
          <T tone="h2">Call Centre Verification</T>
          {attempts.length > 0 && (
            <Pill
              text={`${attempts.length} attempt${attempts.length === 1 ? '' : 's'}`}
              color={C.navy700}
              bg={C.navy50}
            />
          )}
        </Row>

        {attempts.length === 0 ? (
          <T tone="small" style={{ marginTop: 4 }}>
            Not called yet. The call centre will connect with the customer in accordance with the daily run schedule.
          </T>
        ) : (
          <View style={{ marginTop: 4 }}>
            {latestAttempt && (
              <KV
                k="Last Call Outcome"
                v={`${latestAttempt.outcome}${latestAttempt.slot ? ` (${latestAttempt.slot})` : ''} · ${latestAttempt.call_date}`}
              />
            )}
            {answers ? (
              <>
                {answers.visit && <KV k="Visit Confirmed by Customer" v={answers.visit} />}
                {answers.loan_need && <KV k="Loan Requirement Stated" v={answers.loan_need} />}
                {answers.purpose && <KV k="Loan Purpose" v={answers.purpose} />}
                {answers.timeline && <KV k="Loan Timeline" v={answers.timeline} />}
                {answers.income && <KV k="Income / Employment" v={answers.income} />}
                {answers.documents && <KV k="Document Availability" v={answers.documents} />}
                {answers.remarks && <KV k="Telecaller Remarks" v={answers.remarks} />}
              </>
            ) : null}

            {/* Past Attempts log if multiple */}
            {attempts.length > 1 && (
              <View style={{ marginTop: 10, paddingTop: 10, borderTopWidth: 1, borderTopColor: C.line, gap: 6 }}>
                <T tone="label">Attempt History</T>
                {attempts.map((a, idx) => (
                  <Row key={a.id || idx} style={{ justifyContent: 'space-between' }}>
                    <T tone="small">{idx + 1}. {a.call_date} ({a.slot})</T>
                    <T tone="small" style={{ fontFamily: F.semibold, color: a.outcome === 'Connected' ? C.green700 : C.roof700 }}>
                      {a.outcome}
                    </T>
                  </Row>
                ))}
              </View>
            )}
          </View>
        )}
      </Card>

      {/* Field Work & What You Recorded Card */}
      <Card style={{ gap: 6 }}>
        <T tone="h2">Meeting Details</T>
        <KV k="Description" v={body?.description || server?.description} />
        {server?.cp_subtype_label && <KV k="CP sub-type" v={server.cp_subtype_label} />}
        {(body?.keka_photo_time || server?.keka_photo_time) && (
          <KV k="Keka photo time" v={(body?.keka_photo_time || server?.keka_photo_time)?.slice(0, 5)} />
        )}
        <KV
          k="Submit pressed"
          v={new Date(body?.submitted_at_device || server?.submitted_at_device || '').toLocaleString()}
        />
        <KV
          k="GPS at Submit"
          v={
            loc?.latitude != null && loc?.longitude != null
              ? `${loc.latitude.toFixed(5)}, ${loc.longitude.toFixed(5)}${loc.accuracy_m != null ? ` (±${Math.round(loc.accuracy_m)} m)` : ''}`
              : `No fix (${String(loc?.status || 'no fix').replace('_', ' ')})`
          }
        />
        {(server?.place_name || loc?.place_name) && <KV k="Place" v={server?.place_name || loc?.place_name} />}
        {local?.received_at && <KV k="Reached the server" v={new Date(local.received_at).toLocaleString()} />}
      </Card>

      {/* Photos Gallery */}
      {photos.length > 0 ? (
        <Card>
          <T tone="h2">Photos ({photos.length})</T>
          <ScrollView horizontal contentContainerStyle={{ gap: 10, paddingTop: 10 }}>
            {photos.map((p) => (
              <View key={p.id} style={{ width: 120, gap: 4 }}>
                <Image source={{ uri: p.path }} style={{ width: 120, height: 120, borderRadius: 12, backgroundColor: C.navy100 }} />
                <T tone="small">
                  {new Date(p.captured_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} · {p.latitude != null ? 'GPS' : 'no GPS'}
                  {p.uploaded ? ' · sent' : ''}
                </T>
              </View>
            ))}
          </ScrollView>
        </Card>
      ) : server?.photos && server.photos.length > 0 ? (
        <Card>
          <T tone="h2">Photos ({server.photos.length})</T>
          <ScrollView horizontal contentContainerStyle={{ gap: 10, paddingTop: 10 }}>
            {server.photos.map((p) => (
              <View key={p.photo_id} style={{ width: 120, gap: 4 }}>
                <Image
                  source={{ uri: p.url || p.thumb_url }}
                  style={{ width: 120, height: 120, borderRadius: 12, backgroundColor: C.navy100 }}
                />
                <T tone="small">
                  {p.photo_captured_at_device
                    ? new Date(p.photo_captured_at_device).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                    : 'Photo'}
                  {p.latitude != null ? ' · GPS' : ''}
                </T>
              </View>
            ))}
          </ScrollView>
        </Card>
      ) : null}
    </ScrollView>
  )
}

const st = StyleSheet.create({
  kv: { paddingVertical: 6, borderBottomWidth: 1, borderBottomColor: C.line },
})
