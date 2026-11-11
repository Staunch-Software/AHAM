import * as Crypto from 'expo-crypto'
import { router } from 'expo-router'
import { useCallback, useEffect, useRef, useState } from 'react'
import { Alert, Image, KeyboardAvoidingView, Modal, Platform, Pressable, ScrollView, StyleSheet, View } from 'react-native'
import { Header } from '@/components/Header'
import { Banner, Button, Card, Chip, Field, Icon, type IconName, Pill, Row, T } from '@/components/ui'
import { api, lastServerContact } from '@/lib/api'
import { GPS_TIMEOUT_MS, MAX_PHOTOS } from '@/lib/config'
import { kvGet, kvSet, saveEntry } from '@/lib/db'
import { type Fix, getFix } from '@/lib/location'
import { CameraDenied, deletePhotoFile, type DraftPhoto, takePhoto } from '@/lib/photos'
import { useCached } from '@/lib/remote'
import { CATEGORIES, type CategoryKey, cleanPhone, entryCode, istDate, kekaTime, phoneProblem } from '@/lib/rules'
import { useSession } from '@/lib/session'
import { runSync } from '@/lib/sync'
import { C, F } from '@/lib/theme'

const ICONS: Record<CategoryKey, IconName> = {
  lead: 'home-plus-outline', prospect: 'account-clock-outline', dsa_connector: 'handshake-outline',
  contact_point: 'storefront-outline', existing_customer: 'account-check-outline', existing_applicant: 'file-document-outline',
}

interface Draft { category: CategoryKey | null; cpSubtype: string | null; name: string; phone: string; description: string; keka: string; photos: DraftPhoto[] }
const EMPTY: Draft = { category: null, cpSubtype: null, name: '', phone: '', description: '', keka: '', photos: [] }

interface Saved { code: string; localId: string; fix: Fix; sent: boolean | null }

