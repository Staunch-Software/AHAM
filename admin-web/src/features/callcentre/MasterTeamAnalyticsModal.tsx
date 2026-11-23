import { useQuery } from '@tanstack/react-query'
import {
  Award,
  BarChart3,
  Calendar,
  CheckCircle2,
  Clock,
  Download,
  ExternalLink,
  Flame,
  Languages,
  MapPin,
  PhoneCall,
  PhoneMissed,
  PieChart,
  RefreshCw,
  TrendingUp,
  UserCheck,
  Users,
  UserX,
  X,
} from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Button, Card, cx, EmptyState, ErrorBox, Segmented, Skeleton, StatCard, Table, Td } from '../../components/ui'
import { api, errorMessage } from '../../services/api'
import { PERIODS, type Period } from '../dashboard/Dashboard'
import { CallerAnalyticsModal } from './CallerAnalyticsModal'

export interface MasterCallerStats {
  caller_id: string
  name: string
  employee_code: string
  languages: string[]
  usual_branches: string[]
  is_absent_today: boolean
  active: boolean
  daily_limit: number
  today_load: number
  today_calls_made: number
  attempts: number
  unique_entries: number
  connected: number
  connect_pct: number
  unanswered: number
  validated: number
  conversion_pct: number
}

export interface MasterTeamAnalyticsData {
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
    active_callers_count: number
    avg_calls_per_caller: number
    total_capacity_today: number
    today_calls_made: number
  }
  callers: MasterCallerStats[]
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
    caller_name: string
  }[]
}

interface Props {
  onClose: () => void
}

type TabType = 'leaderboard' | 'slots' | 'outcomes' | 'categories' | 'recent'

