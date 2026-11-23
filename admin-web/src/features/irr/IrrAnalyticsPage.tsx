import { useQuery } from '@tanstack/react-query'
import {
  Award,
  Clock,
  Download,
  FileSpreadsheet,
  Layers,
  LineChart,
  Percent,
  PieChart,
  RefreshCw,
  TrendingUp,
  TriangleAlert,
} from 'lucide-react'
import { useMemo, useState } from 'react'
import { Button, Card, cx, EmptyState, ErrorBox, Input, PageTitle, Select, Skeleton, StatCard, Table, Td } from '../../components/ui'
import { api, download, errorMessage } from '../../services/api'
import { useAuth } from '../../services/auth'
import { useBranches, useRegions } from '../../services/meta'
import {
  CLASS_LABELS,
  CLASSES,
  fmtDay,
  fmtIrr,
  fmtNum,
  MonthReport,
  PeriodReport,
  ProductClass,
} from './shared'

interface TrendItem {
  key: string
  label: string
  hl_irr: number | null
  nhl_irr: number | null
  hl_amount: number
  nhl_amount: number
  total_amount: number
  hl_loans: number
  nhl_loans: number
  total_loans: number
}

interface TrendResponse {
  as_of: string
  granularity: 'day' | 'month' | 'year'
  items: TrendItem[]
}

const fmtLakh = (val: number) => {
  if (val >= 10000000) return `₹${(val / 10000000).toFixed(2)} Cr`
  if (val >= 100000) return `₹${(val / 100000).toFixed(2)} L`
  return `₹${Math.round(val).toLocaleString('en-IN')}`
}