export default function NewEntry() {
  const { me } = useSession()
  const draftKey = `draft:${me?.id}`
  const [d, setD] = useState<Draft>(EMPTY)
  const [touched, setTouched] = useState(false)
  const [saving, setSaving] = useState(false)
  const [snapping, setSnapping] = useState(false)
  const [saved, setSaved] = useState<Saved | null>(null)
  const loaded = useRef(false)
  const subtypes = useCached<{ id: string; label: string }[]>('cp_subtypes', '/cp-subtypes/active')

  // The form survives the app being closed: the draft is kept on the phone (debounced).
  useEffect(() => { kvGet<Draft>(draftKey).then((v) => { if (v) setD({ ...EMPTY, ...v }) }).finally(() => { loaded.current = true }) }, [draftKey])
  useEffect(() => {
    if (!loaded.current) return
    const t = setTimeout(() => { kvSet(draftKey, d).catch(() => {}) }, 500)
    return () => clearTimeout(t)
  }, [d, draftKey])

  const set = <K extends keyof Draft>(k: K, v: Draft[K]) => setD((x) => ({ ...x, [k]: v }))
  // A customer who is already a converted lead (TCS lead ID or login) is not entered again: checked here while
  // online, and again by the server when the entry is sent (an offline entry is refused then, with the reason).
  const [alreadyLead, setAlreadyLead] = useState<string | null>(null)
  const typedPhone = cleanPhone(d.phone)
  const phoneOk = !phoneProblem(d.phone)
  useEffect(() => {
    setAlreadyLead(null)
    if (!phoneOk) return
    let live = true
    const t = setTimeout(() => {
      api<{ lead: { message: string } | null }>('GET', `/entries/check-phone?phone=${encodeURIComponent(typedPhone)}`)
        .then((r) => { if (live) setAlreadyLead(r.lead?.message ?? null) })
        .catch(() => {})  // offline or no answer: the server checks when the entry is sent
    }, 400)
    return () => { live = false; clearTimeout(t) }
  }, [typedPhone, phoneOk])
  let kekaError: string | null = null
  try { kekaTime(d.keka) } catch (e) { kekaError = (e as Error).message }
  const errors = {
    category: !d.category ? 'Choose who you met' : null,
    cpSubtype: d.category === 'contact_point' && !d.cpSubtype ? 'Choose the CP sub-type' : null,
    name: !d.name.trim() ? 'Enter the name of the person met' : null,
    phone: phoneProblem(d.phone) ?? alreadyLead,
    description: !d.description.trim() ? 'Write a short description of the meeting' : null,
    keka: kekaError,
  }
  const valid = Object.values(errors).every((e) => !e)
  const show = (k: keyof typeof errors) => (touched ? errors[k] : null)
  const cleaned = cleanPhone(d.phone)

  const addPhoto = async () => {
    setSnapping(true)
    try {
      const p = await takePhoto()
      if (p) set('photos', [...d.photos, p])
    } catch (e) {
      Alert.alert('Camera', e instanceof CameraDenied ? e.message : 'The photo could not be saved. Try again.')
    } finally { setSnapping(false) }
  }
  const removePhoto = (p: DraftPhoto) => { deletePhotoFile(p.path); set('photos', d.photos.filter((x) => x.id !== p.id)) }

  const submit = useCallback(async () => {
    setTouched(true)
    if (!valid || !me || !d.category) return
    // The entry's time is this moment: stamped before anything else, never the time it reaches the server.
    const submittedAt = new Date()
    setSaving(true)
    try {
      const fix = await getFix(GPS_TIMEOUT_MS)  // at most 8 s; without a fix the entry is saved anyway
      const localId = Crypto.randomUUID()
      const code = entryCode(me.employee_code, submittedAt)
      const lastContact = await lastServerContact()
      const body = JSON.stringify({
        idempotency_key: Crypto.randomUUID(), client_entry_id: localId, category: d.category,
        cp_subtype_id: d.category === 'contact_point' ? d.cpSubtype : null,
        person_name: d.name.trim(), phone: d.phone.trim(), description: d.description.trim(), keka_photo_time: kekaTime(d.keka),
        photo_ids: d.photos.map((p) => p.id), submitted_at_device: submittedAt.toISOString(), device_tz_offset_min: -submittedAt.getTimezoneOffset(),
        device_clock_at_last_contact: lastContact,
        location: { latitude: fix.latitude, longitude: fix.longitude, accuracy_m: fix.accuracy_m, fix_at_device: fix.fix_at, status: fix.status },
      })
      await saveEntry({
        local_id: localId, owner_id: me.id, idempotency_key: JSON.parse(body).idempotency_key, entry_code: code, body,
        person_name: d.name.trim(), phone: cleaned, category: d.category, submitted_at: submittedAt.toISOString(),
        entry_day: istDate(submittedAt), created_at: Date.now(),
      }, d.photos, draftKey)
      setSaved({ code, localId, fix, sent: null })
      setD(EMPTY)
      setTouched(false)
      const report = await runSync(me.id)
      setSaved((s) => (s && s.localId === localId ? { ...s, sent: !!report && report.accepted > 0 && !report.stopped } : s))
    } catch (e) {
      Alert.alert('Not saved', (e as Error)?.message ?? 'The entry could not be saved on this phone.')
    } finally { setSaving(false) }
  }, [valid, me, d, cleaned, draftKey])

  return (
    <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <Header subtitle="One entry per person met" title="New entry" />
      <ScrollView contentContainerStyle={{ padding: 16, gap: 14, paddingBottom: 40 }} keyboardShouldPersistTaps="handled">
        <Card>
          <T tone="h2">Who did you meet?</T>
          <View style={st.chips} accessibilityRole="radiogroup">
            {CATEGORIES.map((c) => <Chip key={c.key} label={c.label} hint={c.hint} icon={ICONS[c.key]} selected={d.category === c.key}
              onPress={() => setD((x) => ({ ...x, category: c.key, cpSubtype: c.key === 'contact_point' ? x.cpSubtype : null }))} />)}
          </View>
          {show('category') && <T tone="small" style={st.err}>{errors.category}</T>}
          {d.category === 'contact_point' && (
            <View style={{ marginTop: 14 }}>
              <T tone="label">CP sub-type</T>
              <View style={[st.chips, { marginTop: 8 }]}>
                {(subtypes.data ?? []).map((s) => <Chip key={s.id} label={s.label} selected={d.cpSubtype === s.id} onPress={() => set('cpSubtype', s.id)} />)}
              </View>
              {!subtypes.data?.length && <T tone="small" style={st.err}>The list downloads once you are online.</T>}
              {show('cpSubtype') && <T tone="small" style={st.err}>{errors.cpSubtype}</T>}
            </View>
          )}
        </Card>

        <Card style={{ gap: 14 }}>
          <Field label="Name of person met" value={d.name} onChangeText={(t) => set('name', t)} autoCapitalize="words" error={show('name')} testID="f-name" />
          <Field label="Mobile (WhatsApp) number" value={d.phone} onChangeText={(t) => set('phone', t)} keyboardType="phone-pad" maxLength={17}
            error={d.phone.length >= 10 || touched ? errors.phone : null} testID="f-phone"
            hint={!errors.phone ? `Saved as ${cleaned.replace(/(\d{5})(\d{5})/, '$1 $2')}` : 'Only Indian mobile numbers (10 digits, starting 6-9)'}
            right={!errors.phone ? <Icon name="check-circle" color={C.green600} /> : null} />
          <Field label="Short description of the meeting" value={d.description} onChangeText={(t) => set('description', t)} multiline
            maxLength={2000} error={show('description')} testID="f-desc" placeholder="What was discussed, what they need" />
          <Field label="Keka photo time (optional)" value={d.keka} onChangeText={(t) => set('keka', t.replace(/[^0-9:]/g, ''))} keyboardType="numbers-and-punctuation"
            maxLength={5} placeholder="HH:MM" error={d.keka ? kekaError : null} hint="When your Keka attendance photo was taken" />
        </Card>

        <Card>
          <Row style={{ justifyContent: 'space-between' }}>
            <T tone="h2">Photos</T>
            <T tone="small">{d.photos.length} / {MAX_PHOTOS}</T>
          </Row>
          <T tone="small" style={{ marginTop: 4 }}>Each photo keeps its own time and GPS position.</T>
          <ScrollView horizontal contentContainerStyle={{ gap: 10, paddingVertical: 12 }} showsHorizontalScrollIndicator={false}>
            {d.photos.map((p) => (
              <View key={p.id} style={st.thumb}>
                <Image source={{ uri: p.path }} style={st.thumbImg} />
                <Pressable onPress={() => removePhoto(p)} style={st.remove} accessibilityLabel="Remove photo" hitSlop={8}><Icon name="close" size={16} color={C.white} /></Pressable>
                <View style={st.thumbMeta}>
                  <Icon name={p.latitude != null ? 'crosshairs-gps' : 'crosshairs-question'} size={12} color={C.white} />
                  <T style={st.thumbText}>{new Date(p.captured_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</T>
                </View>
              </View>
            ))}
            {d.photos.length < MAX_PHOTOS && (
              <Pressable onPress={addPhoto} disabled={snapping} style={st.addPhoto} accessibilityRole="button" accessibilityLabel="Take a photo">
                <Icon name="camera-plus-outline" size={28} />
                <T tone="small" style={{ color: C.navy700, fontFamily: F.semibold }}>{snapping ? 'Saving…' : 'Take photo'}</T>
              </Pressable>
            )}
          </ScrollView>
        </Card>

        {touched && !valid && <Banner tone="error" icon="alert-circle-outline">Fix the fields marked in red.</Banner>}
        <Button title={saving ? 'Saving… (getting GPS)' : 'Submit entry'} icon="send" busy={saving} onPress={submit} testID="f-submit" />
        <T tone="small" style={{ textAlign: 'center' }}>The time and place recorded are those of this Submit press, even if you are offline now.</T>
      </ScrollView>

      <Modal visible={!!saved} transparent animationType="fade" onRequestClose={() => setSaved(null)}>
        <View style={st.backdrop}>
          <View style={st.sheet}>
            <View style={st.okIcon}><Icon name="check-bold" size={30} color={C.green600} /></View>
            <T tone="title" style={{ textAlign: 'center' }}>Entry saved</T>
            <T tone="small" style={{ textAlign: 'center' }}>Entry ID</T>
            <T style={st.code} selectable testID="saved-code">{saved?.code}</T>
            <View style={{ alignItems: 'center', gap: 6 }}>
              {saved?.sent === null && <Pill text="Sending…" icon="cloud-upload-outline" color={C.navy700} bg={C.navy50} />}
              {saved?.sent === true && <Pill text="Sent to the server" icon="cloud-check-outline" color={C.green700} bg={C.green50} />}
              {saved?.sent === false && <Pill text="Saved on this phone · sends automatically" icon="cloud-clock-outline" color={C.gold700} bg={C.gold100} />}
              <Pill text={saved?.fix.status === 'obtained' ? `GPS ±${Math.round(saved.fix.accuracy_m ?? 0)} m` : `No GPS (${saved?.fix.status.replace('_', ' ')})`}
                icon={saved?.fix.status === 'obtained' ? 'crosshairs-gps' : 'crosshairs-off'} />
            </View>
            <Button title="Add another" icon="plus" onPress={() => setSaved(null)} testID="saved-another" />
            <Button title="Done" variant="secondary" onPress={() => { setSaved(null); router.replace('/home') }} />
          </View>
        </View>
      </Modal>
    </KeyboardAvoidingView>
  )
}

const st = StyleSheet.create({
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 12 },
  err: { color: C.roof700, marginTop: 6 },
  thumb: { width: 96, height: 96, borderRadius: 12, overflow: 'hidden', backgroundColor: C.navy100 },
  thumbImg: { width: 96, height: 96 },
  remove: { position: 'absolute', top: 4, right: 4, width: 24, height: 24, borderRadius: 12, backgroundColor: 'rgba(15,23,42,0.6)', alignItems: 'center', justifyContent: 'center' },
  thumbMeta: { position: 'absolute', left: 0, right: 0, bottom: 0, flexDirection: 'row', alignItems: 'center', gap: 4, padding: 4, backgroundColor: 'rgba(15,23,42,0.55)' },
  thumbText: { fontFamily: F.semibold, fontSize: 10, color: C.white },
  addPhoto: { width: 96, height: 96, borderRadius: 12, borderWidth: 1.5, borderStyle: 'dashed', borderColor: C.navy200, alignItems: 'center', justifyContent: 'center', gap: 4, backgroundColor: C.navy50 },
  backdrop: { flex: 1, backgroundColor: 'rgba(23,21,58,0.55)', justifyContent: 'flex-end' },
  sheet: { backgroundColor: C.white, borderTopLeftRadius: 28, borderTopRightRadius: 28, padding: 24, paddingBottom: 36, gap: 12 },
  okIcon: { alignSelf: 'center', width: 60, height: 60, borderRadius: 30, backgroundColor: C.green50, alignItems: 'center', justifyContent: 'center' },
  code: { fontFamily: F.bold, fontSize: 18, color: C.navy700, textAlign: 'center', letterSpacing: 0.5 },
})
