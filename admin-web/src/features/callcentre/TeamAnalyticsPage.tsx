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
  LineChart,
  PhoneCall,
  PhoneMissed,
  PieChart,
  RefreshCw,
  TrendingUp,
  User,
  UserCheck,
  Users,
  UserX,
} from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Button, Card, cx, EmptyState, ErrorBox, Input, PageTitle, Segmented, Select, Skeleton, Table, Td } from '../../components/ui'
import { api, errorMessage } from '../../services/api'
import { PERIODS, type Period } from '../dashboard/Dashboard'
import { CallerAnalyticsModal } from './CallerAnalyticsModal'
import type { MasterCallerStats, MasterTeamAnalyticsData } from './MasterTeamAnalyticsModal'

export interface TrendDay {
  date: string
  day_label: string
  attempts: number
  connected: number
  validated: number
  connect_pct: number
}

export interface AnalyticsResponse extends MasterTeamAnalyticsData {
  selected_caller?: { id: string; name: string; employee_code: string } | null
  trend: TrendDay[]
}

const ANALYTICS_PERIODS: { value: Period; label: string }[] = [
  { value: 'today', label: 'Today' },
  { value: 'week', label: 'This week' },
  { value: 'last_week', label: 'Last week' },
  { value: 'month', label: 'This month' },
]

