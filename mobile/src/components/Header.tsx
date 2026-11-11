import type { ReactNode } from 'react'
import { StyleSheet, View } from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'
import { useSession } from '@/lib/session'
import { useSyncStatus } from '@/lib/sync'
import { C, F } from '@/lib/theme'
import { Icon, T } from './ui'

/** Navy page header with the sync state, shared by the tabs. */
export function Header({ title, subtitle, children }: { title: string; subtitle?: string; children?: ReactNode }) {
  const insets = useSafeAreaInsets()
  const { offline } = useSession()
  const s = useSyncStatus()
  const text = s.running ? 'Sending…' : s.pending ? `${s.pending} waiting to send` : s.failed ? `${s.failed} need attention` : offline ? 'Offline' : 'All sent'
  const tone = s.failed ? C.roof200 : s.pending || offline ? C.gold400 : '#6EE7B7'
  return (
    <View style={[st.wrap, { paddingTop: insets.top + 14 }]}>
      <View style={st.top}>
        <View style={{ flex: 1 }}>
          {subtitle && <T style={st.sub}>{subtitle}</T>}
          <T style={st.title}>{title}</T>
        </View>
        <View style={st.sync} accessibilityLabel={`Sync: ${text}`}>
          <Icon name={s.running ? 'cloud-sync-outline' : s.pending || offline ? 'cloud-clock-outline' : s.failed ? 'cloud-alert' : 'cloud-check-outline'} size={16} color={tone} />
          <T style={[st.syncText, { color: tone }]}>{text}</T>
        </View>
      </View>
      {children}
    </View>
  )
}

const st = StyleSheet.create({
  wrap: { backgroundColor: C.navy800, paddingHorizontal: 20, paddingBottom: 20, borderBottomLeftRadius: 24, borderBottomRightRadius: 24 },
  top: { flexDirection: 'row', alignItems: 'flex-start', gap: 12 },
  sub: { fontFamily: F.medium, fontSize: 12, color: C.navy200, letterSpacing: 0.3 },
  title: { fontFamily: F.bold, fontSize: 22, color: C.white, marginTop: 2 },
  sync: { flexDirection: 'row', alignItems: 'center', gap: 5, backgroundColor: 'rgba(255,255,255,0.08)', paddingHorizontal: 10, paddingVertical: 5, borderRadius: 999 },
  syncText: { fontFamily: F.semibold, fontSize: 11 },
})
