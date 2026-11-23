import { useQuery } from '@tanstack/react-query'
import {
  BarChart3,
  Calendar,
  CheckCircle2,
  Clock,
  Download,
  ExternalLink,
  FileSpreadsheet,
  Languages,
  MapPin,
  PhoneCall,
  PhoneMissed,
  PieChart,
  RefreshCw,
  TrendingUp,
  User,
  UserCheck,
  UserX,
  X,
} from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Button, Card, cx, EmptyState, ErrorBox, Segmented, Skeleton, StatCard, Table, Td } from '../../components/ui'
import { api, errorMessage } from '../../services/api'
import { PERIODS, type Period } from '../dashboard/Dashboard'

export interface CallerAnalyticsData {
  caller: {
    id: string
    name: string
    employee_code: string
    languages: string[]
    usual_branches: string[]
    is_absent_today: boolean
    active: boolean
    daily_limit: number
    today_load: number
    today_calls_made: number
  }
  period: {
    label: string
    from: string
    to: string
  }
  summary: {
    total_attempts: number
    unique_entries: number
    connected_calls: number
    connected_pct: number
    unanswered_calls: number
    unanswered_pct: number
    validated_entries: number
    conversion_pct: number
    first_attempts_on_time: number
    first_attempt_on_time_pct: number
    avg_calls_per_day: number
  }
  outcome_breakdown: {
    outcome: string
    count: number
    pct: number
    group: 'positive' | 'unanswered' | 'discarded'
  }[]
  slot_distribution: {
    slot: string
    attempts: number
    connected: number
    connect_pct: number
  }[]
  category_performance: {
    category: string
    label: string
    entries: number
    attempts: number
    connected: number
    validated: number
    connect_pct: number
  }[]
  recent_calls: {
    id: string
    call_date: string
    slot: string
    created_at: string | null
    outcome: string
    row_status: string | null
    cycle: number
    entry_id: string
    entry_code: string
    person_name: string
    phone: string
    category: string
    branch_name: string
  }[]
}

interface Props {
  callerId: string
  callerName?: string
  onClose: () => void
}

type TabType = 'outcomes' | 'slots' | 'categories' | 'recent'