export default function TeamAnalyticsPage() {
  const [period, setPeriod] = useState<Period>('week')
  const [selectedCallerId, setSelectedCallerId] = useState<string>('')
  const [dateFrom, setDateFrom] = useState<string>('')
  const [dateTo, setDateTo] = useState<string>('')
  const [isCustomDate, setIsCustomDate] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [exportError, setExportError] = useState<string | null>(null)
  const [drilldownCaller, setDrilldownCaller] = useState<{ id: string; name: string } | null>(null)
  const [hoveredTrendIdx, setHoveredTrendIdx] = useState<number | null>(null)

  const queryParams: Record<string, string | undefined> = {
    period: isCustomDate ? 'custom' : period,
    caller_id: selectedCallerId || undefined,
    date_from: isCustomDate && dateFrom ? dateFrom : undefined,
    date_to: isCustomDate && dateTo ? dateTo : undefined,
  }

  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ['calls', 'master-analytics', queryParams],
    queryFn: async () =>
      (
        await api.get<AnalyticsResponse>('/reports/callcentre/master-analytics', {
          params: queryParams,
        })
      ).data,
  })

  const summary = data?.summary
  const trend = data?.trend ?? []
  const callers = data?.callers ?? []
  const selectedCallerObj = callers.find((c) => c.caller_id === selectedCallerId)

  const handleExport = async () => {
    setExportError(null)
    setExporting(true)
    try {
      const res = await api.get('/reports/callcentre/master-analytics/export.xlsx', {
        params: queryParams,
        responseType: 'blob',
      })
      const href = URL.createObjectURL(res.data as Blob)
      const a = document.createElement('a')
      a.href = href
      const callerTag = selectedCallerObj ? `_${selectedCallerObj.name.replace(/\s+/g, '_')}` : '_All_Callers'
      a.download = `Call_Centre_Analytics${callerTag}_${isCustomDate ? 'custom' : period}.xlsx`
      a.click()
      setTimeout(() => URL.revokeObjectURL(href), 1000)
    } catch (e) {
      setExportError(errorMessage(e))
    } finally {
      setExporting(false)
    }
  }

  // Peak productivity slot calculation
  const peakSlot = data?.slot_distribution?.reduce(
    (best, cur) => (cur.attempts > (best?.attempts ?? 0) ? cur : best),
    data?.slot_distribution?.[0]
  )

  const pct = (a: number, b: number) => (b ? `${Math.round((a / b) * 100)}%` : '0%')

  return (
    <>
      <PageTitle
        subtitle="Visual data analytics, performance trends, outcome breakdown, and productivity heatmaps"
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              small
              onClick={() => refetch()}
              disabled={isFetching}
              title="Refresh live metrics"
            >
              <RefreshCw size={14} className={isFetching ? 'animate-spin' : ''} />
            </Button>

            <Button
              variant="gold"
              small
              onClick={handleExport}
              disabled={exporting || isLoading}
              title="Download formatted analytics report in Excel (.xlsx)"
            >
              <Download size={14} />
              {exporting ? 'Generating Excel…' : 'Export Excel (.xlsx)'}
            </Button>
          </div>
        }
      >
        Call Centre Data Analytics
      </PageTitle>

      <ErrorBox error={error ? errorMessage(error) : exportError} />

      {/* FILTER CONTROL BAR: Clean horizontal alignment */}
      <div className="mb-6 rounded-2xl border border-slate-200/90 bg-white p-4 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-4">
          {/* Left: Caller Dropdown */}
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-50 text-brand-700">
              <User size={18} />
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Caller:</span>
              <Select
                className="w-60 py-1.5 text-sm font-semibold"
                value={selectedCallerId}
                onChange={(e) => setSelectedCallerId(e.target.value)}
              >
                <option value="">All Callers (Full Team)</option>
                {callers.map((c) => (
                  <option key={c.caller_id} value={c.caller_id}>
                    {c.name} {c.employee_code ? `(${c.employee_code})` : ''}
                  </option>
                ))}
              </Select>
              {selectedCallerObj && (
                <button
                  type="button"
                  onClick={() => setSelectedCallerId('')}
                  className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-600 hover:bg-slate-200 hover:text-slate-800 transition"
                  title="Clear caller filter"
                >
                  Clear ×
                </button>
              )}
            </div>
          </div>

          {/* Right: Period Selector & Custom Date Picker */}
          <div className="flex items-center gap-3">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Timeframe:</span>
            <Segmented
              label="Period"
              options={ANALYTICS_PERIODS}
              value={period}
              onChange={(p) => {
                setPeriod(p)
                setIsCustomDate(false)
              }}
            />

            <button
              type="button"
              onClick={() => setIsCustomDate(!isCustomDate)}
              className={cx(
                'rounded-lg px-3 py-1.5 text-xs font-semibold transition border',
                isCustomDate
                  ? 'border-brand-600 bg-brand-50 text-brand-700'
                  : 'border-slate-200 bg-slate-50 text-slate-600 hover:bg-slate-100'
              )}
            >
              Custom Dates
            </button>

            {isCustomDate && (
              <div className="flex items-center gap-1.5">
                <Input
                  type="date"
                  aria-label="From date"
                  value={dateFrom}
                  onChange={(e) => setDateFrom(e.target.value)}
                  className="w-auto py-1 text-xs"
                />
                <span className="text-xs text-slate-400">to</span>
                <Input
                  type="date"
                  aria-label="To date"
                  value={dateTo}
                  onChange={(e) => setDateTo(e.target.value)}
                  className="w-auto py-1 text-xs"
                />
              </div>
            )}
          </div>
        </div>

        {/* Scope status strip with balanced padding */}
        <div className="mt-3 flex flex-wrap items-center justify-between border-t border-slate-100 pt-2.5 text-xs text-slate-500">
          <div className="flex items-center gap-2">
            <span className="inline-block h-2 w-2 rounded-full bg-emerald-500" />
            <span>
              Active Scope:{' '}
              <strong className="text-slate-800">
                {selectedCallerObj ? `${selectedCallerObj.name} (${selectedCallerObj.employee_code})` : 'All Callers (Full Team)'}
              </strong>
            </span>
            <span>·</span>
            <span>
              Period:{' '}
              <strong className="text-slate-800">
                {data?.period?.from ?? '—'} to {data?.period?.to ?? '—'}
              </strong>
            </span>
          </div>

          {summary && (
            <div className="flex items-center gap-4 text-slate-600">
              <span>
                Capacity: <strong>{summary.today_calls_made}</strong> / {summary.total_capacity_today} calls today (
                <strong className="text-emerald-700">{pct(summary.today_calls_made, summary.total_capacity_today)}</strong>)
              </span>
              <span>·</span>
              <span>
                Total in Period: <strong>{summary.total_attempts}</strong> calls (
                <strong className="text-emerald-700">{summary.connected_pct}% connected</strong>)
              </span>
            </div>
          )}
        </div>
      </div>

      {isLoading ? (
        <div className="space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            <Skeleton className="h-32 rounded-2xl" />
            <Skeleton className="h-32 rounded-2xl" />
            <Skeleton className="h-32 rounded-2xl" />
            <Skeleton className="h-32 rounded-2xl" />
          </div>
          <Skeleton className="h-80 w-full rounded-2xl" />
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Skeleton className="h-72 rounded-2xl" />
            <Skeleton className="h-72 rounded-2xl" />
          </div>
        </div>
      ) : !data || !summary ? (
        <EmptyState title="No analytics found for this filter" />
      ) : (
        <div className="space-y-6">
          {/* ============================================================== */}
          {/* TOP ROW: 4 BENTO KPI CARDS (Symmetrical Grid with Progress Bar) */}
          {/* ============================================================== */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {/* KPI 1: Calls Attempted */}
            <div className="flex flex-col justify-between rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm hover:shadow-md transition">
              <div>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Calls Attempted</span>
                  <span className="inline-flex items-center rounded-full bg-brand-50 px-2 py-0.5 text-xs font-bold text-brand-700">
                    Volume
                  </span>
                </div>
                <div className="mt-2.5 text-3xl font-extrabold text-slate-900 tabular-nums">
                  {summary.total_attempts}
                </div>
                <p className="mt-1 text-xs text-slate-500">
                  {summary.unique_entries} distinct customer leads reached
                </p>
              </div>
              <div className="mt-4 h-1.5 w-full rounded-full bg-slate-100 overflow-hidden">
                <div
                  className="h-full rounded-full bg-brand-700 transition-all duration-500"
                  style={{ width: `${Math.min(100, (summary.total_attempts / Math.max(1, summary.total_capacity_today)) * 100)}%` }}
                />
              </div>
            </div>

            {/* KPI 2: Connected Calls */}
            <div className="flex flex-col justify-between rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm hover:shadow-md transition">
              <div>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Connected Calls</span>
                  <span className="inline-flex items-center rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-bold text-emerald-700">
                    {summary.connected_pct}% Rate
                  </span>
                </div>
                <div className="mt-2.5 text-3xl font-extrabold text-emerald-700 tabular-nums">
                  {summary.connected_calls}
                </div>
                <p className="mt-1 text-xs text-slate-500">
                  {summary.unanswered_calls} unanswered or dropped calls
                </p>
              </div>
              <div className="mt-4 h-1.5 w-full rounded-full bg-slate-100 overflow-hidden">
                <div
                  className="h-full rounded-full bg-emerald-500 transition-all duration-500"
                  style={{ width: `${Math.min(100, summary.connected_pct)}%` }}
                />
              </div>
            </div>

            {/* KPI 3: Validated Leads */}
            <div className="flex flex-col justify-between rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm hover:shadow-md transition">
              <div>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Validated Leads</span>
                  <span className="inline-flex items-center rounded-full bg-gold-50 px-2 py-0.5 text-xs font-bold text-gold-900 border border-gold-200">
                    {summary.conversion_pct}% Conv
                  </span>
                </div>
                <div className="mt-2.5 text-3xl font-extrabold text-gold-900 tabular-nums">
                  {summary.validated_entries}
                </div>
                <p className="mt-1 text-xs text-slate-500">
                  Qualified customer leads converted to validated
                </p>
              </div>
              <div className="mt-4 h-1.5 w-full rounded-full bg-slate-100 overflow-hidden">
                <div
                  className="h-full rounded-full bg-gold-500 transition-all duration-500"
                  style={{ width: `${Math.min(100, summary.conversion_pct)}%` }}
                />
              </div>
            </div>

            {/* KPI 4: First-Try SLA */}
            <div className="flex flex-col justify-between rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm hover:shadow-md transition">
              <div>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-500">First-Try TAT SLA</span>
                  <span className="inline-flex items-center rounded-full bg-blue-50 px-2 py-0.5 text-xs font-bold text-blue-700">
                    Target &lt; 2 Days
                  </span>
                </div>
                <div className="mt-2.5 text-3xl font-extrabold text-blue-700 tabular-nums">
                  {summary.first_attempt_on_time_pct}%
                </div>
                <p className="mt-1 text-xs text-slate-500">
                  {summary.first_attempts_on_time} validated within SLA timeline
                </p>
              </div>
              <div className="mt-4 h-1.5 w-full rounded-full bg-slate-100 overflow-hidden">
                <div
                  className="h-full rounded-full bg-blue-500 transition-all duration-500"
                  style={{ width: `${Math.min(100, summary.first_attempt_on_time_pct)}%` }}
                />
              </div>
            </div>
          </div>

          {/* ============================================================== */}
          {/* MAIN ROW: 2-COLUMN BENTO (Trend Graph 8-Col + Donut 4-Col)       */}
          {/* ============================================================== */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
            {/* 8-Column: Trend Line/Area Curve */}
            <div className="lg:col-span-8 flex flex-col justify-between rounded-2xl border border-slate-200/90 bg-white p-6 shadow-sm">
              <div>
                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-3.5">
                  <div className="flex items-center gap-2.5">
                    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-50 text-brand-700">
                      <LineChart size={18} />
                    </div>
                    <div>
                      <h3 className="text-base font-bold text-slate-900">
                        Calling Activity &amp; Connect Velocity Trajectory
                      </h3>
                      <p className="text-xs text-slate-500">
                        Daily progression from {data.period.from} to {data.period.to}
                      </p>
                    </div>
                  </div>

                  {/* Graph Legend */}
                  <div className="flex items-center gap-4 text-xs font-medium text-slate-600">
                    <span className="flex items-center gap-1.5">
                      <span className="h-2.5 w-2.5 rounded-full bg-brand-700" />
                      Calls Made
                    </span>
                    <span className="flex items-center gap-1.5">
                      <span className="h-2.5 w-2.5 rounded-full bg-emerald-500" />
                      Connected
                    </span>
                    <span className="flex items-center gap-1.5">
                      <span className="h-2.5 w-2.5 rounded-full bg-gold-500" />
                      Validated
                    </span>
                  </div>
                </div>

                {/* Hover Tooltip display banner */}
                <div className="h-7 mt-2 flex items-center justify-end text-xs">
                  {hoveredTrendIdx !== null && trend[hoveredTrendIdx] ? (
                    <div className="flex items-center gap-3 rounded-lg bg-slate-900 px-3 py-1 text-white shadow-sm">
                      <span className="font-bold text-gold-300">{trend[hoveredTrendIdx].day_label}:</span>
                      <span><strong>{trend[hoveredTrendIdx].attempts}</strong> calls</span>
                      <span>·</span>
                      <span className="text-emerald-300"><strong>{trend[hoveredTrendIdx].connected}</strong> connected ({trend[hoveredTrendIdx].connect_pct}%)</span>
                      <span>·</span>
                      <span className="text-amber-300"><strong>{trend[hoveredTrendIdx].validated}</strong> validated</span>
                    </div>
                  ) : (
                    <span className="text-[11px] text-slate-400">Hover over any point to inspect daily metrics</span>
                  )}
                </div>
              </div>

              {/* SVG Curve Chart */}
              <div className="mt-2 w-full overflow-x-auto custom-scrollbar">
                {trend.length === 0 || trend.every((t) => t.attempts === 0) ? (
                  <div className="py-20 text-center text-sm text-slate-400">
                    No calling activity recorded in this period.
                  </div>
                ) : (
                  (() => {
                    const maxVal = Math.max(...trend.map((t) => t.attempts), 5)
                    const height = 240
                    const paddingLeft = 45
                    const paddingRight = 35
                    const paddingTop = 20
                    const paddingBottom = 35
                    const chartWidth = Math.max(680, trend.length * 62)

                    const getX = (i: number) =>
                      paddingLeft + (i / Math.max(1, trend.length - 1)) * (chartWidth - paddingLeft - paddingRight)
                    const getY = (val: number) =>
                      height - paddingBottom - (val / maxVal) * (height - paddingTop - paddingBottom)

                    // Attempts line & area
                    const attemptsPoints = trend.map((t, i) => `${i === 0 ? 'M' : 'L'} ${getX(i)} ${getY(t.attempts)}`).join(' ')
                    const attemptsArea = `${attemptsPoints} L ${getX(trend.length - 1)} ${height - paddingBottom} L ${getX(0)} ${height - paddingBottom} Z`

                    // Connected line & area
                    const connectedPoints = trend.map((t, i) => `${i === 0 ? 'M' : 'L'} ${getX(i)} ${getY(t.connected)}`).join(' ')
                    const connectedArea = `${connectedPoints} L ${getX(trend.length - 1)} ${height - paddingBottom} L ${getX(0)} ${height - paddingBottom} Z`

                    // Validated line
                    const validatedPoints = trend.map((t, i) => `${i === 0 ? 'M' : 'L'} ${getX(i)} ${getY(t.validated)}`).join(' ')

                    return (
                      <svg width={chartWidth} height={height} className="mx-auto block select-none">
                        <defs>
                          <linearGradient id="areaAttempts" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor="#283079" stopOpacity="0.22" />
                            <stop offset="100%" stopColor="#283079" stopOpacity="0.0" />
                          </linearGradient>
                          <linearGradient id="areaConnected" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor="#10b981" stopOpacity="0.30" />
                            <stop offset="100%" stopColor="#10b981" stopOpacity="0.0" />
                          </linearGradient>
                        </defs>

                        {/* Horizontal Grid Lines */}
                        {[0, 0.25, 0.5, 0.75, 1].map((ratio) => {
                          const y = height - paddingBottom - ratio * (height - paddingTop - paddingBottom)
                          const labelVal = Math.round(maxVal * ratio)
                          return (
                            <g key={ratio}>
                              <line
                                x1={paddingLeft}
                                y1={y}
                                x2={chartWidth - paddingRight}
                                y2={y}
                                stroke="#f1f5f9"
                                strokeDasharray="3 3"
                              />
                              <text x={paddingLeft - 8} y={y + 4} textAnchor="end" fontSize="10" fill="#94a3b8" fontFamily="sans-serif">
                                {labelVal}
                              </text>
                            </g>
                          )
                        })}

                        {/* Shaded Areas */}
                        <path d={attemptsArea} fill="url(#areaAttempts)" />
                        <path d={connectedArea} fill="url(#areaConnected)" />

                        {/* Curves */}
                        <path
                          d={attemptsPoints}
                          fill="none"
                          stroke="#283079"
                          strokeWidth="3"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                        <path
                          d={connectedPoints}
                          fill="none"
                          stroke="#10b981"
                          strokeWidth="2.5"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                        <path
                          d={validatedPoints}
                          fill="none"
                          stroke="#f59e0b"
                          strokeWidth="2"
                          strokeLinecap="round"
                          strokeDasharray="4 2"
                        />

                        {/* Data Points & Interactive hover zones */}
                        {trend.map((t, i) => {
                          const x = getX(i)
                          const yAtt = getY(t.attempts)
                          const yConn = getY(t.connected)
                          const isHovered = hoveredTrendIdx === i

                          return (
                            <g
                              key={t.date}
                              onMouseEnter={() => setHoveredTrendIdx(i)}
                              onMouseLeave={() => setHoveredTrendIdx(null)}
                              className="cursor-pointer"
                            >
                              {/* Hover vertical dashed line */}
                              {isHovered && (
                                <line
                                  x1={x}
                                  y1={paddingTop}
                                  x2={x}
                                  y2={height - paddingBottom}
                                  stroke="#94a3b8"
                                  strokeWidth="1.5"
                                  strokeDasharray="2 2"
                                />
                              )}

                              {/* Attempts Circle */}
                              <circle
                                cx={x}
                                cy={yAtt}
                                r={isHovered ? 6 : 4}
                                fill="#283079"
                                stroke="#ffffff"
                                strokeWidth="2"
                                className="transition-all"
                              />

                              {/* Connected Circle */}
                              <circle
                                cx={x}
                                cy={yConn}
                                r={isHovered ? 5 : 3.5}
                                fill="#10b981"
                                stroke="#ffffff"
                                strokeWidth="2"
                                className="transition-all"
                              />

                              {/* X Axis Day Label */}
                              <text
                                x={x}
                                y={height - 10}
                                textAnchor="middle"
                                fontSize="11"
                                fontWeight={isHovered ? '700' : '500'}
                                fill={isHovered ? '#0f172a' : '#64748b'}
                              >
                                {t.day_label}
                              </text>
                            </g>
                          )
                        })}
                      </svg>
                    )
                  })()
                )}
              </div>
            </div>

            {/* 4-Column: Connect Rate Radial Target & Outcome Split */}
            <div className="lg:col-span-4 flex flex-col justify-between rounded-2xl border border-slate-200/90 bg-white p-6 shadow-sm">
              <div>
                <div className="flex items-center gap-2.5 border-b border-slate-100 pb-3.5">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-50 text-emerald-700">
                    <PieChart size={18} />
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-slate-900">Connect Rate &amp; Outcomes</h3>
                    <p className="text-xs text-slate-500">Benchmark target vs dispositions</p>
                  </div>
                </div>

                {/* Symmetrical Donut Ring */}
                <div className="my-5 flex items-center justify-center">
                  {summary.total_attempts === 0 ? (
                    <div className="py-8 text-xs text-slate-400">No calls to display</div>
                  ) : (
                    <div className="relative flex items-center justify-center">
                      {(() => {
                        const total = summary.total_attempts
                        const size = 190
                        const strokeWidth = 26
                        const radius = (size - strokeWidth) / 2
                        const circumference = 2 * Math.PI * radius
                        let currentAngle = -90

                        const colorMap: Record<string, string> = {
                          'Connected and answered': '#10b981',
                          'Not answered': '#f59e0b',
                          'Switched off': '#64748b',
                          Busy: '#3b82f6',
                          'Invalid phone number': '#ef4444',
                          'Wrong number': '#dc2626',
                          'Call disconnected': '#f97316',
                          'Out of coverage': '#8b5cf6',
                          'Incoming barred': '#ec4899',
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
                              <span className="text-3xl font-black text-slate-900 tabular-nums">
                                {summary.connected_pct}%
                              </span>
                              <span className="text-[10px] font-extrabold text-emerald-600 uppercase tracking-widest">
                                Connect Rate
                              </span>
                              <span className="text-[11px] text-slate-400 mt-0.5">
                                {summary.connected_calls} of {summary.total_attempts} calls
                              </span>
                            </div>
                          </>
                        )
                      })()}
                    </div>
                  )}
                </div>
              </div>

              {/* 2x2 Outcome Chips with balanced heights */}
              <div className="grid grid-cols-2 gap-2 text-xs">
                {data.outcome_breakdown.slice(0, 4).map((item) => (
                  <div
                    key={item.outcome}
                    className="flex flex-col justify-between rounded-xl border border-slate-100 bg-slate-50/70 p-2.5"
                  >
                    <div className="flex items-center gap-1.5">
                      <span
                        className={cx(
                          'h-2 w-2 rounded-full shrink-0',
                          item.group === 'positive'
                            ? 'bg-emerald-500'
                            : item.group === 'unanswered'
                            ? 'bg-amber-500'
                            : 'bg-rose-500'
                        )}
                      />
                      <span className="font-semibold text-slate-700 truncate" title={item.outcome}>
                        {item.outcome}
                      </span>
                    </div>
                    <div className="mt-1 flex items-baseline justify-between">
                      <span className="font-bold text-slate-900 tabular-nums">{item.count}</span>
                      <span className="text-[11px] font-medium text-slate-500">{item.pct}%</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* ============================================================== */}
          {/* SECOND ROW: HOURLY VELOCITY SLOTS + CALLER LEADERBOARD          */}
          {/* ============================================================== */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-stretch">
            {/* Left: Hourly Velocity Slots (09:00 – 18:00) with Fixed Height & Inside Scroll */}
            <div className="h-[460px] flex flex-col justify-between rounded-2xl border border-slate-200/90 bg-white p-6 shadow-sm">
              <div className="flex flex-col min-h-0 flex-1">
                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-3.5 shrink-0">
                  <div className="flex items-center gap-2.5">
                    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gold-50 text-gold-800">
                      <Clock size={18} />
                    </div>
                    <div>
                      <h3 className="text-base font-bold text-slate-900">
                        Hourly Productivity Slots (09:00 – 18:00)
                      </h3>
                      <p className="text-xs text-slate-500">
                        Identify optimal calling windows throughout the workday
                      </p>
                    </div>
                  </div>

                  {peakSlot && peakSlot.attempts > 0 && (
                    <span className="flex items-center gap-1 rounded-full bg-gold-50 border border-gold-200 px-2.5 py-1 text-xs font-bold text-gold-900">
                      <Flame size={13} className="text-gold-600" />
                      Peak: {peakSlot.slot} ({peakSlot.connect_pct}%)
                    </span>
                  )}
                </div>

                {/* Symmetrical Slot Rows with inside scroll */}
                <div className="mt-4 flex-1 min-h-0 overflow-y-auto pr-2 custom-scrollbar space-y-2.5">
                  {data.slot_distribution.map((slot) => {
                    const isPeak = slot.slot === peakSlot?.slot && slot.attempts > 0
                    const maxAttempts = Math.max(...data.slot_distribution.map((s) => s.attempts), 1)
                    const fillPct = (slot.attempts / maxAttempts) * 100

                    return (
                      <div
                        key={slot.slot}
                        className={cx(
                          'flex items-center gap-3 rounded-xl px-3 py-2 text-xs transition',
                          isPeak ? 'bg-gold-50/80 border border-gold-200/90' : 'bg-slate-50/60 border border-slate-100'
                        )}
                      >
                        <span className={cx('w-20 font-semibold', isPeak ? 'text-gold-900 font-bold' : 'text-slate-600')}>
                          {slot.slot} {isPeak ? '🔥' : ''}
                        </span>

                        {/* Dual bar track */}
                        <div className="flex-1 h-3 rounded-full bg-slate-200 overflow-hidden flex">
                          <div
                            className="bg-brand-700 h-full transition-all duration-300"
                            style={{ width: `${fillPct}%` }}
                          />
                        </div>

                        <span className="w-16 text-right font-bold text-slate-900 tabular-nums">
                          {slot.attempts} calls
                        </span>

                        <span
                          className={cx(
                            'w-16 text-right font-bold tabular-nums',
                            slot.connect_pct >= 50
                              ? 'text-emerald-700'
                              : slot.connect_pct >= 30
                              ? 'text-amber-700'
                              : 'text-slate-500'
                          )}
                        >
                          {slot.connect_pct}% conn
                        </span>
                      </div>
                    )
                  })}
                </div>
              </div>

              {/* Slot Legend */}
              <div className="mt-3 flex items-center justify-between border-t border-slate-100 pt-3 text-xs text-slate-500 shrink-0">
                <span className="flex items-center gap-1.5">
                  <span className="h-2.5 w-2.5 rounded-sm bg-brand-700" /> Total Attempts Bar
                </span>
                <span>Calculated over all 9 standard work slots</span>
              </div>
            </div>

            {/* Right: Comparative Caller Leaderboard with Fixed Height & Inside Scroll */}
            <div className="h-[460px] flex flex-col justify-between rounded-2xl border border-slate-200/90 bg-white p-6 shadow-sm">
              <div className="flex flex-col min-h-0 flex-1">
                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-3.5 shrink-0">
                  <div className="flex items-center gap-2.5">
                    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-amber-50 text-amber-700">
                      <Award size={18} />
                    </div>
                    <div>
                      <h3 className="text-base font-bold text-slate-900">
                        Comparative Caller Leaderboard
                      </h3>
                      <p className="text-xs text-slate-500">
                        Ranking by calls completed, connect rate, and validations
                      </p>
                    </div>
                  </div>

                  <span className="text-xs text-slate-500">
                    <strong>{callers.length}</strong> Total Callers
                  </span>
                </div>

                {/* Symmetrical Caller Rows with inside scroll */}
                <div className="mt-4 flex-1 min-h-0 overflow-y-auto pr-2 custom-scrollbar space-y-3">
                  {!callers.length ? (
                    <EmptyState title="No callers registered" />
                  ) : (
                    callers.map((clr, idx) => {
                      const rank = idx + 1
                      return (
                        <div
                          key={clr.caller_id}
                          className={cx(
                            'rounded-xl border p-3.5 transition flex items-center justify-between gap-3',
                            selectedCallerId === clr.caller_id
                              ? 'border-brand-600 bg-brand-50/60 shadow-xs'
                              : 'border-slate-200/80 bg-white hover:bg-slate-50/80'
                          )}
                        >
                          {/* Rank Medal & Caller Identity */}
                          <div className="flex items-center gap-3">
                            <span className="w-6 text-center font-bold text-base">
                              {rank === 1 ? '🥇' : rank === 2 ? '🥈' : rank === 3 ? '🥉' : `#${rank}`}
                            </span>
                            <div>
                              <div className="flex items-center gap-2">
                                <button
                                  type="button"
                                  onClick={() => setSelectedCallerId(selectedCallerId === clr.caller_id ? '' : clr.caller_id)}
                                  className="font-bold text-slate-900 text-sm hover:text-brand-700 hover:underline text-left"
                                  title="Click to filter dashboard to this caller"
                                >
                                  {clr.name}
                                </button>
                                {clr.employee_code && (
                                  <span className="rounded bg-slate-100 px-1.5 py-0.2 text-[10px] font-mono text-slate-600">
                                    {clr.employee_code}
                                  </span>
                                )}
                              </div>
                              <span className="block text-[11px] text-slate-400 mt-0.5">
                                {clr.languages.join(', ') || 'No language set'}
                              </span>
                            </div>
                          </div>

                          {/* Caller Metrics & Action */}
                          <div className="flex items-center gap-4 text-xs">
                            <div className="text-right">
                              <span className="font-extrabold text-slate-900 tabular-nums">
                                {clr.attempts} calls
                              </span>
                              <span className="block text-[11px] font-semibold text-emerald-700">
                                {clr.connect_pct}% conn
                              </span>
                            </div>

                            <div className="text-right">
                              <span className="font-bold text-gold-900 tabular-nums">
                                {clr.validated} val
                              </span>
                              <span className="block text-[11px] text-slate-500">
                                {clr.today_load}/{clr.daily_limit} load
                              </span>
                            </div>

                            <Button
                              variant="secondary"
                              small
                              onClick={() => setDrilldownCaller({ id: clr.caller_id, name: clr.name })}
                              title="Inspect full audit modal for this caller"
                            >
                              <TrendingUp size={13} /> Deep Dive
                            </Button>
                          </div>
                        </div>
                      )
                    })
                  )}
                </div>
              </div>

              {/* Leaderboard footer */}
              <div className="mt-3 flex items-center justify-between border-t border-slate-100 pt-3 text-xs text-slate-500 shrink-0">
                <span>Click caller name to isolate dashboard view</span>
                <span>Sorted by calls completed desc</span>
              </div>
            </div>
          </div>

          {/* ============================================================== */}
          {/* SECTION 4: PRODUCT CATEGORY PERFORMANCE TABLE                  */}
          {/* ============================================================== */}
          <Card
            title="Product Category Calling Breakdown"
            subtitle="Calling metrics across AHAM loan product categories for the selected period"
            flush
          >
            {!data.category_performance.length ? (
              <EmptyState title="No category calling records found" />
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

          {/* ============================================================== */}
          {/* SECTION 5: RECENT AUDIT CALLS LOG TABLE                        */}
          {/* ============================================================== */}
          <Card
            title={`Recent Call Activity Log (${data.recent_calls.length} calls)`}
            subtitle="Audit trail of calls with customer details, assigned caller, outcome, and status"
            flush
          >
            {!data.recent_calls.length ? (
              <EmptyState title="No recent call activity found" />
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
        </div>
      )}

      {/* Deep-dive drill-down modal */}
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
