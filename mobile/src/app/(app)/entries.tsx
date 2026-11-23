import { router, useFocusEffect } from 'expo-router'
import { useCallback, useMemo, useState } from 'react'
import { FlatList, Pressable, RefreshControl, ScrollView, StyleSheet, TextInput, View } from 'react-native'
import { Header } from '@/components/Header'
import { Button, Chip, Icon, Pill, RagBadge, Row, T } from '@/components/ui'
import { api } from '@/lib/api'
import { type LocalEntry, listEntries } from '@/lib/db'
import { useCached } from '@/lib/remote'
import { type ServerRow, STATE_PILL, statusText } from '@/lib/entryView'
import { categoryLabel } from '@/lib/rules'
import { useSession } from '@/lib/session'
import { runSync, useSyncStatus } from '@/lib/sync'
import { C, F } from '@/lib/theme'

type Item = { key: string; local?: LocalEntry; server?: ServerRow; when: string }
const FILTERS = [
  ['all', 'All'],
  ['action', 'To follow up'],
  ['waiting', 'Waiting to send'],
  ['validated', 'Validated'],
  ['retry', 'In retry'],
  ['correct', 'Fix number'],
] as const
const PAGE = 200

export default function Entries() {
  const { me } = useSession()
  const sync = useSyncStatus()
  const [local, setLocal] = useState<LocalEntry[]>([])
  const [filter, setFilter] = useState<(typeof FILTERS)[number][0]>('all')
  const [search, setSearch] = useState('')
  const server = useCached<{ items: ServerRow[]; total?: number }>(me ? `server_entries:${me.id}` : null, `/entries?page_size=${PAGE}`)
  // Older entries load on request, a page at a time: nothing is cut off silently (section 15).
  const [older, setOlder] = useState<ServerRow[]>([])
  const [localLimit, setLocalLimit] = useState(PAGE)
  const [loadingMore, setLoadingMore] = useState(false)
  const load = useCallback(() => { if (me) listEntries(me.id, localLimit).then(setLocal).catch(() => {}) }, [me, localLimit])
  useFocusEffect(load)
  const serverRows = useMemo(() => [...(server.data?.items ?? []), ...older], [server.data, older])
  const total = server.data?.total ?? serverRows.length
  const hasMore = serverRows.length < total || local.length >= localLimit
  const loadMore = async () => {
    setLoadingMore(true)
    try {
      if (serverRows.length < total) {
        const next = Math.floor(serverRows.length / PAGE) + 1
        const r = await api<{ items: ServerRow[] }>('GET', `/entries?page_size=${PAGE}&page=${next}`)
        setOlder((o) => [...o, ...r.items])
      }
      setLocalLimit((n) => n + PAGE)
    } catch { /* offline: the button stays for another try */ } finally { setLoadingMore(false) }
  }
  const items = useMemo<Item[]>(() => {
    const byServerId = new Map(serverRows.map((r) => [r.id, r]))
    const out: Item[] = local.map((l) => {
      const s = l.server_id ? byServerId.get(l.server_id) : undefined
      if (l.server_id) byServerId.delete(l.server_id)
      return { key: l.local_id, local: l, server: s, when: l.submitted_at }
    })
    for (const s of byServerId.values()) out.push({ key: `s:${s.id}`, server: s, when: s.submitted_at_device })  // made on another phone
    out.sort((a, b) => b.when.localeCompare(a.when))

    const q = search.trim().toLowerCase()

    return out.filter((i) => {
      // 1. Status Filter
      if (filter === 'waiting' && (!i.local || i.local.state === 'accepted')) return false
      if (filter === 'action' && !i.server?.so_action) return false
      if (filter === 'validated' && !(i.server?.rag === 'GREEN' || i.server?.customer_validated)) return false
      if (filter === 'retry' && !(i.server?.status === 'In retry' || i.server?.rag === 'RNR' || i.server?.rag === 'AMBER')) return false
      if (filter === 'correct' && !(i.server?.status === 'Invalid number' || i.server?.status === 'Wrong person')) return false

      // 2. Search Query
      if (q) {
        const name = (i.local?.person_name ?? i.server?.person_name ?? '').toLowerCase()
        const phone = (i.local?.phone ?? i.server?.phone ?? '').toLowerCase()
        const code = (i.local?.server_code ?? i.server?.entry_code ?? i.local?.entry_code ?? '').toLowerCase()
        if (!name.includes(q) && !phone.includes(q) && !code.includes(q)) return false
      }
      return true
    })
  }, [local, serverRows, filter, search, sync.lastRunAt])  // eslint-disable-line react-hooks/exhaustive-deps
  const refresh = async () => { if (me) { await runSync(me.id, true); await server.refresh(); load() } }
  return (
    <View style={{ flex: 1 }}>
      <Header subtitle={me?.employee_code} title="My entries">
        {/* Live Search Bar */}
        <View style={st.searchBox}>
          <Icon name="magnify" size={18} color="rgba(255,255,255,0.7)" />
          <TextInput
            value={search}
            onChangeText={setSearch}
            placeholder="Search by name, phone or ID…"
            placeholderTextColor="rgba(255,255,255,0.45)"
            style={st.searchInput}
            autoCorrect={false}
            autoCapitalize="none"
          />
          {search ? (
            <Pressable onPress={() => setSearch('')} hitSlop={8} accessibilityLabel="Clear search">
              <Icon name="close-circle" size={18} color="rgba(255,255,255,0.7)" />
            </Pressable>
          ) : null}
        </View>

        {/* Filter Chips */}
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 8, marginTop: 12 }}>
          {FILTERS.map(([k, label]) => (
            <Pressable key={k} onPress={() => setFilter(k)} style={[st.filter, filter === k && st.filterOn]} accessibilityRole="tab" accessibilityState={{ selected: filter === k }}>
              <T style={[st.filterText, filter === k && { color: C.navy900 }]}>{label}</T>
            </Pressable>
          ))}
        </ScrollView>
      </Header>
      <FlatList data={items} keyExtractor={(i) => i.key} contentContainerStyle={{ padding: 16, gap: 10, paddingBottom: 32 }}
        refreshControl={<RefreshControl refreshing={sync.running} onRefresh={refresh} tintColor={C.navy700} />}
        ListFooterComponent={hasMore ? (
          <View style={{ paddingTop: 6, gap: 6 }}>
            <T tone="small" style={{ textAlign: 'center' }}>Showing {serverRows.length} of {total} entries</T>
            <Button title={loadingMore ? 'Loading…' : 'Load older entries'} variant="ghost" icon="history" onPress={loadMore} disabled={loadingMore} testID="load-more" />
          </View>
        ) : undefined}
        ListEmptyComponent={
          <View style={{ alignItems: 'center', padding: 40, gap: 8 }}>
            <Icon name="clipboard-text-outline" size={36} color={C.navy200} />
            <T tone="small">{search ? `No entries matching "${search}"` : 'No entries here yet.'}</T>
          </View>
        }
        renderItem={({ item }) => {
          const l = item.local, s = item.server
          const pill = l ? STATE_PILL[l.state] : STATE_PILL.accepted
          return (
            <Pressable onPress={() => router.push({ pathname: '/entry/[id]', params: { id: l ? l.local_id : `s:${s!.id}` } })} style={st.item} accessibilityRole="button">
              <Row style={{ justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <View style={{ flex: 1, marginRight: 8 }}>
                  <T style={st.name} numberOfLines={1}>{l?.person_name ?? s?.person_name}</T>
                  <T tone="mono" style={{ fontSize: 11, marginTop: 2 }}>{l?.server_code ?? s?.entry_code ?? l?.entry_code}</T>
                </View>
                {s ? <RagBadge value={s.rag} /> : null}
              </Row>
              <T tone="small">{categoryLabel(l?.category ?? s!.category)} · Mobile {l?.phone ?? s?.phone} · {new Date(item.when).toLocaleString([], { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}</T>
              <Row style={{ flexWrap: 'wrap', marginTop: 4, gap: 6 }}>
                <Pill {...pill!} />
                {statusText(s) && <Pill text={statusText(s)!} />}
                {s?.tcs_id && <Pill text={`TCS: ${s.tcs_id}`} color={C.navy700} bg={C.navy100} icon="file-document-outline" />}
                {s?.so_action && <Pill text={`${s.so_action}${s.so_action_date ? ` · ${s.so_action_date}` : ''}`} color={C.roof700} bg={C.roof50} icon="flag-outline" />}
              </Row>
            </Pressable>
          )
        }} />
    </View>
  )
}

const st = StyleSheet.create({
  searchBox: { flexDirection: 'row', alignItems: 'center', backgroundColor: 'rgba(255,255,255,0.12)', borderRadius: 12, paddingHorizontal: 12, paddingVertical: 8, marginTop: 12, gap: 8 },
  searchInput: { flex: 1, fontFamily: F.regular, fontSize: 14, color: C.white, padding: 0 },
  filter: { paddingHorizontal: 12, paddingVertical: 6, borderRadius: 999, backgroundColor: 'rgba(255,255,255,0.08)' },
  filterOn: { backgroundColor: C.gold400 },
  filterText: { fontFamily: F.semibold, fontSize: 12, color: C.navy100 },
  item: { backgroundColor: C.white, borderRadius: 16, borderWidth: 1, borderColor: C.line, padding: 14, gap: 4 },
  name: { fontFamily: F.semibold, fontSize: 15, color: C.navy900 },
})
