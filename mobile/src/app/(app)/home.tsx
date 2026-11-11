import { router, useFocusEffect } from 'expo-router'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Pressable, RefreshControl, ScrollView, StyleSheet, View } from 'react-native'
import { Header } from '@/components/Header'
import { Banner, Button, Card, Icon, Progress, RagBadge, Row, T } from '@/components/ui'
import { type DayCount, localDayCounts } from '@/lib/db'
import { useCached } from '@/lib/remote'
import { addDaysIso, countDate, istDate, LEAD_CATEGORIES } from '@/lib/rules'
import { useSession } from '@/lib/session'
import { runSync, useSyncStatus } from '@/lib/sync'
import { C, F } from '@/lib/theme'

interface Summary {
  today: string; entries_today: number; lead_prospect_today: number; entry_target: number; lead_target: number
  rag_last_30_days: Record<string, number>
  correct_number_window_days?: number
  holidays?: string[]
  correct_number: { id: string; entry_code: string; person_name: string; phone: string; until: string | null; status: string | null }[]
}

const greet = () => { const h = new Date().getHours(); return h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening' }

export default function Home() {
  const { me, offline } = useSession()
  const sync = useSyncStatus()
  const summary = useCached<Summary>(me ? `summary:${me.id}` : null, '/me/summary')
  const [rows, setRows] = useState<DayCount[]>([])
  const today = istDate(new Date())
  const loadLocal = useCallback(() => {
    if (!me) return
    localDayCounts(me.id, addDaysIso(today, -14)).then(setRows).catch(() => {})
  }, [me, today])
  useFocusEffect(loadLocal)
  const { refresh } = summary
  useEffect(() => { if (sync.lastRunAt) { loadLocal(); refresh() } }, [sync.lastRunAt, loadLocal, refresh])
  if (!me) return null
  // Everything counts on its count date (4.4): Sunday and holiday entries count on the next working day. With the
  // server's numbers for today (all phones), add what is still waiting on this phone; offline, count this phone.
  const holidays = useMemo(() => new Set(summary.data?.holidays ?? []), [summary.data])
  const countsToday = (unsentOnly: boolean) => rows.filter((r) => (!unsentOnly || r.unsent) && countDate(r.entry_day, holidays) === today)
  const sum = (rs: DayCount[], leadsOnly = false) => rs.filter((r) => !leadsOnly || LEAD_CATEGORIES.has(r.category)).reduce((a, r) => a + r.n, 0)
  const server = summary.data && summary.data.today === today ? summary.data : null
  const total = server ? server.entries_today + sum(countsToday(true)) : sum(countsToday(false))
  const leads = server ? server.lead_prospect_today + sum(countsToday(true), true) : sum(countsToday(false), true)
  const countsOn = countDate(today, holidays)
  const madeToday = sum(rows.filter((r) => r.entry_day === today))
  const fixDays = summary.data?.correct_number_window_days ?? 15
  const target = summary.data?.entry_target ?? 10
  const leadTarget = summary.data?.lead_target ?? 5
  const rag = summary.data?.rag_last_30_days ?? {}
  const onRefresh = async () => { loadLocal(); await Promise.all([summary.refresh(), runSync(me.id)]); loadLocal() }
  return (
    <View style={{ flex: 1 }}>
      <Header subtitle={`${greet()},`} title={me.full_name}>
        <T style={st.meta}>{me.employee_code} · {me.designation ?? me.role_label} · {me.branch_name ?? 'No branch'}{me.region_name ? ` · ${me.region_name}` : ''}</T>
      </Header>
      <ScrollView contentContainerStyle={{ padding: 16, gap: 14, paddingBottom: 32 }}
        refreshControl={<RefreshControl refreshing={sync.running} onRefresh={onRefresh} tintColor={C.navy700} />}>
        {offline && <Banner tone="warn" icon="wifi-off">You are offline. Keep making entries: they are saved on this phone and sent when the signal returns.</Banner>}
        <Card>
          <Row style={{ justifyContent: 'space-between' }}>
            <T tone="h2">Today</T>
            <T tone="small">{today}</T>
          </Row>
          <View style={st.bigRow}>
            <T style={st.big} testID="today-count">{total}</T>
            <T style={st.of}>/ {target} entries</T>
          </View>
          <Progress value={total} max={target} color={total >= target ? C.green600 : C.navy700} />
          <Row style={{ marginTop: 14, justifyContent: 'space-between' }}>
            <T tone="label">Lead / Prospect</T>
            <T style={{ fontFamily: F.semibold, color: C.navy900 }}>{leads} / {leadTarget}</T>
          </Row>
          <View style={{ marginTop: 6 }}><Progress value={leads} max={leadTarget} color={C.gold500} /></View>
          {countsOn !== today && (
            <T tone="small" style={{ marginTop: 10 }} testID="counts-on">
              Today is a Sunday or a holiday: the {madeToday} {madeToday === 1 ? 'entry' : 'entries'} made today count on {new Date(`${countsOn}T00:00:00Z`).toLocaleDateString([], { weekday: 'short', day: 'numeric', month: 'short', timeZone: 'UTC' })}.
            </T>
          )}
          {total >= target && <Banner tone="ok" icon="check-decagram">Target reached for today. Well done!</Banner>}
        </Card>

        <Button title="New entry" icon="plus" variant="gold" onPress={() => router.push('/new')} testID="home-new" />

        {!!summary.data?.correct_number.length && (
          <Card>
            <Row><Icon name="phone-alert-outline" color={C.roof500} /><T tone="h2">Numbers to correct</T></Row>
            <T tone="small" style={{ marginTop: 4 }}>The call centre could not reach these people. Give the right number to your BM within {fixDays} days of the entry.</T>
            <View style={{ marginTop: 10, gap: 8 }}>
              {summary.data.correct_number.map((c) => (
                <View key={c.id} style={st.fix}>
                  <View style={{ flex: 1 }}>
                    <T style={{ fontFamily: F.semibold }}>{c.person_name} · Mobile {c.phone}</T>
                    <T tone="small">{c.entry_code}{c.until ? ` · until ${c.until}` : ''}</T>
                  </View>
                  <T tone="small" style={{ color: C.roof700 }}>{c.status}</T>
                </View>
              ))}
            </View>
          </Card>
        )}

        <Card>
          <Row style={{ justifyContent: 'space-between' }}>
            <T tone="h2">Last 30 days</T>
            {!summary.fresh && <T tone="small">{summary.data ? 'Saved copy' : 'Needs a connection'}</T>}
          </Row>
          <T tone="small" style={{ marginTop: 4 }}>How the call centre classified your entries.</T>
          <View style={st.ragGrid}>
            {['GREEN', 'AMBER', 'RED', 'RNR', 'PENDING', 'NA'].map((k) => (
              <View key={k} style={st.ragCell}><RagBadge value={k} /><T style={st.ragNum}>{rag[k] ?? 0}</T></View>
            ))}
          </View>
        </Card>

        <Pressable onPress={() => router.push('/entries')} style={st.link} accessibilityRole="link">
          <T style={{ fontFamily: F.semibold, color: C.navy700 }}>See my entries</T>
          <Icon name="chevron-right" />
        </Pressable>
      </ScrollView>
    </View>
  )
}

const st = StyleSheet.create({
  meta: { fontFamily: F.medium, fontSize: 12, color: C.navy200, marginTop: 6 },
  bigRow: { flexDirection: 'row', alignItems: 'baseline', gap: 6, marginTop: 8, marginBottom: 10 },
  big: { fontFamily: F.bold, fontSize: 44, color: C.navy900, lineHeight: 50 },
  of: { fontFamily: F.medium, fontSize: 15, color: C.muted },
  fix: { flexDirection: 'row', alignItems: 'center', gap: 8, padding: 10, borderRadius: 12, backgroundColor: C.roof50 },
  ragGrid: { flexDirection: 'row', flexWrap: 'wrap', marginTop: 10, rowGap: 10 },
  ragCell: { width: '33.3%', gap: 4 },
  ragNum: { fontFamily: F.bold, fontSize: 20, color: C.navy900 },
  link: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: 16, backgroundColor: C.white, borderRadius: 16, borderWidth: 1, borderColor: C.line },
})
