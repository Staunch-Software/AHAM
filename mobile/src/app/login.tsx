import { Redirect } from 'expo-router'
import { useRef, useState } from 'react'
import { Image, KeyboardAvoidingView, Platform, ScrollView, StyleSheet, View } from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'
import { ServerSetting } from '@/components/ServerSetting'
import { Banner, Button, Field, Icon, type IconName, type InputRef, T } from '@/components/ui'
import { loginMessage, useSession } from '@/lib/session'
import { C, F } from '@/lib/theme'

const POINTS: [IconName, string][] = [
  ['map-marker-check-outline', 'Time and place are those of the Submit press'],
  ['wifi-off', 'Works offline; entries send themselves later'],
  ['card-account-details-outline', 'Your Emp ID and branch come from HR'],
]

export default function Login() {
  const { status, me, login } = useSession()
  const insets = useSafeAreaInsets()
  const [id, setId] = useState('')
  const [pw, setPw] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const pwRef = useRef<InputRef>(null)
  if (status === 'signedIn' && me) return <Redirect href="/" />
  const submit = async () => {
    setError(null)
    if (!id.trim() || !pw) { setError('Enter your Emp ID and password'); return }
    setBusy(true)
    try { await login(id, pw) } catch (e) { setError(loginMessage(e)) } finally { setBusy(false) }
  }
  return (
    <KeyboardAvoidingView style={{ flex: 1, backgroundColor: C.white }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <ScrollView contentContainerStyle={{ flexGrow: 1 }} keyboardShouldPersistTaps="handled">
        <View style={[st.hero, { paddingTop: insets.top + 28 }]}>
          <View style={st.brand}>
            <View style={st.logo}><Image source={require('../../assets/images/aham-logo.jpg')} style={{ width: 52, height: 52 }} resizeMode="cover" /></View>
            <View>
              <T style={st.brandName}>AHAM Sankalp</T>
              <T style={st.brandTag}>SALES OFFICER APP</T>
            </View>
          </View>
          <T style={st.headline}>Every meeting, <T style={[st.headline, { color: C.gold400 }]}>on record</T>.</T>
          <View style={{ gap: 10, marginTop: 18 }}>
            {POINTS.map(([icon, text]) => (
              <View key={text} style={st.point}>
                <View style={st.pointIcon}><Icon name={icon} size={17} color={C.gold400} /></View>
                <T style={st.pointText}>{text}</T>
              </View>
            ))}
          </View>
        </View>
        <View style={st.form}>
          <T tone="title">Sign in</T>
          <T tone="small" style={{ marginTop: -8 }}>Use your Emp ID (for example AHFL01810) and password.</T>
          {error && <Banner tone="error" icon="alert-circle-outline">{error}</Banner>}
          <Field label="Emp ID" value={id} onChangeText={setId} autoCapitalize="characters" autoCorrect={false} placeholder="AHFL01810"
            returnKeyType="next" onSubmitEditing={() => pwRef.current?.focus()} testID="login-id" />
          <Field ref={pwRef} label="Password" value={pw} onChangeText={setPw} secureTextEntry returnKeyType="go" onSubmitEditing={submit} testID="login-password" />
          <Button title="Sign in" icon="login" busy={busy} onPress={submit} testID="login-submit" />
          <T tone="small" style={{ textAlign: 'center' }}>First time? HR gives you a temporary password; you choose your own next.</T>
          <ServerSetting />
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  )
}

const st = StyleSheet.create({
  hero: { backgroundColor: C.navy800, paddingHorizontal: 24, paddingBottom: 36, borderBottomLeftRadius: 28, borderBottomRightRadius: 28 },
  brand: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  logo: { width: 52, height: 52, borderRadius: 14, overflow: 'hidden', backgroundColor: C.white },
  brandName: { fontFamily: F.bold, fontSize: 18, color: C.white },
  brandTag: { fontFamily: F.semibold, fontSize: 10, letterSpacing: 1.4, color: C.gold400 },
  headline: { fontFamily: F.bold, fontSize: 30, lineHeight: 36, color: C.white, marginTop: 28 },
  point: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  pointIcon: { width: 30, height: 30, borderRadius: 9, backgroundColor: 'rgba(255,255,255,0.1)', alignItems: 'center', justifyContent: 'center' },
  pointText: { fontFamily: F.medium, fontSize: 13, color: C.navy100, flex: 1 },
  form: { padding: 24, gap: 16 },
})