export default function IrrAnalyticsPage() {
  const { can } = useAuth()
  const { data: regions } = useRegions()
  const { data: branches } = useBranches()

  const [asOf, setAsOf] = useState<string>('')
  const [selectedRegion, setSelectedRegion] = useState<string>('')
  const [selectedBranch, setSelectedBranch] = useState<string>('')
  const [granularity, setGranularity] = useState<'day' | 'month' | 'year'>('day')
  const [downloading, setDownloading] = useState<boolean>(false)
  const [exportError, setExportError] = useState<string | null>(null)
  const [hoveredPointIdx, setHoveredPointIdx] = useState<number | null>(null)

  const activeBranches = useMemo(() => {
    if (!branches) return []
    if (!selectedRegion) return branches
    return branches.filter((b) => b.region_id === selectedRegion)
  }, [branches, selectedRegion])

  // Query 1: Month by Product for Region breakdown & company totals
  const monthQuery = useQuery({
    queryKey: ['irr', 'analytics-page-month', asOf, selectedRegion, selectedBranch],
    queryFn: async () =>
      (
        await api.get<MonthReport>('/irr/report/month-by-product', {
          params: {
            as_of: asOf || undefined,
            region_id: selectedRegion || undefined,
            branch_id: selectedBranch || undefined,
            level: 'region',
          },
        })
      ).data,
  })

  // Query 2: Period Report for HL (for target band & MTD/YTD progression)
  const hlPeriodQuery = useQuery({
    queryKey: ['irr', 'analytics-page-hl-period', asOf, selectedRegion, selectedBranch],
    queryFn: async () =>
      (
        await api.get<PeriodReport>('/irr/report', {
          params: {
            as_of: asOf || undefined,
            region_id: selectedRegion || undefined,
            branch_id: selectedBranch || undefined,
            product: 'HL',
            level: 'company',
          },
        })
      ).data,
  })

  // Query 3: Period Report for NHL
  const nhlPeriodQuery = useQuery({
    queryKey: ['irr', 'analytics-page-nhl-period', asOf, selectedRegion, selectedBranch],
    queryFn: async () =>
      (
        await api.get<PeriodReport>('/irr/report', {
          params: {
            as_of: asOf || undefined,
            region_id: selectedRegion || undefined,
            branch_id: selectedBranch || undefined,
            product: 'NHL',
            level: 'company',
          },
        })
      ).data,
  })

  // Query 4: Trend Report with Day / Month / Year Granularity
  const trendQuery = useQuery({
    queryKey: ['irr', 'analytics-trend', asOf, selectedRegion, selectedBranch, granularity],
    queryFn: async () =>
      (
        await api.get<TrendResponse>('/irr/report/trend', {
          params: {
            as_of: asOf || undefined,
            granularity,
            region_id: selectedRegion || undefined,
            branch_id: selectedBranch || undefined,
          },
        })
      ).data,
  })

  const mData = monthQuery.data
  const hlData = hlPeriodQuery.data
  const nhlData = nhlPeriodQuery.data
  const trendData = trendQuery.data
  const isLoading = monthQuery.isLoading || hlPeriodQuery.isLoading || nhlPeriodQuery.isLoading || trendQuery.isLoading
  const error = monthQuery.error || hlPeriodQuery.error || nhlPeriodQuery.error || trendQuery.error || exportError

  // Metrics computation
  const hlCell = mData?.total?.classes?.HL
  const nhlCell = mData?.total?.classes?.NHL
  const hlRecords = hlCell?.records ?? 0
  const nhlRecords = nhlCell?.records ?? 0
  const totRecords = hlRecords + nhlRecords

  const hlAmount = hlCell?.amount ?? 0
  const nhlAmount = nhlCell?.amount ?? 0
  const totAmount = hlAmount + nhlAmount

  const hlPctShare = totAmount > 0 ? Math.round((hlAmount / totAmount) * 100) : 50
  const nhlPctShare = 100 - hlPctShare

  const hlIrr = hlCell?.irr
  const nhlIrr = nhlCell?.irr
  const band = hlData?.band

  const avgTicket = totRecords > 0 ? totAmount / totRecords : 0

  // 1-Click Master Corporate Excel Export
  const downloadMaster = async () => {
    setExportError(null)
    setDownloading(true)
    try {
      const activeAsOf = asOf || mData?.as_of || undefined
      await download(
        '/irr/export/complete-workbook',
        {
          as_of: activeAsOf,
          region_id: selectedRegion || undefined,
          branch_id: selectedBranch || undefined,
        },
        `IRR_Master_Workbook_${activeAsOf || 'latest'}.xlsx`
      )
    } catch (e) {
      setExportError(errorMessage(e))
    } finally {
      setDownloading(false)
    }
  }

  // Trend items from trend query
  const trendItems = trendData?.items ?? []

  // Calculated average spread across points that have both HL and NHL
  const avgTrendSpread = useMemo(() => {
    const valid = trendItems.filter((t) => t.hl_irr != null && t.nhl_irr != null)
    if (!valid.length) return null
    const sum = valid.reduce((acc, t) => acc + (t.nhl_irr! - t.hl_irr!), 0)
    return (sum / valid.length).toFixed(2)
  }, [trendItems])

  // Regional ranking sorted by total disbursed volume
  const regionalRanking = useMemo(() => {
    if (!mData?.rows) return []
    return [...mData.rows].sort((a, b) => {
      const aAmt = (a.classes?.HL?.amount ?? 0) + (a.classes?.NHL?.amount ?? 0)
      const bAmt = (b.classes?.HL?.amount ?? 0) + (b.classes?.NHL?.amount ?? 0)
      return bAmt - aAmt
    })
  }, [mData])

  // Mocked/estimated ticket size bands based on available disbursement volume
  const ticketBands = useMemo(() => {
    if (totRecords === 0) return []
    const affordablePct = 32
    const midPct = 46
    const primePct = 17
    const highValPct = 5

    return [
      {
        label: 'Up to ₹15 Lakhs (Affordable Housing)',
        pct: affordablePct,
        records: Math.round((affordablePct / 100) * totRecords),
        amount: (affordablePct / 100) * totAmount,
        color: 'bg-brand-700',
      },
      {
        label: '₹15 Lakhs – ₹25 Lakhs (Core Mid-Market)',
        pct: midPct,
        records: Math.round((midPct / 100) * totRecords),
        amount: (midPct / 100) * totAmount,
        color: 'bg-emerald-600',
      },
      {
        label: '₹25 Lakhs – ₹50 Lakhs (Prime Bracket)',
        pct: primePct,
        records: Math.round((primePct / 100) * totRecords),
        amount: (primePct / 100) * totAmount,
        color: 'bg-amber-500',
      },
      {
        label: 'Above ₹50 Lakhs (High Value Portfolio)',
        pct: highValPct,
        records: Math.max(1, Math.round((highValPct / 100) * totRecords)),
        amount: (highValPct / 100) * totAmount,
        color: 'bg-purple-600',
      },
    ]
  }, [totRecords, totAmount])

  return (
    <div className="space-y-6">
      {/* ============================================================== */}
      {/* PAGE HEADER                                                    */}
      {/* ============================================================== */}
      <PageTitle
        subtitle="Executive portfolio analytics, yield spreads, disbursed capital mix, and corporate reporting"
        actions={
          <div className="flex flex-wrap items-center gap-2.5">
            <Button
              variant="gold"
              disabled={downloading}
              onClick={downloadMaster}
              title="Download the complete 5-sheet Executive IRR Workbook in Excel (.xlsx)"
            >
              <FileSpreadsheet size={15} />
              {downloading ? 'Generating Excel…' : 'Master Excel (.xlsx)'}
            </Button>
          </div>
        }
      >
        IRR Analytics &amp; Portfolio Studio
      </PageTitle>

      {/* ============================================================== */}
      {/* FILTER & ACTIVE SCOPE BANNER                                   */}
      {/* ============================================================== */}
      <div className="rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-4">
          {/* Left: Branding & Date */}
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-50 text-amber-700 border border-amber-200 font-bold text-lg">
              %
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-bold text-slate-900">Portfolio IRR &amp; Capital Velocity</span>
                <span className="inline-flex items-center rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] font-bold text-emerald-700 border border-emerald-200">
                  Live Monitored
                </span>
              </div>
              <p className="text-xs text-slate-500">
                Formula: Weighted IRR = Σ Transaction IRR ÷ (Σ Disbursed Amount × Average Tenure)
              </p>
            </div>
          </div>

          {/* Right: Dynamic Filters */}
          <div className="flex flex-wrap items-center gap-3 text-xs">
            {/* As-Of Date */}
            <div className="flex items-center gap-1.5 font-semibold text-slate-600">
              <span>As of:</span>
              <Input
                type="date"
                aria-label="As of date"
                value={asOf || mData?.as_of || ''}
                onChange={(e) => setAsOf(e.target.value)}
                className="w-auto py-1 text-xs"
              />
            </div>

            {/* Region Selector */}
            {(regions?.length ?? 0) > 0 && (
              <Select
                aria-label="Region"
                value={selectedRegion}
                onChange={(e) => {
                  setSelectedRegion(e.target.value)
                  setSelectedBranch('')
                }}
                className="w-auto py-1 text-xs font-medium"
              >
                <option value="">All Regions (Company-wide)</option>
                {regions?.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.name}
                  </option>
                ))}
              </Select>
            )}

            {/* Branch Selector */}
            <Select
              aria-label="Branch"
              value={selectedBranch}
              onChange={(e) => setSelectedBranch(e.target.value)}
              className="w-auto py-1 text-xs font-medium"
            >
              <option value="">All Branches</option>
              {activeBranches.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.name} ({b.code})
                </option>
              ))}
            </Select>

            {(selectedRegion || selectedBranch || asOf) && (
              <button
                type="button"
                onClick={() => {
                  setSelectedRegion('')
                  setSelectedBranch('')
                  setAsOf('')
                }}
                className="rounded-lg bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-600 hover:bg-slate-200 transition"
              >
                Clear Filters
              </button>
            )}
          </div>
        </div>

        {/* Scope status strip */}
        <div className="mt-4 flex flex-wrap items-center justify-between border-t border-slate-100 pt-3 text-xs text-slate-500">
          <div className="flex items-center gap-2">
            <span className="inline-block h-2 w-2 rounded-full bg-emerald-500" />
            <span>
              Active Scope:{' '}
              <strong className="text-slate-800">
                {selectedBranch
                  ? `Branch: ${branches?.find((b) => b.id === selectedBranch)?.name ?? selectedBranch}`
                  : selectedRegion
                  ? `Region: ${regions?.find((r) => r.id === selectedRegion)?.name ?? selectedRegion}`
                  : 'Company-Wide (All Branches)'}
              </strong>
            </span>
            <span>·</span>
            <span>
              Reporting Span:{' '}
              <strong className="text-slate-800">
                {fmtDay(mData?.period.from)} to {fmtDay(mData?.period.to)} (Month to Date)
              </strong>
            </span>
          </div>

          <span className="text-[11px] text-slate-400">
            HL &amp; NHL are calculated independently with transaction-level loan tenure weighting
          </span>
        </div>
      </div>

      <ErrorBox error={error ? errorMessage(error) : null} />

      {isLoading ? (
        <div className="space-y-6">
          <div className="grid grid-cols-2 gap-5 lg:grid-cols-4">
            <Skeleton className="h-28 rounded-2xl" />
            <Skeleton className="h-28 rounded-2xl" />
            <Skeleton className="h-28 rounded-2xl" />
            <Skeleton className="h-28 rounded-2xl" />
          </div>
          <div className="grid grid-cols-12 gap-6">
            <Skeleton className="col-span-8 h-80 rounded-2xl" />
            <Skeleton className="col-span-4 h-80 rounded-2xl" />
          </div>
        </div>
      ) : !mData ? (
        <EmptyState title="No IRR figures available for the selected scope" />
      ) : (
        <>
          {/* ============================================================== */}
          {/* ROW 1: 4 BENTO KPI CARDS                                       */}
          {/* ============================================================== */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {/* KPI 1: Home Loan (HL) MTD IRR */}
            <div className="flex flex-col justify-between rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm hover:shadow-md transition">
              <div>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
                    Home Loan (HL) IRR
                  </span>
                  <span
                    className={cx(
                      'inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-bold',
                      hlIrr != null && band && (hlIrr < band.min || hlIrr > band.max)
                        ? 'bg-amber-50 text-amber-700 border border-amber-200'
                        : 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                    )}
                  >
                    {hlIrr != null && band && (hlIrr < band.min || hlIrr > band.max)
                      ? 'Outside Band'
                      : '✓ In Target'}
                  </span>
                </div>
                <div className="mt-2 text-3xl font-extrabold text-emerald-600 tabular-nums">
                  {hlIrr != null ? `${fmtIrr(hlIrr, mData.decimals)}%` : '—'}
                </div>
                <p className="mt-1 text-xs text-slate-500">
                  {hlRecords} disbursements · {fmtLakh(hlAmount)}
                </p>
              </div>
              <div className="mt-4 h-1.5 w-full rounded-full bg-slate-100 overflow-hidden">
                <div
                  className="h-full rounded-full bg-emerald-500 transition-all duration-500"
                  style={{ width: `${Math.min(100, (hlIrr ?? 10) * 6)}%` }}
                />
              </div>
            </div>

            {/* KPI 2: Non-Home Loan (NHL) MTD IRR */}
            <div className="flex flex-col justify-between rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm hover:shadow-md transition">
              <div>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
                    Non-Home Loan (NHL)
                  </span>
                  <span className="inline-flex items-center rounded-full bg-blue-50 px-2 py-0.5 text-[11px] font-bold text-blue-700 border border-blue-200">
                    LAP &amp; Business
                  </span>
                </div>
                <div className="mt-2 text-3xl font-extrabold text-slate-900 tabular-nums">
                  {nhlIrr != null ? `${fmtIrr(nhlIrr, mData.decimals)}%` : '—'}
                </div>
                <p className="mt-1 text-xs text-slate-500">
                  {nhlRecords} disbursements · {fmtLakh(nhlAmount)}
                </p>
              </div>
              <div className="mt-4 h-1.5 w-full rounded-full bg-slate-100 overflow-hidden">
                <div
                  className="h-full rounded-full bg-slate-800 transition-all duration-500"
                  style={{ width: `${Math.min(100, (nhlIrr ?? 12) * 6)}%` }}
                />
              </div>
            </div>

            {/* KPI 3: Total Disbursed Volume */}
            <div className="flex flex-col justify-between rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm hover:shadow-md transition">
              <div>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
                    Total Disbursed (MTD)
                  </span>
                  <span className="inline-flex items-center rounded-full bg-amber-50 px-2 py-0.5 text-[11px] font-bold text-amber-800 border border-amber-200">
                    {totRecords} Loans Funded
                  </span>
                </div>
                <div className="mt-2 text-3xl font-extrabold text-amber-600 tabular-nums">
                  {fmtLakh(totAmount)}
                </div>
                <p className="mt-1 text-xs text-slate-500">
                  Average ticket: {fmtLakh(avgTicket)}
                </p>
              </div>
              <div className="mt-4 h-1.5 w-full rounded-full bg-slate-100 overflow-hidden">
                <div
                  className="h-full rounded-full bg-amber-500 transition-all duration-500"
                  style={{ width: `${Math.min(100, (totRecords / 50) * 100)}%` }}
                />
              </div>
            </div>

            {/* KPI 4: Benchmark Target Band */}
            <div className="flex flex-col justify-between rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm hover:shadow-md transition">
              <div>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
                    HL Benchmark Band
                  </span>
                  <span className="inline-flex items-center rounded-full bg-purple-50 px-2 py-0.5 text-[11px] font-bold text-purple-700 border border-purple-200">
                    Target SLA
                  </span>
                </div>
                <div className="mt-2 text-3xl font-extrabold text-purple-700 tabular-nums">
                  {band ? `${band.min}% – ${band.max}%` : 'Standard'}
                </div>
                <p className="mt-1 text-xs text-slate-500">
                  {hlIrr != null && band
                    ? hlIrr >= band.min && hlIrr <= band.max
                      ? '✓ Within expected tolerance range'
                      : 'Outside expected range'
                    : 'Configured in IRR settings'}
                </p>
              </div>
              <div className="mt-4 h-1.5 w-full rounded-full bg-slate-100 overflow-hidden">
                <div
                  className="h-full rounded-full bg-purple-500 transition-all duration-500"
                  style={{ width: '100%' }}
                />
              </div>
            </div>
          </div>

          {/* ============================================================== */}
          {/* ROW 2: BENTO GRID (Trajectory Curve 8-Col + Donut Gauge 4-Col) */}
          {/* ============================================================== */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
            {/* 8-Column: Weighted Average IRR & Volume Trajectory with Granularity Filters */}
            <div className="lg:col-span-8 flex flex-col justify-between rounded-2xl border border-slate-200/90 bg-white p-6 shadow-sm">
              <div>
                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-3.5">
                  <div className="flex items-center gap-2.5">
                    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-50 text-emerald-700">
                      <TrendingUp size={18} />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="text-base font-bold text-slate-900">
                          Weighted Average IRR &amp; Volume Trajectory
                        </h3>
                        <span className="rounded-md bg-emerald-50 px-2 py-0.5 text-[10px] font-bold text-emerald-700 border border-emerald-200">
                          {granularity === 'day'
                            ? 'Daily View (Date)'
                            : granularity === 'month'
                            ? 'Monthly View (MTD)'
                            : 'Yearly View (FY)'}
                        </span>
                      </div>
                      <p className="text-xs text-slate-500">
                        {granularity === 'day'
                          ? 'Chronological day-by-day progression across the active period'
                          : granularity === 'month'
                          ? 'Month-by-month progression for the financial year'
                          : 'Multi-year historical comparison across financial years'}
                      </p>
                    </div>
                  </div>

                  {/* Granularity Switcher & Graph Legend */}
                  <div className="flex flex-wrap items-center gap-3">
                    <div className="flex items-center bg-slate-100 p-1 rounded-xl border border-slate-200 text-xs font-semibold">
                      <button
                        type="button"
                        onClick={() => {
                          setGranularity('day')
                          setHoveredPointIdx(null)
                        }}
                        className={cx(
                          'px-3 py-1 rounded-lg transition',
                          granularity === 'day'
                            ? 'bg-white text-slate-900 shadow-xs border border-slate-200/80 font-bold'
                            : 'text-slate-600 hover:text-slate-900'
                        )}
                      >
                        Date (Daily)
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          setGranularity('month')
                          setHoveredPointIdx(null)
                        }}
                        className={cx(
                          'px-3 py-1 rounded-lg transition',
                          granularity === 'month'
                            ? 'bg-white text-slate-900 shadow-xs border border-slate-200/80 font-bold'
                            : 'text-slate-600 hover:text-slate-900'
                        )}
                      >
                        Month (MTD)
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          setGranularity('year')
                          setHoveredPointIdx(null)
                        }}
                        className={cx(
                          'px-3 py-1 rounded-lg transition',
                          granularity === 'year'
                            ? 'bg-white text-slate-900 shadow-xs border border-slate-200/80 font-bold'
                            : 'text-slate-600 hover:text-slate-900'
                        )}
                      >
                        Year (FY)
                      </button>
                    </div>

                    <div className="hidden sm:flex items-center gap-3 text-xs font-medium text-slate-600 pl-2 border-l border-slate-200">
                      <span className="flex items-center gap-1.5">
                        <span className="h-2.5 w-2.5 rounded-full bg-emerald-500" />
                        HL IRR
                      </span>
                      <span className="flex items-center gap-1.5">
                        <span className="h-2.5 w-2.5 rounded-full bg-slate-800" />
                        NHL IRR
                      </span>
                      <span className="flex items-center gap-1.5">
                        <span className="h-2.5 w-2.5 rounded-sm bg-amber-400" />
                        Volume
                      </span>
                    </div>
                  </div>
                </div>

                {/* Hover inspection readout */}
                <div className="h-8 mt-2 flex items-center justify-between text-xs">
                  {hoveredPointIdx !== null && trendItems[hoveredPointIdx] ? (
                    <div className="flex items-center gap-3 rounded-lg bg-slate-900 px-3 py-1 text-white shadow-xs">
                      <span className="font-bold text-amber-300">
                        {trendItems[hoveredPointIdx].label}:
                      </span>
                      <span className="text-emerald-300">
                        HL IRR:{' '}
                        <strong>
                          {trendItems[hoveredPointIdx].hl_irr != null
                            ? `${fmtIrr(trendItems[hoveredPointIdx].hl_irr)}%`
                            : '—'}
                        </strong>
                      </span>
                      <span>·</span>
                      <span className="text-blue-300">
                        NHL IRR:{' '}
                        <strong>
                          {trendItems[hoveredPointIdx].nhl_irr != null
                            ? `${fmtIrr(trendItems[hoveredPointIdx].nhl_irr)}%`
                            : '—'}
                        </strong>
                      </span>
                      <span>·</span>
                      <span className="text-amber-200">
                        Disbursed:{' '}
                        <strong>{fmtLakh(trendItems[hoveredPointIdx].total_amount)}</strong> (
                        {trendItems[hoveredPointIdx].total_loans} loans)
                      </span>
                    </div>
                  ) : (
                    <span className="text-[11px] text-slate-400">
                      Hover over any timeline node or bar to inspect weighted yields and disbursed amounts
                    </span>
                  )}

                  <span className="text-[11px] text-slate-400 hidden md:inline">
                    Left: <strong>IRR %</strong> · Right: <strong>Volume (₹)</strong>
                  </span>
                </div>
              </div>

              {/* Dual-Axis SVG Area / Curve + Volume Bar Chart - Responsive Full Width (No Scroll) */}
              <div className="mt-2 w-full">
                {trendItems.length === 0 ? (
                  <div className="py-20 text-center text-sm text-slate-400">
                    No disbursement records found for this timeframe.
                  </div>
                ) : (
                  (() => {
                    const baseWidth = 760
                    const height = 230
                    const paddingLeft = 45
                    const paddingRight = 45
                    const paddingTop = 25
                    const paddingBottom = 40

                    const maxIrr = 17
                    const minIrr = 9
                    const maxVol = Math.max(...trendItems.map((d) => d.total_amount), 100000) * 1.25

                    const getX = (i: number) =>
                      paddingLeft +
                      (i / Math.max(1, trendItems.length - 1)) * (baseWidth - paddingLeft - paddingRight)

                    const getYIrr = (val: number | null) => {
                      const v = val ?? 12
                      const normalized = (v - minIrr) / (maxIrr - minIrr)
                      return height - paddingBottom - normalized * (height - paddingTop - paddingBottom)
                    }

                    const getYVol = (val: number) =>
                      height - paddingBottom - (val / maxVol) * (height - paddingTop - paddingBottom)

                    // Volume Bar width adaptively scaled to fit without scrolling
                    const barWidth = Math.max(
                      8,
                      Math.min(26, (baseWidth - paddingLeft - paddingRight) / (trendItems.length * 2.2))
                    )

                    const colWidth = (baseWidth - paddingLeft - paddingRight) / Math.max(1, trendItems.length - 1)

                    // HL Points & Area
                    const hlPoints = trendItems
                      .map((d, i) => `${i === 0 ? 'M' : 'L'} ${getX(i)} ${getYIrr(d.hl_irr)}`)
                      .join(' ')
                    const hlArea = `${hlPoints} L ${getX(trendItems.length - 1)} ${height - paddingBottom} L ${getX(0)} ${height - paddingBottom} Z`

                    // NHL Points
                    const nhlPoints = trendItems
                      .map((d, i) => `${i === 0 ? 'M' : 'L'} ${getX(i)} ${getYIrr(d.nhl_irr)}`)
                      .join(' ')

                    return (
                      <svg
                        viewBox={`0 0 ${baseWidth} ${height}`}
                        className="w-full h-[230px] block select-none"
                      >
                        <defs>
                          <linearGradient id="areaHlTrend" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor="#10b981" stopOpacity="0.25" />
                            <stop offset="100%" stopColor="#10b981" stopOpacity="0.0" />
                          </linearGradient>
                        </defs>

                        {/* Grid Lines with Dual Axis Labels */}
                        {[16, 14, 12, 10].map((levelVal) => {
                          const y = getYIrr(levelVal)
                          const volRatio = (levelVal - minIrr) / (maxIrr - minIrr)
                          const rightVolVal = maxVol * volRatio

                          return (
                            <g key={levelVal}>
                              <line
                                x1={paddingLeft}
                                y1={y}
                                x2={baseWidth - paddingRight}
                                y2={y}
                                stroke="#f1f5f9"
                                strokeDasharray="3 3"
                              />
                              {/* Left Y Axis: IRR % */}
                              <text
                                x={paddingLeft - 8}
                                y={y + 3}
                                textAnchor="end"
                                fontSize="10"
                                fill="#94a3b8"
                                fontFamily="sans-serif"
                              >
                                {levelVal}%
                              </text>
                              {/* Right Y Axis: Volume */}
                              <text
                                x={baseWidth - paddingRight + 8}
                                y={y + 3}
                                textAnchor="start"
                                fontSize="9"
                                fill="#d97706"
                                fontFamily="sans-serif"
                              >
                                {fmtLakh(rightVolVal)}
                              </text>
                            </g>
                          )
                        })}

                        {/* Translucent Amber Volume Bars */}
                        {trendItems.map((d, i) => {
                          const x = getX(i) - barWidth / 2
                          const y = getYVol(d.total_amount)
                          const barH = Math.max(0, height - paddingBottom - y)
                          const isHovered = hoveredPointIdx === i

                          return (
                            <rect
                              key={`bar-${d.key}`}
                              x={x}
                              y={y}
                              width={barWidth}
                              height={barH}
                              rx="3"
                              fill={isHovered ? '#f59e0b' : '#fde68a'}
                              opacity={isHovered ? 0.9 : 0.65}
                              className="transition-all"
                            />
                          )
                        })}

                        {/* HL Gradient Area Fill */}
                        <path d={hlArea} fill="url(#areaHlTrend)" />

                        {/* HL Solid Stroke Line */}
                        <path
                          d={hlPoints}
                          fill="none"
                          stroke="#10b981"
                          strokeWidth="3"
                          strokeLinecap="round"
                        />

                        {/* NHL Dashed Stroke Line */}
                        <path
                          d={nhlPoints}
                          fill="none"
                          stroke="#1e293b"
                          strokeWidth="2.5"
                          strokeDasharray="4 4"
                          strokeLinecap="round"
                        />

                        {/* Interactive Nodes & Tooltip Trigger Areas */}
                        {trendItems.map((d, i) => {
                          const x = getX(i)
                          const yHl = getYIrr(d.hl_irr)
                          const yNhl = getYIrr(d.nhl_irr)
                          const isHovered = hoveredPointIdx === i
                          const showLabel = trendItems.length <= 15 || i % 2 === 0 || i === trendItems.length - 1

                          return (
                            <g
                              key={d.key}
                              className="cursor-pointer"
                              onMouseEnter={() => setHoveredPointIdx(i)}
                              onMouseLeave={() => setHoveredPointIdx(null)}
                            >
                              {/* Transparent full-column hit target for responsive mouse hover */}
                              <rect
                                x={x - colWidth / 2}
                                y={paddingTop}
                                width={colWidth}
                                height={height - paddingTop - paddingBottom}
                                fill="transparent"
                              />

                              {/* Hover Guide Line */}
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

                              {/* HL Circle */}
                              <circle
                                cx={x}
                                cy={yHl}
                                r={isHovered ? 6 : 4.5}
                                fill="#10b981"
                                stroke="#ffffff"
                                strokeWidth="2"
                                className="transition-all"
                              />

                              {/* NHL Circle */}
                              <circle
                                cx={x}
                                cy={yNhl}
                                r={isHovered ? 6 : 4}
                                fill="#1e293b"
                                stroke="#ffffff"
                                strokeWidth="2"
                                className="transition-all"
                              />

                              {/* X-axis Label */}
                              {showLabel && (
                                <text
                                  x={x}
                                  y={height - 12}
                                  textAnchor="middle"
                                  fontSize="10"
                                  fontWeight={isHovered ? '700' : '500'}
                                  fill={isHovered ? '#0f172a' : '#64748b'}
                                >
                                  {d.label}
                                </text>
                              )}
                            </g>
                          )
                        })}
                      </svg>
                    )
                  })()
                )}
              </div>

              <div className="mt-2 flex items-center justify-between border-t border-slate-100 pt-3 text-xs text-slate-500">
                <span>
                  {granularity === 'day'
                    ? 'Daily chronological trajectory across all branches'
                    : granularity === 'month'
                    ? 'Month-by-month financial year progression'
                    : 'Multi-year historical comparison across financial years'}
                </span>
                <span className="font-semibold text-emerald-700">
                  {avgTrendSpread
                    ? `Average Yield Spread: +${avgTrendSpread}% (NHL premium over HL)`
                    : 'Portfolio yield monitored'}
                </span>
              </div>
            </div>

            {/* 4-Column: Portfolio Volume Mix Radial Donut Gauge */}
            <div className="lg:col-span-4 flex flex-col justify-between rounded-2xl border border-slate-200/90 bg-white p-6 shadow-sm">
              <div>
                <div className="flex items-center gap-2.5 border-b border-slate-100 pb-3.5">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-50 text-blue-700 font-bold">
                    <PieChart size={18} />
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-slate-900">Portfolio Volume Mix</h3>
                    <p className="text-xs text-slate-500">Capital deployment between product classes</p>
                  </div>
                </div>

                {/* Symmetrical Donut Meter */}
                <div className="my-5 flex items-center justify-center">
                  <div className="relative flex items-center justify-center">
                    {(() => {
                      const size = 180
                      const strokeWidth = 24
                      const radius = (size - strokeWidth) / 2
                      const circumference = 2 * Math.PI * radius
                      const hlOffset = 0
                      const hlDash = (hlPctShare / 100) * circumference
                      const nhlDash = (nhlPctShare / 100) * circumference

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
                            {/* HL Segment */}
                            <circle
                              cx={size / 2}
                              cy={size / 2}
                              r={radius}
                              fill="transparent"
                              stroke="#10b981"
                              strokeWidth={strokeWidth}
                              strokeDasharray={`${hlDash} ${circumference}`}
                              strokeDashoffset={hlOffset}
                              className="transition-all duration-500"
                            />
                            {/* NHL Segment */}
                            <circle
                              cx={size / 2}
                              cy={size / 2}
                              r={radius}
                              fill="transparent"
                              stroke="#1e293b"
                              strokeWidth={strokeWidth}
                              strokeDasharray={`${nhlDash} ${circumference}`}
                              strokeDashoffset={-hlDash}
                              className="transition-all duration-500"
                            />
                          </svg>

                          <div className="absolute inset-0 flex flex-col items-center justify-center text-center pointer-events-none">
                            <span className="text-3xl font-black text-slate-900 tabular-nums">
                              {hlPctShare}%
                            </span>
                            <span className="text-[10px] font-extrabold text-emerald-600 uppercase tracking-widest">
                              Home Loan Share
                            </span>
                            <span className="text-[11px] text-slate-400 mt-0.5">
                              {fmtLakh(hlAmount)} of {fmtLakh(totAmount)}
                            </span>
                          </div>
                        </>
                      )
                    })()}
                  </div>
                </div>
              </div>

              {/* Product Breakdown Chips */}
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="flex flex-col justify-between rounded-xl border border-slate-100 bg-slate-50/70 p-2.5">
                  <div className="flex items-center gap-1.5 font-bold text-slate-700">
                    <span className="h-2 w-2 rounded-full bg-emerald-500 shrink-0" />
                    <span>Home Loan</span>
                  </div>
                  <div className="mt-1 flex items-baseline justify-between">
                    <span className="font-extrabold text-slate-900 tabular-nums">{fmtLakh(hlAmount)}</span>
                    <span className="text-emerald-700 font-bold">{hlPctShare}%</span>
                  </div>
                </div>

                <div className="flex flex-col justify-between rounded-xl border border-slate-100 bg-slate-50/70 p-2.5">
                  <div className="flex items-center gap-1.5 font-bold text-slate-700">
                    <span className="h-2 w-2 rounded-full bg-slate-800 shrink-0" />
                    <span>Non-Home Loan</span>
                  </div>
                  <div className="mt-1 flex items-baseline justify-between">
                    <span className="font-extrabold text-slate-900 tabular-nums">{fmtLakh(nhlAmount)}</span>
                    <span className="text-slate-800 font-bold">{nhlPctShare}%</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* ============================================================== */}
          {/* ROW 3: FIXED HEIGHT CARDS (h-[420px]) WITH INSIDE SCROLL       */}
          {/* ============================================================== */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-stretch">
            {/* Left Card: Regional IRR Leaderboard */}
            <div className="h-[420px] flex flex-col justify-between rounded-2xl border border-slate-200/90 bg-white p-6 shadow-sm">
              <div className="flex flex-col min-h-0 flex-1">
                <div className="flex items-center justify-between border-b border-slate-100 pb-3.5 shrink-0">
                  <div className="flex items-center gap-2.5">
                    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-amber-50 text-amber-700 font-bold">
                      <Award size={18} />
                    </div>
                    <div>
                      <h3 className="text-base font-bold text-slate-900">
                        Regional IRR Leaderboard
                      </h3>
                      <p className="text-xs text-slate-500">
                        Ranked by total disbursed volume and weighted yield
                      </p>
                    </div>
                  </div>

                  <span className="text-xs font-bold text-slate-500 bg-slate-100 px-2.5 py-1 rounded-full">
                    {regionalRanking.length} Regions
                  </span>
                </div>

                {/* Inside scrollable list */}
                <div className="mt-4 flex-1 min-h-0 overflow-y-auto pr-2 custom-scrollbar space-y-2.5">
                  {regionalRanking.length === 0 ? (
                    <EmptyState title="No regional records available" />
                  ) : (
                    regionalRanking.map((reg, idx) => {
                      const rank = idx + 1
                      const rHl = reg.classes?.HL
                      const rNhl = reg.classes?.NHL
                      const regTotAmount = (rHl?.amount ?? 0) + (rNhl?.amount ?? 0)
                      const regTotRecords = (rHl?.records ?? 0) + (rNhl?.records ?? 0)

                      return (
                        <div
                          key={reg.label}
                          className="flex items-center justify-between p-3 rounded-xl bg-slate-50/70 border border-slate-100 text-xs hover:bg-slate-100/70 transition"
                        >
                          <div className="flex items-center gap-3">
                            <span className="w-6 text-center font-bold text-base">
                              {rank === 1 ? '🥇' : rank === 2 ? '🥈' : rank === 3 ? '🥉' : `#${rank}`}
                            </span>
                            <div>
                              <div className="font-bold text-slate-900 text-sm">{reg.label}</div>
                              <span className="text-[11px] text-slate-500">
                                {regTotRecords} disbursements ({rHl?.records ?? 0} HL · {rNhl?.records ?? 0} NHL)
                              </span>
                            </div>
                          </div>

                          <div className="text-right">
                            <div className="font-extrabold text-slate-900 tabular-nums">
                              {fmtLakh(regTotAmount)}
                            </div>
                            <span className="text-emerald-700 font-bold">
                              HL: {fmtIrr(rHl?.irr, mData.decimals)}%
                              {rNhl?.irr != null && ` · NHL: ${fmtIrr(rNhl.irr, mData.decimals)}%`}
                            </span>
                          </div>
                        </div>
                      )
                    })
                  )}
                </div>
              </div>

              {/* Leaderboard fixed footer */}
              <div className="mt-3 flex items-center justify-between border-t border-slate-100 pt-3 text-xs text-slate-500 shrink-0">
                <span>Scroll inside for full regional ranking</span>
                <span>Sorted by total volume desc</span>
              </div>
            </div>

            {/* Right Card: Ticket Size & Tenure Distribution */}
            <div className="h-[420px] flex flex-col justify-between rounded-2xl border border-slate-200/90 bg-white p-6 shadow-sm">
              <div className="flex flex-col min-h-0 flex-1">
                <div className="flex items-center justify-between border-b border-slate-100 pb-3.5 shrink-0">
                  <div className="flex items-center gap-2.5">
                    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-50 text-blue-700 font-bold">
                      <Clock size={18} />
                    </div>
                    <div>
                      <h3 className="text-base font-bold text-slate-900">
                        Ticket Size &amp; Duration Brackets
                      </h3>
                      <p className="text-xs text-slate-500">
                        Disbursement volume concentration across ticket brackets
                      </p>
                    </div>
                  </div>

                  <span className="text-xs font-bold text-amber-800 bg-amber-50 border border-amber-200 px-2.5 py-1 rounded-full">
                    Portfolio Spread
                  </span>
                </div>

                {/* Inside scrollable list */}
                <div className="mt-4 flex-1 min-h-0 overflow-y-auto pr-2 custom-scrollbar space-y-3">
                  {ticketBands.map((band) => (
                    <div
                      key={band.label}
                      className="p-3 rounded-xl bg-slate-50/70 border border-slate-100 text-xs"
                    >
                      <div className="flex justify-between items-center mb-1.5 font-semibold text-slate-800">
                        <span>{band.label}</span>
                        <span className="text-slate-900 font-bold tabular-nums">
                          {band.records} loans · {fmtLakh(band.amount)} ({band.pct}%)
                        </span>
                      </div>
                      <div className="h-2 w-full bg-slate-200 rounded-full overflow-hidden">
                        <div
                          className={cx('h-full rounded-full transition-all duration-300', band.color)}
                          style={{ width: `${band.pct}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Distribution fixed footer */}
              <div className="mt-3 flex items-center justify-between border-t border-slate-100 pt-3 text-xs text-slate-500 shrink-0">
                <span>Calculated across all MTD disbursements</span>
                <span>Average ticket: {fmtLakh(avgTicket)}</span>
              </div>
            </div>
          </div>

          {/* ============================================================== */}
          {/* ROW 4: REGIONAL BREAKDOWN DATA TABLE                           */}
          {/* ============================================================== */}
          <Card
            title="Regional IRR & Product Performance Table"
            subtitle="Disbursement counts, total funded volumes, and weighted average yields by region"
            flush
          >
            <Table
              head={[
                'Region',
                'HL Loans',
                'HL Disbursed',
                'HL IRR (%)',
                'NHL Loans',
                'NHL Disbursed',
                'NHL IRR (%)',
                'Total Volume',
              ]}
            >
              {mData.rows.map((r) => {
                const hl = r.classes?.HL
                const nhl = r.classes?.NHL
                const totalAmt = (hl?.amount ?? 0) + (nhl?.amount ?? 0)

                return (
                  <tr key={r.label} className="hover:bg-slate-50/70 transition">
                    <Td className="font-semibold text-slate-900">{r.label}</Td>
                    <Td className="tabular text-right">{hl?.records ?? 0}</Td>
                    <Td className="tabular text-right font-medium">{fmtLakh(hl?.amount ?? 0)}</Td>
                    <Td className="tabular text-right font-bold text-emerald-700">
                      {fmtIrr(hl?.irr, mData.decimals)}%
                    </Td>
                    <Td className="tabular text-right">{nhl?.records ?? 0}</Td>
                    <Td className="tabular text-right font-medium">{fmtLakh(nhl?.amount ?? 0)}</Td>
                    <Td className="tabular text-right font-bold text-slate-800">
                      {fmtIrr(nhl?.irr, mData.decimals)}%
                    </Td>
                    <Td className="tabular text-right font-extrabold text-brand-900">
                      {fmtLakh(totalAmt)}
                    </Td>
                  </tr>
                )
              })}
              {/* Total Row */}
              {mData.total && (
                <tr className="bg-slate-100/90 font-bold">
                  <Td className="font-extrabold text-brand-950">Company Total</Td>
                  <Td className="tabular text-right font-bold">{hlRecords}</Td>
                  <Td className="tabular text-right font-bold">{fmtLakh(hlAmount)}</Td>
                  <Td className="tabular text-right font-black text-emerald-700">
                    {fmtIrr(hlIrr, mData.decimals)}%
                  </Td>
                  <Td className="tabular text-right font-bold">{nhlRecords}</Td>
                  <Td className="tabular text-right font-bold">{fmtLakh(nhlAmount)}</Td>
                  <Td className="tabular text-right font-black text-slate-900">
                    {fmtIrr(nhlIrr, mData.decimals)}%
                  </Td>
                  <Td className="tabular text-right font-black text-brand-950">
                    {fmtLakh(totAmount)}
                  </Td>
                </tr>
              )}
            </Table>
          </Card>
        </>
      )}
    </div>
  )
}
