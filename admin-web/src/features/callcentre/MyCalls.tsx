import { useQuery } from '@tanstack/react-query'
import {
  CheckCircle2,
  Clock,
  Flag,
  History,
  PhoneCall,
  PhoneForwarded,
  PhoneMissed,
  Repeat,
  Search,
  Sparkles,
  X,
  XCircle,
} from 'lucide-react'
import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Card,
  cx,
  EmptyState,
  ErrorBox,
  ExportBar,
  Input,
  PageTitle,
  Pager,
  RAG_LABEL,
  RagBadge,
  Segmented,
  Select,
  Skeleton,
  Table,
  Td,
} from '../../components/ui'
import { api, errorMessage } from '../../services/api'
import { useAuth } from '../../services/auth'
import { useBranches, useCallers, useMeta } from '../../services/meta'
import type { CallHistoryItem, CallRow, Page } from '../../types'

const GROUPS = [
  { kind: 'priority', title: 'PRIORITY', hint: 'Reopened by the branch or flagged by the master owner: call first', icon: Flag, tone: 'text-roof-600 bg-roof-50' },
  { kind: 'retry', title: 'Retries due', hint: 'Unanswered before, or a callback that is due today', icon: Repeat, tone: 'text-violet-700 bg-violet-50' },
  { kind: 'followup', title: 'Follow-ups', hint: 'Cases to take forward and follow-ups sent to the call centre', icon: PhoneForwarded, tone: 'text-gold-700 bg-gold-100' },
  { kind: 'fresh', title: 'New entries', hint: 'Selected in today’s run for your branches', icon: Sparkles, tone: 'text-brand-700 bg-brand-50' },
] as const

