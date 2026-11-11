import Constants from 'expo-constants'
import { Alert, ScrollView, View } from 'react-native'
import { Header } from '@/components/Header'
import { ServerSetting } from '@/components/ServerSetting'
import { Banner, Button, Card, Row, T } from '@/components/ui'
import { useSession } from '@/lib/session'
import { runSync, useSyncStatus } from '@/lib/sync'
import { C } from '@/lib/theme'

const Line = ({ k, v }: { k: string; v?: string | null }) => (
  <Row style={{ justifyContent: 'space-between', paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: C.line }}>
    <T tone="label">{k}</T><T style={{ flexShrink: 1, textAlign: 'right' }}>{v || '—'}</T>
  </Row>
)

export default function Account() {
  const { me, logout, offline } = useSession()
  const sync = useSyncStatus()
  if (!me) return null
  const signOut = () => {
    const pending = sync.pending + sync.failed
    Alert.alert('Sign out?', pending
      ? `${pending} entr${pending === 1 ? 'y is' : 'ies are'} still on this phone. They stay here and are sent when you sign in again.`
      : 'You can sign in again with your Emp ID.', [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Sign out', style: 'destructive', onPress: () => { logout() } },
    ])
  }
  return (
    <View style={{ flex: 1 }}>
      <Header subtitle={me.role_label} title={me.full_name} />
      <ScrollView contentContainerStyle={{ padding: 16, gap: 14, paddingBottom: 32 }}>
        <Card>
          <T tone="h2">From the HR roster</T>
          <Line k="Emp ID" v={me.employee_code} />
          <Line k="Designation" v={me.designation} />
          <Line k="Branch" v={me.branch_name} />
          <Line k="Cluster" v={me.cluster_name} />
          <Line k="Region" v={me.region_name} />
          <Line k="Spoke" v={me.spoke} />
          <T tone="small" style={{ marginTop: 8 }}>Wrong? Ask HR to correct the roster: your entries take the branch from here.</T>
        </Card>
        <Card style={{ gap: 10 }}>
          <T tone="h2">Sending entries</T>
          <Line k="Waiting to send" v={String(sync.pending)} />
          <Line k="Need attention" v={String(sync.failed)} />
          <Line k="Last sync" v={sync.lastRunAt ? new Date(sync.lastRunAt).toLocaleString() : 'Not yet'} />
          {sync.error && <Banner tone="warn" icon="cloud-alert">{sync.error}</Banner>}
          {offline && <Banner tone="warn" icon="wifi-off">Offline: entries wait on this phone.</Banner>}
          <Button title="Sync now" icon="cloud-sync-outline" variant="secondary" busy={sync.running} onPress={() => runSync(me.id, true)} />
        </Card>
        <Card style={{ gap: 10 }}>
          <Line k="App version" v={Constants.expoConfig?.version} />
          <ServerSetting onChanged={() => runSync(me.id, true)} />
        </Card>
        <Button title="Sign out" icon="logout" variant="danger" onPress={signOut} />
      </ScrollView>
    </View>
  )
}
