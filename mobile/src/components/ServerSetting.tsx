import { useEffect, useState } from 'react'
import { Pressable, View } from 'react-native'
import { Banner, Button, Field, Row, T } from '@/components/ui'
import { serverUrl, setServer } from '@/lib/api'
import { BUILT_IN_SERVER, SERVER_EDITABLE } from '@/lib/config'
import { C, F } from '@/lib/theme'

/**
 * The server this phone talks to. On a build for a PC on the Wi-Fi the PC's address can change from day to day, so
 * it can be typed here (checked before it is used); entries waiting on the phone are kept and go to that address.
 */
export function ServerSetting({ onChanged }: { onChanged?: (url: string) => void }) {
  const [current, setCurrent] = useState<string | null>(null)
  const [editing, setEditing] = useState(false)
  const [value, setValue] = useState('')
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState<{ tone: 'error' | 'ok'; text: string } | null>(null)
  useEffect(() => { serverUrl().then(setCurrent).catch(() => setCurrent(BUILT_IN_SERVER)) }, [])

  const open = () => { setValue(current?.replace(/^http:\/\//, '').replace(/:8000$/, '') ?? ''); setMsg(null); setEditing(true) }
  const save = async () => {
    setBusy(true)
    setMsg(null)
    try {
      const url = await setServer(value)
      setCurrent(url)
      setEditing(false)
      setMsg({ tone: 'ok', text: `Connected to ${url}` })
      onChanged?.(url)
    } catch (e) {
      setMsg({ tone: 'error', text: (e as Error).message })
    } finally {
      setBusy(false)
    }
  }

  if (!editing) {
    return (
      <View style={{ gap: 8 }}>
        <Row style={{ justifyContent: 'center', flexWrap: 'wrap', gap: 6 }}>
          <T tone="small" style={{ color: '#94A3B8' }} testID="server-current">Server: {current ?? '…'}</T>
          {SERVER_EDITABLE && (
            <Pressable onPress={open} accessibilityRole="button" hitSlop={10} testID="server-change">
              <T tone="small" style={{ color: C.navy700, fontFamily: F.semibold }}>Change</T>
            </Pressable>
          )}
        </Row>
        {msg && <Banner tone={msg.tone} icon={msg.tone === 'ok' ? 'check-circle-outline' : 'alert-circle-outline'}>{msg.text}</Banner>}
      </View>
    )
  }
  return (
    <View style={{ gap: 12 }}>
      <Field label="Server (the PC’s address)" value={value} onChangeText={setValue} autoCapitalize="none" autoCorrect={false}
        keyboardType="url" placeholder="192.168.1.20" returnKeyType="go" onSubmitEditing={save} testID="server-input"
        hint={`On the PC: ipconfig → Wi-Fi → IPv4 address. Port 8000 is added. Leave blank for the built-in ${BUILT_IN_SERVER}.`} />
      {msg && <Banner tone={msg.tone} icon="alert-circle-outline">{msg.text}</Banner>}
      <Row style={{ gap: 10 }}>
        <Button title="Check and use" icon="lan-connect" busy={busy} onPress={save} style={{ flex: 1 }} testID="server-save" />
        <Button title="Cancel" variant="secondary" onPress={() => { setEditing(false); setMsg(null) }} style={{ flex: 1 }} />
      </Row>
    </View>
  )
}