export function CallerAnalyticsModal({ callerId, callerName, onClose }: Props) {
  const [period, setPeriod] = useState<Period>('today')
  const [activeTab, setActiveTab] = useState<TabType>('outcomes')
  const [exporting, setExporting] = useState(false)
  const [exportError, setExportError] = useState<string | null>(null)

  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ['calls', 'caller-analytics', callerId, period],
    queryFn: async () =>
      (
        await api.get<CallerAnalyticsData>(`/reports/callcentre/caller/${callerId}`, {
          params: { period },
        })
      ).data,
  })

  const caller = data?.caller
  const summary = data?.summary

  const handleExport = async () => {
    setExportError(null)
    setExporting(true)
    try {
      const res = await api.get(`/reports/callcentre/caller/${callerId}/export.xlsx`, {
        params: { period },
        responseType: 'blob',
      })
      const href = URL.createObjectURL(res.data as Blob)
      const a = document.createElement('a')
      a.href = href
      a.download = `Caller_Analytics_${(caller?.name || 'Caller').replace(/\s+/g, '_')}_${period}.xlsx`
      a.click()
      setTimeout(() => URL.revokeObjectURL(href), 1000)
    } catch (e) {
      setExportError(errorMessage(e))
    } finally {
      setExporting(false)
    }
  }

  // Find peak slot
  const peakSlot = data?.slot_distribution?.reduce(
    (best, cur) => (cur.attempts > (best?.attempts ?? 0) ? cur : best),
    data?.slot_distribution?.[0]
  )

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-brand-950/60 p-3 sm:p-5 backdrop-blur-[2px]"
      onMouseDown={(e) => e.target === e.currentTarget && onClose()}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label={`Caller Analytics - ${caller?.name ?? callerName ?? 'Caller'}`}
        className="flex max-h-[92vh] w-full max-w-5xl flex-col overflow-hidden rounded-2xl bg-slate-50 shadow-2xl"
      >
        {/* Header Bar */}
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 bg-white px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-100 text-brand-700">
              <User size={22} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-bold text-slate-900">{caller?.name ?? callerName ?? 'Caller Analytics'}</h2>
                {caller?.employee_code && (
                  <span className="rounded bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-600">
                    {caller.employee_code}
                  </span>
                )}
                {caller && (
                  <span
                    className={cx(
                      'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold',
                      caller.active
                        ? caller.is_absent_today
                          ? 'bg-amber-100 text-amber-800'
                          : 'bg-emerald-100 text-emerald-800'
                        : 'bg-slate-100 text-slate-500'
                    )}
                  >
                    {caller.active ? (
                      caller.is_absent_today ? (
                        <>
                          <UserX size={12} /> Absent Today
                        </>
                      ) : (
                        <>
                          <UserCheck size={12} /> Present Today
                        </>
                      )
                    ) : (
                      'Inactive'
                    )}
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-500">Call Master deep drill-down & performance dashboard</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Segmented
              label="Period"
              options={PERIODS}
              value={period}
              onChange={(p) => setPeriod(p as Period)}
            />
            <Button
              variant="secondary"
              small
              onClick={handleExport}
              disabled={exporting || isLoading || !data}
              aria-label="Export caller analytics workbook"
            >
              <FileSpreadsheet size={15} className="text-emerald-700" />
              {exporting ? 'Exporting…' : 'Export Excel (.xlsx)'}
            </Button>
            <Button
              variant="ghost"
              small
              onClick={() => refetch()}
              disabled={isFetching}
              aria-label="Refresh caller analytics"
            >
              <RefreshCw size={15} className={isFetching ? 'animate-spin' : ''} />
            </Button>
            <button
              type="button"
              onClick={onClose}
              aria-label="Close analytics modal"
              className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
            >
              <X size={20} />
            </button>
          </div>
        </div>

        {/* Modal Scrollable Body */}
        <div className="flex-1 space-y-5 overflow-y-auto p-6">
          <ErrorBox error={error ? errorMessage(error) : null} />

          {isLoading || !data ? (
            <div className="space-y-4">
              <Skeleton className="h-24 w-full" />
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                <Skeleton className="h-20" />
                <Skeleton className="h-20" />
                <Skeleton className="h-20" />
                <Skeleton className="h-20" />
              </div>
              <Skeleton className="h-64 w-full" />
            </div>
          ) : (
            <>
              {/* Caller Snapshot Banner */}
              <div className="grid gap-4 rounded-xl border border-brand-100 bg-white p-4 shadow-sm md:grid-cols-3">
                <div className="space-y-1">
                  <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-500">
                    <Languages size={14} className="text-brand-600" />
                    <span>Languages Spoken</span>
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {caller?.languages?.length ? (
                      caller.languages.map((l) => (
                        <span
                          key={l}
                          className="rounded-md bg-brand-50 px-2 py-0.5 text-xs font-medium text-brand-700"
                        >
                          {l}
                        </span>
                      ))
                    ) : (
                      <span className="text-xs italic text-slate-400">None registered</span>
                    )}
                  </div>
                </div>

                <div className="space-y-1">
                  <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-500">
                    <MapPin size={14} className="text-brand-600" />
                    <span>Usual Branches</span>
                  </div>
                  <div className="text-xs text-slate-700">
                    {caller?.usual_branches?.length ? (
                      caller.usual_branches.join(', ')
                    ) : (
                      <span className="italic text-slate-400">No usual branch assigned</span>
                    )}
                  </div>
                </div>

                <div className="space-y-1">
                  <div className="flex items-center justify-between text-xs font-semibold text-slate-500">
                    <span>Today's Workload vs Limit</span>
                    <span className="font-mono text-slate-700">
                      {caller?.today_load ?? 0} / {caller?.daily_limit ?? 250}
                    </span>
                  </div>
                  <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100">
                    <div
                      className={cx(
                        'h-full rounded-full transition-all',
                        (caller?.today_load ?? 0) > (caller?.daily_limit ?? 250)
                          ? 'bg-red-500'
                          : 'bg-brand-600'
                      )}
                      style={{
                        width: `${Math.min(
                          100,
                          Math.round(((caller?.today_load ?? 0) / (caller?.daily_limit || 250)) * 100)
                        )}%`,
                      }}
                    />
                  </div>
                  <div className="flex justify-between text-[11px] text-slate-500">
                    <span>{caller?.today_calls_made ?? 0} calls completed today</span>
                    <span>
                      {(caller?.daily_limit ?? 250) - (caller?.today_load ?? 0) >= 0
                        ? `${(caller?.daily_limit ?? 250) - (caller?.today_load ?? 0)} remaining capacity`
                        : `${(caller?.today_load ?? 0) - (caller?.daily_limit ?? 250)} over limit`}
                    </span>
                  </div>
                </div>
              </div>

              {/* KPI Stat Cards */}
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                <StatCard
                  label="Total Calls Made"
                  value={summary?.total_attempts ?? 0}
                  hint={`${summary?.unique_entries ?? 0} distinct entries contacted`}
                />
                <StatCard
                  label="Connected Calls"
                  value={summary?.connected_calls ?? 0}
                  tone="green"
                  hint={`${summary?.connected_pct ?? 0}% connect rate`}
                />
                <StatCard
                  label="Validated Conversions"
                  value={summary?.validated_entries ?? 0}
                  tone="gold"
                  hint={`${summary?.conversion_pct ?? 0}% conversion of entries`}
                />
                <StatCard
                  label="First Try On-Time"
                  value={`${summary?.first_attempt_on_time_pct ?? 0}%`}
                  tone="blue"
                  hint={`${summary?.first_attempts_on_time ?? 0} on time · ${summary?.avg_calls_per_day ?? 0} calls/day avg`}
                />
              </div>

              {/* Navigation Tabs */}
              <div className="flex border-b border-slate-200">
                <button
                  type="button"
                  onClick={() => setActiveTab('outcomes')}
                  className={cx(
                    'border-b-2 px-4 py-2.5 text-sm font-semibold transition',
                    activeTab === 'outcomes'
                      ? 'border-brand-600 text-brand-600'
                      : 'border-transparent text-slate-500 hover:text-slate-800'
                  )}
                >
                  Call Outcomes & Quality
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab('slots')}
                  className={cx(
                    'border-b-2 px-4 py-2.5 text-sm font-semibold transition',
                    activeTab === 'slots'
                      ? 'border-brand-600 text-brand-600'
                      : 'border-transparent text-slate-500 hover:text-slate-800'
                  )}
                >
                  Hourly Productivity Slots
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab('categories')}
                  className={cx(
                    'border-b-2 px-4 py-2.5 text-sm font-semibold transition',
                    activeTab === 'categories'
                      ? 'border-brand-600 text-brand-600'
                      : 'border-transparent text-slate-500 hover:text-slate-800'
                  )}
                >
                  Category Performance
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab('recent')}
                  className={cx(
                    'border-b-2 px-4 py-2.5 text-sm font-semibold transition',
                    activeTab === 'recent'
                      ? 'border-brand-600 text-brand-600'
                      : 'border-transparent text-slate-500 hover:text-slate-800'
                  )}
                >
                  Recent Call History ({data.recent_calls?.length ?? 0})
                </button>
              </div>

              {/* Tab 1: Outcome Breakdown */}
              {activeTab === 'outcomes' && (
                <div className="space-y-4">
                  <div className="grid gap-4 md:grid-cols-3">
                    <div className="rounded-xl border border-emerald-200 bg-emerald-50/50 p-4">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold uppercase tracking-wider text-emerald-800">
                          Connected Calls
                        </span>
                        <PhoneCall size={18} className="text-emerald-600" />
                      </div>
                      <div className="mt-2 text-2xl font-bold text-emerald-950">
                        {summary?.connected_calls ?? 0}
                      </div>
                      <p className="mt-1 text-xs text-emerald-700">
                        {summary?.connected_pct ?? 0}% of all attempts reached the customer
                      </p>
                    </div>

                    <div className="rounded-xl border border-amber-200 bg-amber-50/50 p-4">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold uppercase tracking-wider text-amber-800">
                          Unanswered / Busy
                        </span>
                        <PhoneMissed size={18} className="text-amber-600" />
                      </div>
                      <div className="mt-2 text-2xl font-bold text-amber-950">
                        {summary?.unanswered_calls ?? 0}
                      </div>
                      <p className="mt-1 text-xs text-amber-700">
                        {summary?.unanswered_pct ?? 0}% ring no response, busy, or switched off
                      </p>
                    </div>

                    <div className="rounded-xl border border-blue-200 bg-blue-50/50 p-4">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold uppercase tracking-wider text-blue-800">
                          Validated Conversions
                        </span>
                        <CheckCircle2 size={18} className="text-blue-600" />
                      </div>
                      <div className="mt-2 text-2xl font-bold text-blue-950">
                        {summary?.validated_entries ?? 0}
                      </div>
                      <p className="mt-1 text-xs text-blue-700">
                        {summary?.conversion_pct ?? 0}% of distinct entries validated successfully
                      </p>
                    </div>
                  </div>

                  <div className="grid gap-4 lg:grid-cols-3">
                    {/* Graphical Donut Chart Card */}
                    <Card title="Outcome Proportion Chart">
                      {summary && summary.total_attempts > 0 ? (
                        <div className="flex flex-col items-center justify-center p-3 space-y-4">
                          {(() => {
                            const cPct = summary.connected_pct
                            const uPct = summary.unanswered_pct
                            const dPct = Math.max(0, 100 - cPct - uPct)
                            const circ = 2 * Math.PI * 38 // ~238.76
                            const cDash = (cPct / 100) * circ
                            const uDash = (uPct / 100) * circ
                            const dDash = (dPct / 100) * circ

                            return (
                              <div className="relative flex items-center justify-center">
                                <svg width="160" height="160" viewBox="0 0 100 100" className="transform -rotate-90">
                                  {/* Background ring */}
                                  <circle cx="50" cy="50" r="38" fill="transparent" stroke="#f1f5f9" strokeWidth="11" />
                                  {/* Connected slice */}
                                  {cPct > 0 && (
                                    <circle
                                      cx="50"
                                      cy="50"
                                      r="38"
                                      fill="transparent"
                                      stroke="#10b981"
                                      strokeWidth="11"
                                      strokeDasharray={`${cDash} ${circ}`}
                                      strokeDashoffset="0"
                                      strokeLinecap="round"
                                    />
                                  )}
                                  {/* Unanswered slice */}
                                  {uPct > 0 && (
                                    <circle
                                      cx="50"
                                      cy="50"
                                      r="38"
                                      fill="transparent"
                                      stroke="#f59e0b"
                                      strokeWidth="11"
                                      strokeDasharray={`${uDash} ${circ}`}
                                      strokeDashoffset={`${-cDash}`}
                                      strokeLinecap="round"
                                    />
                                  )}
                                  {/* Discarded slice */}
                                  {dPct > 0 && (
                                    <circle
                                      cx="50"
                                      cy="50"
                                      r="38"
                                      fill="transparent"
                                      stroke="#f43f5e"
                                      strokeWidth="11"
                                      strokeDasharray={`${dDash} ${circ}`}
                                      strokeDashoffset={`${-(cDash + uDash)}`}
                                      strokeLinecap="round"
                                    />
                                  )}
                                </svg>
                                <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
                                  <span className="text-xl font-bold text-slate-900">{summary.connected_pct}%</span>
                                  <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Connected</span>
                                </div>
                              </div>
                            )
                          })()}
                          {/* Donut Legend */}
                          <div className="w-full space-y-1 text-xs">
                            <div className="flex items-center justify-between">
                              <span className="flex items-center gap-1.5 text-slate-600">
                                <span className="h-2.5 w-2.5 rounded-full bg-emerald-500" /> Connected
                              </span>
                              <span className="font-semibold text-slate-800">{summary.connected_pct}% ({summary.connected_calls})</span>
                            </div>
                            <div className="flex items-center justify-between">
                              <span className="flex items-center gap-1.5 text-slate-600">
                                <span className="h-2.5 w-2.5 rounded-full bg-amber-500" /> Unanswered
                              </span>
                              <span className="font-semibold text-slate-800">{summary.unanswered_pct}% ({summary.unanswered_calls})</span>
                            </div>
                            <div className="flex items-center justify-between">
                              <span className="flex items-center gap-1.5 text-slate-600">
                                <span className="h-2.5 w-2.5 rounded-full bg-rose-500" /> Other / Discarded
                              </span>
                              <span className="font-semibold text-slate-800">
                                {Math.max(0, Math.round((100 - summary.connected_pct - summary.unanswered_pct) * 10) / 10)}%
                              </span>
                            </div>
                          </div>
                        </div>
                      ) : (
                        <div className="p-8 text-center text-xs text-slate-400">No call data for chart.</div>
                      )}
                    </Card>

                    {/* Detailed Progress Bars Card */}
                    <div className="lg:col-span-2">
                      <Card title="Detailed Outcome Distribution">
                        {!data.outcome_breakdown?.length ? (
                          <EmptyState icon={<BarChart3 size={20} />} title="No calls recorded in this period." />
                        ) : (
                          <div className="space-y-3 p-1">
                            {data.outcome_breakdown.map((item) => (
                              <div key={item.outcome} className="space-y-1">
                                <div className="flex items-center justify-between text-xs">
                                  <span className="font-medium text-slate-800">{item.outcome}</span>
                                  <span className="font-semibold text-slate-600">
                                    {item.count} calls ({item.pct}%)
                                  </span>
                                </div>
                                <div className="h-2.5 w-full overflow-hidden rounded-full bg-slate-100">
                                  <div
                                    className={cx(
                                      'h-full rounded-full transition-all',
                                      item.group === 'positive'
                                        ? 'bg-emerald-500'
                                        : item.group === 'unanswered'
                                        ? 'bg-amber-500'
                                        : 'bg-rose-400'
                                    )}
                                    style={{ width: `${Math.min(100, item.pct)}%` }}
                                  />
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </Card>
                    </div>
                  </div>
                </div>
              )}

              {/* Tab 2: Hourly Productivity Slots */}
              {activeTab === 'slots' && (
                <div className="space-y-4">
                  {peakSlot && peakSlot.attempts > 0 && (
                    <div className="flex items-center gap-3 rounded-xl border border-brand-200 bg-brand-50/60 p-4 text-brand-900">
                      <Clock size={20} className="text-brand-600 shrink-0" />
                      <div>
                        <span className="text-xs font-bold uppercase tracking-wider text-brand-700">
                          Peak Calling Hour
                        </span>
                        <p className="text-sm">
                          Slot <span className="font-bold">{peakSlot.slot}</span> recorded the highest volume with{' '}
                          <span className="font-bold">{peakSlot.attempts} attempts</span> and{' '}
                          <span className="font-bold">{peakSlot.connect_pct}% connect rate</span>.
                        </p>
                      </div>
                    </div>
                  )}

                  {/* Graphical Hourly Bar Chart (Histogram) */}
                  <Card title="Productivity Histogram by Slot">
                    {(() => {
                      const maxAtt = Math.max(...(data.slot_distribution.map((s) => s.attempts) || [1]), 1)
                      return (
                        <div className="overflow-x-auto p-2">
                          <svg viewBox="0 0 540 150" className="w-full min-w-[500px] h-40">
                            {/* Gridlines */}
                            <line x1="10" y1="110" x2="530" y2="110" stroke="#e2e8f0" strokeWidth="1" />
                            <line x1="10" y1="65" x2="530" y2="65" stroke="#f1f5f9" strokeWidth="1" strokeDasharray="3 3" />
                            <line x1="10" y1="20" x2="530" y2="20" stroke="#f1f5f9" strokeWidth="1" strokeDasharray="3 3" />

                            {data.slot_distribution.map((s, idx) => {
                              const x = 20 + idx * 56
                              const barHeight = s.attempts > 0 ? Math.max(12, Math.round((s.attempts / maxAtt) * 85)) : 4
                              const y = 110 - barHeight
                              const isPeak = peakSlot && peakSlot.slot === s.slot && s.attempts > 0
                              const fillColor =
                                s.attempts === 0
                                  ? '#e2e8f0'
                                  : s.connect_pct >= 60
                                  ? '#10b981'
                                  : s.connect_pct >= 40
                                  ? '#f59e0b'
                                  : '#64748b'

                              return (
                                <g key={s.slot}>
                                  {/* Peak Badge */}
                                  {isPeak && (
                                    <>
                                      <rect x={x + 2} y={Math.max(2, y - 16)} width="36" height="12" rx="3" fill="#312e81" />
                                      <text x={x + 20} y={Math.max(11, y - 7)} textAnchor="middle" className="text-[8px] font-bold fill-white">
                                        PEAK
                                      </text>
                                    </>
                                  )}

                                  {/* Volume count above bar */}
                                  {s.attempts > 0 && !isPeak && (
                                    <text x={x + 20} y={y - 4} textAnchor="middle" className="text-[10px] font-bold fill-slate-700">
                                      {s.attempts}
                                    </text>
                                  )}

                                  {/* Bar Rect */}
                                  <rect
                                    x={x + 2}
                                    y={y}
                                    width="36"
                                    height={barHeight}
                                    rx="4"
                                    fill={fillColor}
                                    className="transition-all hover:opacity-80 cursor-pointer"
                                  >
                                    <title>{`Slot ${s.slot}: ${s.attempts} calls (${s.connect_pct}% connected)`}</title>
                                  </rect>

                                  {/* Slot label below x axis */}
                                  <text x={x + 20} y="125" textAnchor="middle" className="text-[10px] font-semibold fill-slate-700">
                                    {s.slot}
                                  </text>

                                  {/* Connect rate % */}
                                  <text
                                    x={x + 20}
                                    y="138"
                                    textAnchor="middle"
                                    className={cx(
                                      'text-[9px] font-medium',
                                      s.attempts === 0 ? 'fill-slate-400' : 'fill-slate-600'
                                    )}
                                  >
                                    {s.attempts > 0 ? `${s.connect_pct}%` : '—'}
                                  </text>
                                </g>
                              )
                            })}
                          </svg>
                        </div>
                      )
                    })()}
                  </Card>

                  <Card flush title="Calls & Connect Rate by Hourly Slot">
                    <Table head={['Slot', 'Attempts', 'Connected', 'Connect Rate (%)', 'Volume Share']}>
                      {data.slot_distribution.map((s) => {
                        const sharePct = summary?.total_attempts
                          ? Math.round((s.attempts / summary.total_attempts) * 100)
                          : 0
                        return (
                          <tr key={s.slot}>
                            <Td className="font-semibold text-slate-800">{s.slot}</Td>
                            <Td className="tabular font-medium">{s.attempts}</Td>
                            <Td className="tabular text-emerald-700">{s.connected}</Td>
                            <Td className="tabular font-semibold">
                              <span
                                className={cx(
                                  'inline-block rounded px-1.5 py-0.5 text-xs',
                                  s.connect_pct >= 60
                                    ? 'bg-emerald-100 text-emerald-800'
                                    : s.connect_pct >= 40
                                    ? 'bg-amber-100 text-amber-800'
                                    : 'bg-slate-100 text-slate-600'
                                )}
                              >
                                {s.attempts ? `${s.connect_pct}%` : '—'}
                              </span>
                            </Td>
                            <Td className="w-48">
                              <div className="flex items-center gap-2">
                                <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-100">
                                  <div
                                    className="h-full bg-brand-500 rounded-full"
                                    style={{ width: `${Math.min(100, sharePct)}%` }}
                                  />
                                </div>
                                <span className="w-8 text-right text-xs text-slate-500">{sharePct}%</span>
                              </div>
                            </Td>
                          </tr>
                        )
                      })}
                    </Table>
                  </Card>
                </div>
              )}

              {/* Tab 3: Category Performance */}
              {activeTab === 'categories' && (
                <div className="space-y-4">
                  <Card flush title="Product Category Performance & Conversion">
                    {!data.category_performance?.length ? (
                      <EmptyState icon={<TrendingUp size={20} />} title="No categorized calls in this period." />
                    ) : (
                      <Table head={['Category', 'Entries Called', 'Attempts', 'Connected', 'Validated', 'Connect Rate (%)']}>
                        {data.category_performance.map((c) => (
                          <tr key={c.category}>
                            <Td className="font-medium text-slate-900">{c.label}</Td>
                            <Td className="tabular">{c.entries}</Td>
                            <Td className="tabular">{c.attempts}</Td>
                            <Td className="tabular text-emerald-700">{c.connected}</Td>
                            <Td className="tabular font-semibold text-brand-700">{c.validated}</Td>
                            <Td className="tabular font-semibold">
                              <span
                                className={cx(
                                  'inline-block rounded px-1.5 py-0.5 text-xs',
                                  c.connect_pct >= 60
                                    ? 'bg-emerald-100 text-emerald-800'
                                    : 'bg-slate-100 text-slate-600'
                                )}
                              >
                                {c.attempts ? `${c.connect_pct}%` : '—'}
                              </span>
                            </Td>
                          </tr>
                        ))}
                      </Table>
                    )}
                  </Card>
                </div>
              )}

              {/* Tab 4: Recent Call History */}
              {activeTab === 'recent' && (
                <Card flush title="Recent Calls Log (Last 50 attempts)" subtitle="Real-time call attempts recorded by this caller">
                  {!data.recent_calls?.length ? (
                    <EmptyState icon={<PhoneCall size={20} />} title="No call attempts recorded." />
                  ) : (
                    <Table head={['Date & Slot', 'Entry Code', 'Customer', 'Category', 'Branch', 'Outcome', 'Row Status', 'Action']}>
                      {data.recent_calls.map((rc) => (
                        <tr key={rc.id}>
                          <Td className="whitespace-nowrap text-xs">
                            <span className="font-semibold text-slate-800">{rc.call_date}</span>
                            <span className="ml-1 text-slate-500 font-mono">({rc.slot})</span>
                          </Td>
                          <Td className="font-mono text-xs font-semibold text-brand-700">{rc.entry_code}</Td>
                          <Td>
                            <p className="font-medium text-slate-900 text-xs">{rc.person_name}</p>
                            <p className="font-mono text-[11px] text-slate-400">{rc.phone}</p>
                          </Td>
                          <Td className="text-xs text-slate-600">{rc.category}</Td>
                          <Td className="text-xs text-slate-600">{rc.branch_name}</Td>
                          <Td>
                            <span
                              className={cx(
                                'inline-block rounded-full px-2 py-0.5 text-[11px] font-semibold',
                                rc.outcome === 'Connected'
                                  ? 'bg-emerald-100 text-emerald-800'
                                  : 'bg-amber-100 text-amber-800'
                              )}
                            >
                              {rc.outcome}
                            </span>
                          </Td>
                          <Td className="text-xs text-slate-700">{rc.row_status ?? '—'}</Td>
                          <Td>
                            <Link
                              to={`/entries/${rc.entry_id}`}
                              target="_blank"
                              className="inline-flex items-center gap-1 rounded bg-slate-100 px-2 py-1 text-xs font-medium text-brand-700 hover:bg-brand-50 hover:text-brand-800"
                            >
                              View <ExternalLink size={12} />
                            </Link>
                          </Td>
                        </tr>
                      ))}
                    </Table>
                  )}
                </Card>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-slate-200 bg-white px-6 py-3 text-xs text-slate-500">
          <span>Reporting Period: {data?.period?.from} to {data?.period?.to}</span>
          <Button variant="secondary" small onClick={onClose}>
            Close
          </Button>
        </div>
      </div>
    </div>
  )
}
