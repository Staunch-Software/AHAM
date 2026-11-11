import { Redirect } from 'expo-router'
import { Tabs } from 'expo-router/tabs'
import { useEffect } from 'react'
import { Icon, type IconName } from '@/components/ui'
import { registerBackgroundSync } from '@/lib/background'
import { useSession } from '@/lib/session'
import { startSyncTriggers, useSyncStatus } from '@/lib/sync'
import { C, F } from '@/lib/theme'

const tab = (icon: IconName) => ({ color, focused }: { color: unknown; focused: boolean }) => (
  <Icon name={focused ? icon : (`${icon}-outline` as IconName)} color={String(color)} size={24} />
)

export default function AppLayout() {
  const { status, me } = useSession()
  const sync = useSyncStatus()
  const ownerId = me?.id
  useEffect(() => {
    if (!ownerId) return
    registerBackgroundSync()
    return startSyncTriggers(ownerId)
  }, [ownerId])
  if (status !== 'signedIn' || !me) return <Redirect href="/login" />
  if (me.must_change_password) return <Redirect href="/change-password" />
  return (
    <Tabs screenOptions={{
      headerShown: false, tabBarActiveTintColor: C.navy700, tabBarInactiveTintColor: '#94A3B8',
      tabBarLabelStyle: { fontFamily: F.semibold, fontSize: 11 }, tabBarStyle: { height: 64, paddingTop: 6, paddingBottom: 8, borderTopColor: C.line },
      sceneStyle: { backgroundColor: C.page },
    }}>
      <Tabs.Screen name="home" options={{ title: 'Today', tabBarIcon: tab('view-dashboard') }} />
      <Tabs.Screen name="new" options={{ title: 'New entry', tabBarIcon: tab('plus-circle') }} />
      <Tabs.Screen name="entries" options={{ title: 'My entries', tabBarIcon: tab('clipboard-text'), tabBarBadge: sync.pending ? sync.pending : undefined }} />
      <Tabs.Screen name="account" options={{ title: 'Me', tabBarIcon: tab('account-circle') }} />
    </Tabs>
  )
}
