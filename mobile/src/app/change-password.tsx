import { Redirect } from 'expo-router'
import { StatusBar } from 'expo-status-bar'
import { useState } from 'react'
import { ScrollView, View } from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'
import { Banner, Button, Field, Icon, T } from '@/components/ui'
import { loginMessage, useSession } from '@/lib/session'
import { C } from '@/lib/theme'

/** Shown while the account still has the temporary password HR issued. */
export default function ChangePassword() {
  const { status, me, changePassword, logout } = useSession()
  const insets = useSafeAreaInsets()
  const [v, setV] = useState({ current: '', next: '', again: '' })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  if (status !== 'signedIn' || !me) return <Redirect href="/login" />
  if (!me.must_change_password) return <Redirect href="/" />
  const submit = async () => {
    setError(null)
    if (v.next.length < 8) return setError('The new password needs at least 8 characters')
    if (v.next !== v.again) return setError('The two new passwords differ')
    setBusy(true)
    try { await changePassword(v.current, v.next) } catch (e) { setError(loginMessage(e)) } finally { setBusy(false) }
  }
  return (
    <ScrollView contentContainerStyle={{ padding: 24, paddingTop: insets.top + 32, gap: 16 }} keyboardShouldPersistTaps="handled">
      <StatusBar style="dark" />
      <View style={{ width: 52, height: 52, borderRadius: 16, backgroundColor: C.gold100, alignItems: 'center', justifyContent: 'center' }}>
        <Icon name="key-variant" size={26} color={C.gold700} />
      </View>
      <T tone="title">Choose your own password</T>
      <T>Welcome, {me.full_name}. Replace the temporary password HR gave you.</T>
      {error && <Banner tone="error" icon="alert-circle-outline">{error}</Banner>}
      <Field label="Temporary password" secureTextEntry value={v.current} onChangeText={(t) => setV({ ...v, current: t })} />
      <Field label="New password" secureTextEntry value={v.next} onChangeText={(t) => setV({ ...v, next: t })} hint="At least 8 characters" />
      <Field label="New password again" secureTextEntry value={v.again} onChangeText={(t) => setV({ ...v, again: t })} />
      <Button title="Save and continue" busy={busy} onPress={submit} />
      <Button title="Sign out" variant="ghost" onPress={logout} />
    </ScrollView>
  )
}