/** The caller's list for today and their call history, with search & multi-facet filtering. */
export default function MyCalls() {
  const { me, path } = useAuth()
  const isMaster = me?.role === 'master_owner'
  const { data: callers } = useCallers(isMaster)
  const { data: branches } = useBranches()
  const { data: meta } = useMeta()
  const lim = meta?.limits

  const [tab, setTab] = useState<'queue' | 'history'>('queue')
  const [caller, setCaller] = useState('')

  // Queue filters
  const [searchQuery, setSearchQuery] = useState('')
  const [branchFilter, setBranchFilter] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('')
  const [groupFilter, setGroupFilter] = useState('')

  // History filters
  const [historyPage, setHistoryPage] = useState(1)
  const [historySearch, setHistorySearch] = useState('')
  const [historyBranch, setHistoryBranch] = useState('')
  const [historyOutcome, setHistoryOutcome] = useState('')
  const [datePreset, setDatePreset] = useState<'all' | 'today' | 'yesterday' | '7d' | '30d' | 'custom'>('all')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')

  const { data, isLoading, error } = useQuery({
    queryKey: ['calls', 'list', caller],
    queryFn: async () => (await api.get<{ today: string; items: CallRow[]; called_today?: CallRow[] }>('/calls/my-list', { params: { caller_id: caller || undefined } })).data,
    refetchInterval: 60_000,
  })

  const computedDates = useMemo(() => {
    const now = new Date()
    const fmt = (d: Date) => d.toISOString().slice(0, 10)
    if (datePreset === 'today') {
      const d = fmt(now)
      return { from: d, to: d }
    }
    if (datePreset === 'yesterday') {
      const y = new Date(now)
      y.setDate(y.getDate() - 1)
      const d = fmt(y)
      return { from: d, to: d }
    }
    if (datePreset === '7d') {
      const f = new Date(now)
      f.setDate(f.getDate() - 6)
      return { from: fmt(f), to: fmt(now) }
    }
    if (datePreset === '30d') {
      const f = new Date(now)
      f.setDate(f.getDate() - 29)
      return { from: fmt(f), to: fmt(now) }
    }
    if (datePreset === 'custom') {
      return { from: dateFrom || undefined, to: dateTo || undefined }
    }
    return { from: undefined, to: undefined }
  }, [datePreset, dateFrom, dateTo])

  const { data: historyData, isLoading: historyLoading, error: historyError } = useQuery({
    queryKey: ['calls', 'history', caller, historySearch, historyBranch, historyOutcome, computedDates.from, computedDates.to, historyPage],
    queryFn: async () => (await api.get<Page<CallHistoryItem>>('/calls/history', {
      params: {
        caller_id: caller || undefined,
        q: historySearch || undefined,
        branch_id: historyBranch || undefined,
        outcome: historyOutcome || undefined,
        date_from: computedDates.from,
        date_to: computedDates.to,
        page: historyPage,
        page_size: 25,
      },
    })).data,
    enabled: tab === 'history',
  })

  const items = data?.items ?? []
  const calledToday = data?.called_today ?? []

  // Filter Today's Queue client-side
  const filteredItems = useMemo(() => {
    return items.filter((r) => {
      if (searchQuery) {
        const q = searchQuery.toLowerCase().trim()
        const matches =
          r.person_name.toLowerCase().includes(q) ||
          r.phone.includes(q) ||
          r.entry_code.toLowerCase().includes(q) ||
          (r.so_name && r.so_name.toLowerCase().includes(q))
        if (!matches) return false
      }
      if (branchFilter && r.branch_id !== branchFilter) return false
      if (categoryFilter && r.category !== categoryFilter) return false
      if (groupFilter && r.kind !== groupFilter) return false
      return true
    })
  }, [items, searchQuery, branchFilter, categoryFilter, groupFilter])

  const filteredCalledToday = useMemo(() => {
    return calledToday.filter((r) => {
      if (searchQuery) {
        const q = searchQuery.toLowerCase().trim()
        const matches =
          r.person_name.toLowerCase().includes(q) ||
          r.phone.includes(q) ||
          r.entry_code.toLowerCase().includes(q) ||
          (r.so_name && r.so_name.toLowerCase().includes(q))
        if (!matches) return false
      }
      if (branchFilter && r.branch_id !== branchFilter) return false
      if (categoryFilter && r.category !== categoryFilter) return false
      return true
    })
  }, [calledToday, searchQuery, branchFilter, categoryFilter])

  const hasQueueFilters = Boolean(searchQuery || branchFilter || categoryFilter || groupFilter)
  const clearQueueFilters = () => {
    setSearchQuery('')
    setBranchFilter('')
    setCategoryFilter('')
    setGroupFilter('')
  }

  const hasHistoryFilters = Boolean(historySearch || historyBranch || historyOutcome || datePreset !== 'all' || dateFrom || dateTo)
  const clearHistoryFilters = () => {
    setHistorySearch('')
    setHistoryBranch('')
    setHistoryOutcome('')
    setDatePreset('all')
    setDateFrom('')
    setDateTo('')
    setHistoryPage(1)
  }

  return (
    <>
      <PageTitle
        subtitle={data ? `${items.length} to call · ${data.today}.${lim ? ` Lead: ${lim.tries_per_day_lead} tries a day, up to ${lim.max_unanswered_lead} unanswered. DSA/CP: ${lim.tries_per_day_dsa} try, one day.` : ''}` : 'Today’s list'}
        actions={
          <div className="flex flex-wrap items-center gap-3">
            {isMaster && (
              <Select aria-label="Caller" value={caller} onChange={(e) => setCaller(e.target.value)} className="w-52 sm:w-60">
                <option value="">My own list</option>
                {callers?.map((c) => <option key={c.id} value={c.id}>{c.full_name}</option>)}
              </Select>
            )}
          </div>
        }>
        My calls
      </PageTitle>

      {/* Tabs navigation */}
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <Segmented
          label="Calling view"
          value={tab}
          onChange={(v) => setTab(v)}
          options={[
            { value: 'queue', label: `Today’s queue (${items.length})` },
            { value: 'history', label: 'Call history & actioned' },
          ]}
        />
        {tab === 'queue' && items.length + calledToday.length > 0 && (
          <ExportBar
            name="My calls"
            className="px-0"
            header={['List', 'Entry ID', 'Person met', 'Mobile number', 'Category', 'Sales Officer', 'Branch', 'Calls today', 'Unanswered so far', 'Current status', 'RAG', 'PRIORITY reason']}
            rows={() => [...items.map((r) => [GROUPS.find((g) => g.kind === r.kind)?.title ?? r.kind, r] as const), ...calledToday.map((r) => ['Called today, still not answered', r] as const)]
              .map(([list, r]) => [list, r.entry_code, r.person_name, r.phone, r.category_label, r.so_name, r.branch_name, r.tries_today, r.unanswered_count, r.current_status, RAG_LABEL[r.rag] ?? r.rag, r.priority_reason])}
          />
        )}
        {tab === 'history' && (historyData?.total ?? 0) > 0 && (
          <ExportBar
            name="Call history"
            className="px-0"
            header={['Date', 'Time slot', 'Entry ID', 'Person met', 'Mobile number', 'Category', 'Branch', 'Sales Officer', 'Outcome', 'Row status', 'Current status', 'RAG', 'Caller']}
            rows={async () => {
              const all = (await api.get<Page<CallHistoryItem>>('/calls/history', {
                params: {
                  caller_id: caller || undefined,
                  q: historySearch || undefined,
                  branch_id: historyBranch || undefined,
                  outcome: historyOutcome || undefined,
                  date_from: computedDates.from,
                  date_to: computedDates.to,
                  page: 1,
                  page_size: 500,
                },
              })).data.items
              return all.map((h) => [
                h.call_date,
                h.slot,
                h.entry_code,
                h.person_name,
                h.phone,
                h.category_label,
                h.branch_name ?? '',
                h.so_name ?? '',
                h.outcome,
                h.row_status ?? '',
                h.current_status,
                RAG_LABEL[h.rag] ?? h.rag,
                h.caller_name ?? '',
              ])
            }}
          />
        )}
      </div>

      <ErrorBox error={error ? errorMessage(error) : historyError ? errorMessage(historyError) : null} />

      {/* TAB 1: TODAY'S QUEUE */}
      {tab === 'queue' && (
        <>
          {/* Filters for Today's Queue */}
          <div className="mb-4 grid gap-2.5 rounded-2xl border border-slate-200/80 bg-white p-3.5 shadow-card sm:grid-cols-2 lg:grid-cols-4">
            <label className="relative sm:col-span-2">
              <span className="sr-only">Search</span>
              <Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" aria-hidden="true" />
              <Input
                className="pl-9"
                placeholder="Search by customer name, mobile, or entry ID..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </label>

            <Select aria-label="Branch filter" value={branchFilter} onChange={(e) => setBranchFilter(e.target.value)}>
              <option value="">All branches</option>
              {branches?.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
            </Select>

            <Select aria-label="Category filter" value={categoryFilter} onChange={(e) => setCategoryFilter(e.target.value)}>
              <option value="">All categories</option>
              {meta?.categories.map((c) => <option key={c.key} value={c.key}>{c.label}</option>)}
            </Select>

            <Select aria-label="Queue group filter" value={groupFilter} onChange={(e) => setGroupFilter(e.target.value)}>
              <option value="">All queue groups</option>
              {GROUPS.map((g) => <option key={g.kind} value={g.kind}>{g.title}</option>)}
            </Select>

            {hasQueueFilters && (
              <div className="flex items-center justify-between pt-1 border-t border-slate-100 sm:col-span-2 lg:col-span-4 text-xs">
                <span className="text-slate-600 font-medium">
                  Showing {filteredItems.length} of {items.length} entries match criteria
                </span>
                <button
                  type="button"
                  onClick={clearQueueFilters}
                  className="inline-flex items-center gap-1 font-medium text-brand-700 hover:text-brand-900 underline"
                >
                  <X size={13} aria-hidden="true" /> Reset filters
                </button>
              </div>
            )}
          </div>

          {isLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 4 }, (_, i) => <Skeleton key={i} className="h-16" />)}
            </div>
          ) : items.length === 0 ? (
            <Card>
              <EmptyState
                icon={<PhoneCall size={20} />}
                title="Nothing to call right now."
                hint="New entries arrive with the daily run; retries and follow-ups come back on their date."
              />
            </Card>
          ) : filteredItems.length === 0 && hasQueueFilters ? (
            <Card>
              <EmptyState
                icon={<Search size={20} />}
                title="No matching entries found."
                hint="Try broadening your search term or changing the filter options."
                action={
                  <button
                    type="button"
                    onClick={clearQueueFilters}
                    className="mt-2 text-sm font-medium text-brand-700 hover:underline"
                  >
                    Clear all filters
                  </button>
                }
              />
            </Card>
          ) : (
            <div className="space-y-6">
              {GROUPS.map((g) => {
                const rows = filteredItems.filter((r) => r.kind === g.kind)
                if (!rows.length) return null
                return (
                  <section key={g.kind} aria-label={g.title}>
                    <header className="mb-2 flex items-center gap-2">
                      <span className={cx('grid h-7 w-7 place-items-center rounded-lg', g.tone)}>
                        <g.icon size={15} aria-hidden="true" />
                      </span>
                      <h2 className="text-sm font-semibold text-brand-900">
                        {g.title} <span className="text-slate-400">({rows.length})</span>
                      </h2>
                      <span className="hidden text-xs text-slate-500 sm:inline">· {g.hint}</span>
                    </header>
                    <ul className="divide-y divide-slate-100 overflow-hidden rounded-2xl border border-slate-200/80 bg-white shadow-card">
                      {rows.map((r) => (
                        <CallItem key={r.allocation_id} r={r} to={path(`calls/${r.id}`)} />
                      ))}
                    </ul>
                  </section>
                )
              })}
            </div>
          )}

          {calledToday.length > 0 && (
            <section aria-label="Called today" className="mt-8">
              <header className="mb-2 flex items-center gap-2">
                <span className="grid h-7 w-7 place-items-center rounded-lg bg-slate-100 text-slate-600">
                  <PhoneCall size={15} aria-hidden="true" />
                </span>
                <h2 className="text-sm font-semibold text-brand-900">
                  Called today, still not answered <span className="text-slate-400">({filteredCalledToday.length})</span>
                </h2>
                <span className="hidden text-xs text-slate-500 sm:inline">
                  · {lim ? `${lim.tries_per_day_lead} tries are planned a day; up to ${lim.max_slots_per_day} can be recorded, so one more try is possible today` : 'One more try is possible today'}
                </span>
              </header>
              <ul className="divide-y divide-slate-100 overflow-hidden rounded-2xl border border-slate-200/80 bg-white opacity-90 shadow-card">
                {filteredCalledToday.map((r) => <CallItem key={r.allocation_id} r={r} to={path(`calls/${r.id}`)} />)}
              </ul>
            </section>
          )}
        </>
      )}

      {/* TAB 2: CALL HISTORY */}
      {tab === 'history' && (
        <>
          {/* History Filters */}
          <div className="mb-4 grid gap-2.5 rounded-2xl border border-slate-200/80 bg-white p-3.5 shadow-card sm:grid-cols-2 lg:grid-cols-4">
            <label className="relative sm:col-span-2">
              <span className="sr-only">Search call history</span>
              <Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" aria-hidden="true" />
              <Input
                className="pl-9"
                placeholder="Search history by name, mobile, entry code, or SO..."
                value={historySearch}
                onChange={(e) => {
                  setHistorySearch(e.target.value)
                  setHistoryPage(1)
                }}
              />
            </label>

            <Select
              aria-label="Filter history branch"
              value={historyBranch}
              onChange={(e) => {
                setHistoryBranch(e.target.value)
                setHistoryPage(1)
              }}>
              <option value="">All branches</option>
              {branches?.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
            </Select>

            <Select
              aria-label="Filter outcome"
              value={historyOutcome}
              onChange={(e) => {
                setHistoryOutcome(e.target.value)
                setHistoryPage(1)
              }}>
              <option value="">All outcomes</option>
              {meta?.outcomes.map((o) => <option key={o} value={o}>{o}</option>)}
            </Select>

            <div className="sm:col-span-2 lg:col-span-4 flex flex-wrap items-center gap-3 pt-2 border-t border-slate-100">
              <span className="text-xs font-medium text-slate-500">Date range:</span>
              <div className="inline-flex flex-wrap rounded-lg border border-slate-200 bg-slate-50 p-0.5 text-xs">
                {(['all', 'today', 'yesterday', '7d', '30d', 'custom'] as const).map((p) => (
                  <button
                    key={p}
                    type="button"
                    onClick={() => {
                      setDatePreset(p)
                      setHistoryPage(1)
                    }}
                    className={cx(
                      'rounded-md px-2.5 py-1 font-medium transition',
                      datePreset === p ? 'bg-white text-brand-700 shadow-sm font-semibold' : 'text-slate-600 hover:text-slate-900',
                    )}>
                    {p === 'all' ? 'All time' : p === 'today' ? 'Today' : p === 'yesterday' ? 'Yesterday' : p === '7d' ? 'Last 7 days' : p === '30d' ? 'Last 30 days' : 'Custom'}
                  </button>
                ))}
              </div>

              {datePreset === 'custom' && (
                <div className="flex items-center gap-2 text-xs text-slate-600">
                  <span>From:</span>
                  <Input
                    type="date"
                    value={dateFrom}
                    onChange={(e) => {
                      setDateFrom(e.target.value)
                      setHistoryPage(1)
                    }}
                    className="w-36 py-1 text-xs"
                  />
                  <span>To:</span>
                  <Input
                    type="date"
                    value={dateTo}
                    onChange={(e) => {
                      setDateTo(e.target.value)
                      setHistoryPage(1)
                    }}
                    className="w-36 py-1 text-xs"
                  />
                </div>
              )}

              {hasHistoryFilters && (
                <button
                  type="button"
                  onClick={clearHistoryFilters}
                  className="ml-auto inline-flex items-center gap-1 text-xs font-medium text-brand-700 hover:underline"
                >
                  <X size={12} aria-hidden="true" /> Reset filters
                </button>
              )}
            </div>
          </div>

          {/* History Content */}
          {historyLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 4 }, (_, i) => <Skeleton key={i} className="h-16" />)}
            </div>
          ) : !historyData || historyData.items.length === 0 ? (
            <Card>
              <EmptyState
                icon={<History size={20} />}
                title="No call history found."
                hint={hasHistoryFilters ? "No calls match your active search and filter settings." : "Calls you place and record will appear here with full outcome history."}
                action={
                  hasHistoryFilters ? (
                    <button
                      type="button"
                      onClick={clearHistoryFilters}
                      className="mt-2 text-sm font-medium text-brand-700 hover:underline"
                    >
                      Clear history filters
                    </button>
                  ) : undefined
                }
              />
            </Card>
          ) : (
            <>
              <Table
                head={['Date & Slot', 'Customer & Contact', 'Branch & SO', 'Category', 'Call outcome', 'Classification', 'RAG', 'Action']}
              >
                {historyData.items.map((h) => (
                  <tr key={h.id} className="hover:bg-slate-50/80 transition">
                    <Td className="whitespace-nowrap">
                      <div className="font-medium text-slate-900">{h.call_date}</div>
                      <div className="text-xs text-slate-500">Slot: {h.slot}</div>
                    </Td>
                    <Td>
                      <div className="font-medium text-slate-900">{h.person_name}</div>
                      <div className="text-xs text-slate-500">
                        {h.phone} · <span className="font-mono text-slate-400">{h.entry_code}</span>
                      </div>
                    </Td>
                    <Td>
                      <div className="text-sm text-slate-800">{h.branch_name ?? '—'}</div>
                      <div className="text-xs text-slate-500">{h.so_name ?? '—'}</div>
                    </Td>
                    <Td>
                      <span className="text-xs font-medium text-slate-700">{h.category_label}</span>
                    </Td>
                    <Td>
                      <OutcomeBadge outcome={h.outcome} />
                    </Td>
                    <Td>
                      <div className="text-xs font-medium text-slate-800">{h.row_status || h.current_status}</div>
                      {h.lead_id && (
                        <div className="text-[11px] font-mono text-emerald-700">Lead ID: {h.lead_id}</div>
                      )}
                    </Td>
                    <Td>
                      <RagBadge value={h.rag} />
                    </Td>
                    <Td className="whitespace-nowrap text-right">
                      <Link
                        to={path(`calls/${h.entry_id}`)}
                        className="rounded-lg bg-brand-50 px-2.5 py-1 text-xs font-medium text-brand-700 hover:bg-brand-100 transition"
                      >
                        View entry &rarr;
                      </Link>
                    </Td>
                  </tr>
                ))}
              </Table>
              <div className="mt-4">
                <Pager
                  page={historyData.page}
                  pageSize={historyData.page_size}
                  total={historyData.total}
                  onChange={(p) => setHistoryPage(p)}
                />
              </div>
            </>
          )}
        </>
      )}
    </>
  )
}