export function MasterTeamAnalyticsModal({ onClose }: Props) {
  const [period, setPeriod] = useState<Period>('today')
  const [activeTab, setActiveTab] = useState<TabType>('leaderboard')
  const [exporting, setExporting] = useState(false)
  const [exportError, setExportError] = useState<string | null>(null)
  const [drilldownCaller, setDrilldownCaller] = useState<{ id: string; name: string } | null>(null)

  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ['calls', 'master-analytics', period],
    queryFn: async () =>
      (
        await api.get<MasterTeamAnalyticsData>('/reports/callcentre/master-analytics', {
          params: { period },
        })
      ).data,
  })

  const summary = data?.summary

  const handleExport = async () => {
    setExportError(null)
    setExporting(true)
    try {
      const res = await api.get('/reports/callcentre/master-analytics/export.xlsx', {
        params: { period },
        responseType: 'blob',
      })
      const href = URL.createObjectURL(res.data as Blob)
      const a = document.createElement('a')
      a.href = href
      a.download = `Call_Centre_Master_Team_Report_${period}.xlsx`
      a.click()
      setTimeout(() => URL.revokeObjectURL(href), 1000)
    } catch (e) {
      setExportError(errorMessage(e))
    } finally {
      setExporting(false)
    }
  }

  // Find peak productivity slot
  const peakSlot = data?.slot_distribution?.reduce(
    (best, cur) => (cur.attempts > (best?.attempts ?? 0) ? cur : best),
    data?.slot_distribution?.[0]
  )

  const pct = (a: number, b: number) => (b ? `${Math.round((a / b) * 100)}%` : '0%')

  return (
    <>
      <div
        className="fixed inset-0 z-50 flex items-center justify-center bg-brand-950/60 p-3 sm:p-5 backdrop-blur-[2px]"
        onMouseDown={(e) => e.target === e.currentTarget && onClose()}
      >
        <div
          role="dialog"
          aria-modal="true"
          aria-label="Call Centre Team Analytics & Master Report"
          className="flex max-h-[94vh] w-full max-w-6xl flex-col overflow-hidden rounded-2xl bg-slate-50 shadow-2xl"
        >
          {/* Header Bar */}
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 bg-white px-6 py-4">
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-gold-100 text-gold-800">
                <Users size={24} />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-xl font-bold text-slate-900">Call Master Team Analytics</h2>
                  <span className="rounded-full bg-gold-100 px-2.5 py-0.5 text-xs font-semibold text-gold-900">
                    All Callers Consolidated
                  </span>
                </div>
                <p className="text-xs text-slate-500">
                  Real-time productivity, comparative rankings, outcome metrics, and team export for Master Owner
                </p>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2.5">
              <Segmented label="Period" options={PERIODS} value={period} onChange={setPeriod} />

              <Button
                variant="secondary"
                small
                onClick={() => refetch()}
                disabled={isFetching}
                title="Refresh metrics"
              >
                <RefreshCw size={14} className={isFetching ? 'animate-spin' : ''} />
              </Button>

              <Button
                variant="gold"
                small
                onClick={handleExport}
                disabled={exporting || isLoading}
                title="Download 3-Sheet Master Team Report in Excel format"
              >
                <Download size={14} />
                {exporting ? 'Generating Excel…' : 'Master Excel (.xlsx)'}
              </Button>

              <button
                type="button"
                onClick={onClose}
                aria-label="Close"
                className="ml-1 rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition"
              >
                <X size={20} />
              </button>
            </div>
          </div>

          <ErrorBox error={error ? errorMessage(error) : exportError} />

          {/* Modal Scrollable Body */}
          <div className="flex-1 overflow-y-auto p-6 custom-scrollbar">
            {isLoading ? (
              <div className="space-y-4">
                <Skeleton className="h-20 w-full" />
                <div className="grid grid-cols-4 gap-4">
                  <Skeleton className="h-24" />
                  <Skeleton className="h-24" />
                  <Skeleton className="h-24" />
                  <Skeleton className="h-24" />
                </div>
                <Skeleton className="h-64 w-full" />
              </div>
            ) : !data || !summary ? (
              <EmptyState title="No analytics found for this period" />
            ) : (
              <div className="space-y-6">
                {/* Team Capacity Progress Banner */}
                <div className="rounded-xl border border-gold-200 bg-gradient-to-r from-gold-50/70 via-brand-50/50 to-white p-4 shadow-sm">
                  <div className="flex flex-wrap items-center justify-between gap-4">
                    <div>
                      <div className="flex items-center gap-2">
                        <Flame size={18} className="text-gold-600" />
                        <span className="font-semibold text-slate-900">Today's Team Calling Capacity</span>
                        <span className="text-xs text-slate-500">
                          ({summary.active_callers_count} active callers · limit {data.callers[0]?.daily_limit ?? 250}/caller)
                        </span>
                      </div>
                      <div className="mt-1 flex items-baseline gap-2">
                        <span className="text-2xl font-bold text-slate-900">{summary.today_calls_made}</span>
                        <span className="text-sm font-medium text-slate-500">
                          / {summary.total_capacity_today} maximum calls target today
                        </span>
                        <span className="ml-2 rounded-full bg-gold-200/80 px-2 py-0.5 text-xs font-semibold text-gold-900">
                          {pct(summary.today_calls_made, summary.total_capacity_today)} utilized
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center gap-6 text-xs text-slate-600">
                      <div>
                        <span className="block text-slate-400">Selected Range</span>
                        <span className="font-medium text-slate-800">
                          {data.period.from} to {data.period.to}
                        </span>
                      </div>
                      <div>
                        <span className="block text-slate-400">Avg Calls/Caller</span>
                        <span className="font-bold text-slate-800 text-sm">{summary.avg_calls_per_caller}</span>
                      </div>
                    </div>
                  </div>

                  {/* Capacity progress bar */}
                  <div className="mt-3 h-2.5 w-full overflow-hidden rounded-full bg-slate-200">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-gold-500 to-emerald-500 transition-all duration-500"
                      style={{
                        width: `${Math.min(
                          100,
                          summary.total_capacity_today > 0
                            ? (summary.today_calls_made / summary.total_capacity_today) * 100
                            : 0
                        )}%`,
                      }}
                    />
                  </div>
                </div>

                {/* 4 Core Summary Metric Cards */}
                <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
                  <StatCard
                    label="Team Calls Made"
                    value={summary.total_attempts}
                    hint={`${summary.unique_entries} distinct entries contacted`}
                  />
                  <StatCard
                    label="Connected Calls"
                    value={summary.connected_calls}
                    tone="green"
                    hint={`${summary.connected_pct}% team connect rate`}
                  />
                  <StatCard
                    label="Validated Entries"
                    value={summary.validated_entries}
                    tone="gold"
                    hint={`${summary.conversion_pct}% conversion to validated`}
                  />
                  <StatCard
                    label="First-Try TAT Compliance"
                    value={`${summary.first_attempt_on_time_pct}%`}
                    tone="blue"
                    hint={`${summary.first_attempts_on_time} validated within SLA`}
                  />
                </div>

                {/* Navigation Tabs */}
                <div className="flex border-b border-slate-200 gap-1">
                  <button
                    type="button"
                    onClick={() => setActiveTab('leaderboard')}
                    className={cx(
                      'flex items-center gap-2 border-b-2 px-4 py-2.5 text-sm font-semibold transition',
                      activeTab === 'leaderboard'
                        ? 'border-brand-600 text-brand-700 bg-white rounded-t-lg'
                        : 'border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-700'
                    )}
                  >
                    <Award size={16} />
                    Caller Ranking Leaderboard ({data.callers.length})
                  </button>

                  <button
                    type="button"
                    onClick={() => setActiveTab('slots')}
                    className={cx(
                      'flex items-center gap-2 border-b-2 px-4 py-2.5 text-sm font-semibold transition',
                      activeTab === 'slots'
                        ? 'border-brand-600 text-brand-700 bg-white rounded-t-lg'
                        : 'border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-700'
                    )}
                  >
                    <Clock size={16} />
                    Hourly Productivity Slots
                  </button>

                  <button
                    type="button"
                    onClick={() => setActiveTab('outcomes')}
                    className={cx(
                      'flex items-center gap-2 border-b-2 px-4 py-2.5 text-sm font-semibold transition',
                      activeTab === 'outcomes'
                        ? 'border-brand-600 text-brand-700 bg-white rounded-t-lg'
                        : 'border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-700'
                    )}
                  >
                    <PieChart size={16} />
                    Outcome Breakdown
                  </button>

                  <button
                    type="button"
                    onClick={() => setActiveTab('categories')}
                    className={cx(
                      'flex items-center gap-2 border-b-2 px-4 py-2.5 text-sm font-semibold transition',
                      activeTab === 'categories'
                        ? 'border-brand-600 text-brand-700 bg-white rounded-t-lg'
                        : 'border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-700'
                    )}
                  >
                    <BarChart3 size={16} />
                    Product Category Mix
                  </button>

                  <button
                    type="button"
                    onClick={() => setActiveTab('recent')}
                    className={cx(
                      'flex items-center gap-2 border-b-2 px-4 py-2.5 text-sm font-semibold transition',
                      activeTab === 'recent'
                        ? 'border-brand-600 text-brand-700 bg-white rounded-t-lg'
                        : 'border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-700'
                    )}
                  >
                    <PhoneCall size={16} />
                    Recent Team Calls ({data.recent_calls.length})
                  </button>
                </div>

                {/* Tab 1: Caller Comparative Leaderboard */}
                {activeTab === 'leaderboard' && (
                  <Card flush>
                    <div className="border-b border-slate-100 p-4 bg-slate-50/50 flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <h3 className="font-semibold text-slate-900">Caller Comparative Performance Matrix</h3>
                        <p className="text-xs text-slate-500">
                          Side-by-side comparative ranking based on calls made, connect rate, conversions, and daily load. Click any caller to inspect their deep-dive analytics.
                        </p>
                      </div>
                      <div className="text-xs text-slate-500">
                        Total Callers: <strong>{data.callers.length}</strong>
                      </div>
                    </div>

                    {!data.callers.length ? (
                      <EmptyState title="No callers found." />
                    ) : (
                      <div className="overflow-x-auto">
                        <table className="w-full text-left text-sm">
                          <thead className="bg-slate-50 text-xs font-semibold uppercase text-slate-600 border-b border-slate-200">
                            <tr>
                              <th className="px-4 py-3 text-center">Rank</th>
                              <th className="px-4 py-3">Caller Name</th>
                              <th className="px-4 py-3">Emp Code</th>
                              <th className="px-4 py-3">Today Status</th>
                              <th className="px-4 py-3 text-right">Calls Made</th>
                              <th className="px-4 py-3 text-right">Connected</th>
                              <th className="px-4 py-3 text-right">Connect Rate</th>
                              <th className="px-4 py-3 text-right">Validated</th>
                              <th className="px-4 py-3 text-right">Conversion</th>
                              <th className="px-4 py-3 text-right">Today's Load</th>
                              <th className="px-4 py-3 text-center">Deep Dive</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-100">
                            {data.callers.map((clr, idx) => {
                              const rank = idx + 1
                              return (
                                <tr
                                  key={clr.caller_id}
                                  className="hover:bg-slate-50/80 cursor-pointer transition"
                                  onClick={() => setDrilldownCaller({ id: clr.caller_id, name: clr.name })}
                                >
                                  <td className="px-4 py-3 text-center font-bold">
                                    {rank === 1 ? (
                                      <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-amber-100 text-xs font-bold text-amber-800 shadow-sm border border-amber-300">
                                        🥇
                                      </span>
                                    ) : rank === 2 ? (
                                      <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-slate-200 text-xs font-bold text-slate-700 shadow-sm border border-slate-300">
                                        🥈
                                      </span>
                                    ) : rank === 3 ? (
                                      <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-amber-50 text-xs font-bold text-amber-900 shadow-sm border border-amber-200">
                                        🥉
                                      </span>
                                    ) : (
                                      <span className="text-slate-400">#{rank}</span>
                                    )}
                                  </td>
                                  <td className="px-4 py-3 font-medium text-brand-700 hover:underline">
                                    {clr.name}
                                    {clr.languages && clr.languages.length > 0 && (
                                      <span className="block text-[11px] font-normal text-slate-400">
                                        {clr.languages.join(', ')}
                                      </span>
                                    )}
                                  </td>
                                  <td className="px-4 py-3 text-xs text-slate-600 font-mono">
                                    {clr.employee_code || '—'}
                                  </td>
                                  <td className="px-4 py-3">
                                    <span
                                      className={cx(
                                        'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold',
                                        clr.active
                                          ? clr.is_absent_today
                                            ? 'bg-amber-100 text-amber-800'
                                            : 'bg-emerald-100 text-emerald-800'
                                          : 'bg-slate-100 text-slate-500'
                                      )}
                                    >
                                      {clr.active ? (
                                        clr.is_absent_today ? (
                                          <>
                                            <UserX size={11} /> Absent
                                          </>
                                        ) : (
                                          <>
                                            <UserCheck size={11} /> Present
                                          </>
                                        )
                                      ) : (
                                        'Inactive'
                                      )}
                                    </span>
                                  </td>
                                  <td className="px-4 py-3 text-right font-bold text-slate-900 tabular-nums">
                                    {clr.attempts}
                                  </td>
                                  <td className="px-4 py-3 text-right text-emerald-700 font-medium tabular-nums">
                                    {clr.connected}
                                  </td>
                                  <td className="px-4 py-3 text-right tabular-nums">
                                    <span
                                      className={cx(
                                        'inline-block rounded px-1.5 py-0.5 text-xs font-semibold',
                                        clr.connect_pct >= 50
                                          ? 'bg-emerald-50 text-emerald-700'
                                          : clr.connect_pct >= 30
                                          ? 'bg-amber-50 text-amber-700'
                                          : 'bg-slate-100 text-slate-600'
                                      )}
                                    >
                                      {clr.connect_pct}%
                                    </span>
                                  </td>
                                  <td className="px-4 py-3 text-right font-medium text-gold-900 tabular-nums">
                                    {clr.validated}
                                  </td>
                                  <td className="px-4 py-3 text-right text-xs font-semibold text-slate-600 tabular-nums">
                                    {clr.conversion_pct}%
                                  </td>
                                  <td className="px-4 py-3 text-right text-xs tabular-nums text-slate-600">
                                    {clr.today_load} / {clr.daily_limit}
                                  </td>
                                  <td className="px-4 py-3 text-center">
                                    <Button
                                      variant="secondary"
                                      small
                                      onClick={(e) => {
                                        e.stopPropagation()
                                        setDrilldownCaller({ id: clr.caller_id, name: clr.name })
                                      }}
                                    >
                                      <TrendingUp size={13} />
                                      Analytics
                                    </Button>
                                  </td>
                                </tr>
                              )
                            })}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </Card>
                )}

                {/* Tab 2: Hourly Productivity Slots (SVG Bar Chart) */}
                {activeTab === 'slots' && (
                  <Card>
                    <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
                      <div>
                        <h3 className="font-semibold text-slate-900">Team Hourly Calling Volume & Connect Velocity</h3>
                        <p className="text-xs text-slate-500">
                          Distribution across the 9 official calling slots (09:00 to 18:00) for the selected period
                        </p>
                      </div>

                      {peakSlot && peakSlot.attempts > 0 && (
                        <div className="flex items-center gap-2 rounded-xl bg-gold-50 border border-gold-200 px-3 py-1.5 text-xs text-gold-900">
                          <Flame size={15} className="text-gold-600" />
                          <span>
                            Peak Team Window: <strong>{peakSlot.slot}</strong> ({peakSlot.attempts} attempts ·{' '}
                            {peakSlot.connected} connected · {peakSlot.connect_pct}%)
                          </span>
                        </div>
                      )}
                    </div>

                    {/* SVG Bar Chart */}
                    <div className="rounded-xl border border-slate-100 bg-white p-5 shadow-sm">
                      <div className="mb-4 flex items-center justify-between text-xs text-slate-500">
                        <span>Total Calls vs Connected</span>
                        <div className="flex items-center gap-4">
                          <span className="flex items-center gap-1.5">
                            <span className="h-3 w-3 rounded-sm bg-brand-600" /> Total Attempts
                          </span>
                          <span className="flex items-center gap-1.5">
                            <span className="h-3 w-3 rounded-sm bg-emerald-500" /> Connected
                          </span>
                        </div>
                      </div>

                      {/* SVG container */}
                      {(() => {
                        const slots = data.slot_distribution
                        const maxAtt = Math.max(...slots.map((s) => s.attempts), 1)
                        const chartHeight = 220
                        const barWidth = 32
                        const gap = 38

                        return (
                          <div className="overflow-x-auto">
                            <svg
                              width={slots.length * (barWidth * 2 + gap) + 60}
                              height={chartHeight + 60}
                              className="mx-auto"
                            >
                              {/* Background grid lines */}
                              {[0, 0.25, 0.5, 0.75, 1].map((ratio) => {
                                const y = chartHeight * (1 - ratio) + 20
                                const val = Math.round(maxAtt * ratio)
                                return (
                                  <g key={ratio}>
                                    <line
                                      x1="40"
                                      y1={y}
                                      x2={slots.length * (barWidth * 2 + gap) + 40}
                                      y2={y}
                                      stroke="#e2e8f0"
                                      strokeDasharray="3 3"
                                    />
                                    <text x="32" y={y + 4} textAnchor="end" fontSize="10" fill="#94a3b8">
                                      {val}
                                    </text>
                                  </g>
                                )
                              })}

                              {/* Bars */}
                              {slots.map((slot, i) => {
                                const x = 50 + i * (barWidth * 2 + gap)
                                const attHeight = (slot.attempts / maxAtt) * chartHeight
                                const connHeight = (slot.connected / maxAtt) * chartHeight
                                const attY = chartHeight - attHeight + 20
                                const connY = chartHeight - connHeight + 20
                                const isPeak = slot.slot === peakSlot?.slot && slot.attempts > 0

                                return (
                                  <g key={slot.slot} className="group cursor-pointer">
                                    {/* Peak highlight backdrop */}
                                    {isPeak && (
                                      <rect
                                        x={x - 6}
                                        y="15"
                                        width={barWidth * 2 + 16}
                                        height={chartHeight + 10}
                                        fill="#fef3c7"
                                        opacity="0.4"
                                        rx="8"
                                      />
                                    )}

                                    {/* Attempts Bar */}
                                    <rect
                                      x={x}
                                      y={attY}
                                      width={barWidth}
                                      height={attHeight}
                                      fill="#283079"
                                      rx="4"
                                      className="transition-all hover:opacity-80"
                                    />
                                    {slot.attempts > 0 && (
                                      <text
                                        x={x + barWidth / 2}
                                        y={attY - 5}
                                        textAnchor="middle"
                                        fontSize="10"
                                        fontWeight="600"
                                        fill="#1e293b"
                                      >
                                        {slot.attempts}
                                      </text>
                                    )}

                                    {/* Connected Bar */}
                                    <rect
                                      x={x + barWidth + 4}
                                      y={connY}
                                      width={barWidth}
                                      height={connHeight}
                                      fill="#10b981"
                                      rx="4"
                                      className="transition-all hover:opacity-80"
                                    />
                                    {slot.connected > 0 && (
                                      <text
                                        x={x + barWidth + 4 + barWidth / 2}
                                        y={connY - 5}
                                        textAnchor="middle"
                                        fontSize="10"
                                        fontWeight="600"
                                        fill="#047857"
                                      >
                                        {slot.connected}
                                      </text>
                                    )}

                                    {/* Slot Label */}
                                    <text
                                      x={x + barWidth + 2}
                                      y={chartHeight + 38}
                                      textAnchor="middle"
                                      fontSize="11"
                                      fontWeight={isPeak ? '700' : '500'}
                                      fill={isPeak ? '#b45309' : '#475569'}
                                    >
                                      {slot.slot}
                                    </text>

                                    {/* Connect Rate % */}
                                    <text
                                      x={x + barWidth + 2}
                                      y={chartHeight + 52}
                                      textAnchor="middle"
                                      fontSize="10"
                                      fontWeight="600"
                                      fill={slot.connect_pct >= 40 ? '#059669' : '#64748b'}
                                    >
                                      {slot.connect_pct}%
                                    </text>
                                  </g>
                                )
                              })}
                            </svg>
                          </div>
                        )
                      })()}
                    </div>

                    {/* Table of slots */}
                    <div className="mt-5 grid grid-cols-3 gap-3 sm:grid-cols-5 lg:grid-cols-9">
                      {data.slot_distribution.map((s) => (
                        <div
                          key={s.slot}
                          className={cx(
                            'rounded-xl border p-2.5 text-center',
                            s.slot === peakSlot?.slot && s.attempts > 0
                              ? 'border-gold-300 bg-gold-50/60 shadow-sm'
                              : 'border-slate-100 bg-white'
                          )}
                        >
                          <span className="block text-xs font-semibold text-slate-700">{s.slot}</span>
                          <span className="text-lg font-bold text-slate-900">{s.attempts}</span>
                          <span className="block text-[11px] text-emerald-700 font-medium">
                            {s.connected} conn ({s.connect_pct}%)
                          </span>
                        </div>
                      ))}
                    </div>
                  </Card>
                )}

                {/* Tab 3: Outcome Distribution (SVG Donut Chart) */}
                {activeTab === 'outcomes' && (
                  <div className="grid gap-6 lg:grid-cols-2">
                    {/* SVG Donut Chart */}
                    <Card title="Team Call Outcome Distribution">
                      <div className="flex flex-col items-center justify-center p-4">
                        {summary.total_attempts === 0 ? (
                          <EmptyState title="No calls in this period" />
                        ) : (
                          <div className="relative flex items-center justify-center">
                            {(() => {
                              const total = summary.total_attempts
                              const size = 260
                              const strokeWidth = 36
                              const radius = (size - strokeWidth) / 2
                              const circumference = 2 * Math.PI * radius
                              let currentAngle = -90

                              const colorMap: Record<string, string> = {
                                'Connected and answered': '#10b981', // emerald-500
                                'Not answered': '#f59e0b', // amber-500
                                'Switched off': '#64748b', // slate-500
                                Busy: '#3b82f6', // blue-500
                                'Invalid phone number': '#ef4444', // red-500
                                'Wrong number': '#dc2626', // red-600
                                'Call disconnected': '#f97316', // orange-500
                                'Out of coverage': '#8b5cf6', // purple-500
                                'Incoming barred': '#ec4899', // pink-500
                              }

                              const segments = data.outcome_breakdown.map((item) => {
                                const strokeDasharray = `${(item.count / total) * circumference} ${circumference}`
                                const angle = currentAngle
                                currentAngle += (item.count / total) * 360
                                return {
                                  outcome: item.outcome,
                                  count: item.count,
                                  pct: item.pct,
                                  stroke: colorMap[item.outcome] || '#94a3b8',
                                  strokeDasharray,
                                  transform: `rotate(${angle} ${size / 2} ${size / 2})`,
                                }
                              })

                              return (
                                <>
                                  <svg width={size} height={size} className="transform -rotate-90">
                                    <circle
                                      cx={size / 2}
                                      cy={size / 2}
                                      r={radius}
                                      fill="transparent"
                                      stroke="#f1f5f9"
                                      strokeWidth={strokeWidth}
                                    />
                                    {segments.map((seg, i) => (
                                      <circle
                                        key={i}
                                        cx={size / 2}
                                        cy={size / 2}
                                        r={radius}
                                        fill="transparent"
                                        stroke={seg.stroke}
                                        strokeWidth={strokeWidth}
                                        strokeDasharray={seg.strokeDasharray}
                                        strokeDashoffset="0"
                                        className="transition-all duration-300"
                                      />
                                    ))}
                                  </svg>

                                  <div className="absolute inset-0 flex flex-col items-center justify-center text-center pointer-events-none">
                                    <span className="text-3xl font-extrabold text-slate-900">
                                      {summary.connected_pct}%
                                    </span>
                                    <span className="text-xs font-semibold text-emerald-600 uppercase tracking-wider">
                                      Connect Rate
                                    </span>
                                    <span className="text-[11px] text-slate-400">
                                      {summary.connected_calls} of {summary.total_attempts} calls
                                    </span>
                                  </div>
                                </>
                              )
                            })()}
                          </div>
                        )}
                      </div>
                    </Card>

                    {/* Breakdown List */}
                    <Card title="Outcome Granular Summary">
                      <div className="space-y-3">
                        {data.outcome_breakdown.map((item) => (
                          <div
                            key={item.outcome}
                            className="flex items-center justify-between rounded-xl border border-slate-100 bg-white p-3 shadow-xs"
                          >
                            <div className="flex items-center gap-3">
                              <span
                                className={cx(
                                  'h-3 w-3 rounded-full',
                                  item.group === 'positive'
                                    ? 'bg-emerald-500'
                                    : item.group === 'unanswered'
                                    ? 'bg-amber-500'
                                    : 'bg-rose-500'
                                )}
                              />
                              <div>
                                <span className="font-semibold text-slate-800 text-sm">{item.outcome}</span>
                                <span className="block text-[11px] text-slate-400 capitalize">
                                  {item.group} bucket
                                </span>
                              </div>
                            </div>

                            <div className="text-right">
                              <span className="text-sm font-bold text-slate-900">{item.count}</span>
                              <span className="block text-xs font-medium text-slate-500">{item.pct}%</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </Card>
                  </div>
                )}

                {/* Tab 4: Product Category Performance */}
                {activeTab === 'categories' && (
                  <Card flush>
                    <div className="border-b border-slate-100 p-4 bg-slate-50/50">
                      <h3 className="font-semibold text-slate-900">Product Category Calling Metrics</h3>
                      <p className="text-xs text-slate-500">
                        Performance breakdown across AHAM loan product categories for the selected period
                      </p>
                    </div>

                    {!data.category_performance.length ? (
                      <EmptyState title="No categories found for this period." />
                    ) : (
                      <Table
                        head={['Category', 'Entries Called', 'Attempts', 'Connected', 'Validated', 'Connect Rate']}
                      >
                        {data.category_performance.map((cat) => (
                          <tr key={cat.category}>
                            <Td className="font-semibold text-slate-800">{cat.label}</Td>
                            <Td className="tabular font-medium">{cat.entries}</Td>
                            <Td className="tabular font-medium">{cat.attempts}</Td>
                            <Td className="tabular text-emerald-700 font-semibold">{cat.connected}</Td>
                            <Td className="tabular text-gold-900 font-semibold">{cat.validated}</Td>
                            <Td className="tabular">
                              <span
                                className={cx(
                                  'inline-block rounded px-2 py-0.5 text-xs font-semibold',
                                  cat.connect_pct >= 50
                                    ? 'bg-emerald-50 text-emerald-700'
                                    : cat.connect_pct >= 30
                                    ? 'bg-amber-50 text-amber-700'
                                    : 'bg-slate-100 text-slate-600'
                                )}
                              >
                                {cat.connect_pct}%
                              </span>
                            </Td>
                          </tr>
                        ))}
                      </Table>
                    )}
                  </Card>
                )}

                {/* Tab 5: Recent Team Calls Audit Log */}
                {activeTab === 'recent' && (
                  <Card flush>
                    <div className="border-b border-slate-100 p-4 bg-slate-50/50 flex items-center justify-between">
                      <div>
                        <h3 className="font-semibold text-slate-900">Latest 50 Call Attempts Recorded Across Team</h3>
                        <p className="text-xs text-slate-500">
                          Audit trail of recent call attempts with caller assignment, outcome, and verification status
                        </p>
                      </div>
                    </div>

                    {!data.recent_calls.length ? (
                      <EmptyState title="No call activity recorded yet." />
                    ) : (
                      <Table
                        head={[
                          'Date & Slot',
                          'Caller',
                          'Entry Code',
                          'Customer Name',
                          'Phone',
                          'Category & Branch',
                          'Outcome',
                          'Row Status',
                        ]}
                      >
                        {data.recent_calls.map((rc) => (
                          <tr key={rc.id}>
                            <Td>
                              <span className="font-medium text-slate-800">{rc.call_date}</span>
                              <span className="block text-xs text-slate-400 font-mono">{rc.slot}</span>
                            </Td>
                            <Td className="font-medium text-brand-700">{rc.caller_name}</Td>
                            <Td>
                              <Link
                                to={`/entries/${rc.entry_id}`}
                                className="font-bold text-brand-600 hover:underline flex items-center gap-1 font-mono text-xs"
                                target="_blank"
                                rel="noreferrer"
                              >
                                {rc.entry_code}
                                <ExternalLink size={11} />
                              </Link>
                            </Td>
                            <Td className="font-medium text-slate-800">{rc.person_name}</Td>
                            <Td className="font-mono text-xs text-slate-600">{rc.phone}</Td>
                            <Td>
                              <span className="font-medium text-slate-800">{rc.category}</span>
                              <span className="block text-xs text-slate-400">{rc.branch_name}</span>
                            </Td>
                            <Td>
                              <span
                                className={cx(
                                  'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold',
                                  rc.outcome === 'Connected and answered'
                                    ? 'bg-emerald-100 text-emerald-800'
                                    : rc.outcome === 'Not answered'
                                    ? 'bg-amber-100 text-amber-800'
                                    : 'bg-rose-100 text-rose-800'
                                )}
                              >
                                {rc.outcome === 'Connected and answered' ? (
                                  <PhoneCall size={12} />
                                ) : (
                                  <PhoneMissed size={12} />
                                )}
                                {rc.outcome}
                              </span>
                            </Td>
                            <Td>
                              {rc.row_status ? (
                                <span className="inline-block rounded bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700">
                                  {rc.row_status}
                                </span>
                              ) : (
                                <span className="text-xs text-slate-400">—</span>
                              )}
                            </Td>
                          </tr>
                        ))}
                      </Table>
                    )}
                  </Card>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Deep-dive individual caller modal if opened from Leaderboard */}
      {drilldownCaller && (
        <CallerAnalyticsModal
          callerId={drilldownCaller.id}
          callerName={drilldownCaller.name}
          onClose={() => setDrilldownCaller(null)}
        />
      )}
    </>
  )
}