function OutcomeBadge({ outcome }: { outcome: string }) {
  if (outcome === 'Connected') {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 border border-emerald-200 px-2 py-0.5 text-xs font-medium text-emerald-700">
        <CheckCircle2 size={12} aria-hidden="true" />
        Connected
      </span>
    )
  }
  if (outcome === 'Callback requested') {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-violet-50 border border-violet-200 px-2 py-0.5 text-xs font-medium text-violet-700">
        <PhoneForwarded size={12} aria-hidden="true" />
        Callback
      </span>
    )
  }
  if (['Invalid number', 'Wrong person', 'Refused to talk'].includes(outcome)) {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-rose-50 border border-rose-200 px-2 py-0.5 text-xs font-medium text-rose-700">
        <XCircle size={12} aria-hidden="true" />
        {outcome}
      </span>
    )
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 border border-amber-200 px-2 py-0.5 text-xs font-medium text-amber-700">
      <PhoneMissed size={12} aria-hidden="true" />
      {outcome}
    </span>
  )
}

/** One entry on a calling list: who, the SO and branch, today's tries, status and RAG. */
function CallItem({ r, to }: { r: CallRow; to: string }) {
  return (
    <li>
      <Link to={to} className="flex flex-wrap items-center gap-x-6 gap-y-2 px-5 py-4 transition hover:bg-brand-50/40 focus:outline-none focus-visible:bg-brand-50">
        <div className="min-w-0 flex-1">
          <p className="font-medium text-slate-900">{r.person_name} <span className="tabular ml-2 text-sm font-normal text-slate-500">Mobile: {r.phone}</span></p>
          <p className="text-xs text-slate-500">{r.category_label}{r.cp_subtype_label && ` · ${r.cp_subtype_label}`} · {r.so_name} · {r.branch_name} · <span className="font-mono">{r.entry_code}</span></p>
          {(r.priority_reason || r.first_try_overdue) && (
            <p className="mt-1 flex flex-wrap gap-1.5 text-xs">
              {r.priority_reason && <span className="rounded-full bg-roof-50 px-2 py-0.5 font-medium text-roof-700" data-testid="priority-reason">{r.priority_reason}</span>}
              {r.first_try_overdue && <span className="inline-flex items-center gap-1 rounded-full bg-gold-100 px-2 py-0.5 font-medium text-gold-700"><Clock size={12} aria-hidden="true" />First try overdue</span>}
            </p>
          )}
        </div>
        <div className="text-right text-xs text-slate-500">
          <div>{r.tries_today} tried today · {r.unanswered_count} unanswered</div>
          <div>{r.current_status}</div>
        </div>
        <RagBadge value={r.rag} />
      </Link>
    </li>
  )
}
