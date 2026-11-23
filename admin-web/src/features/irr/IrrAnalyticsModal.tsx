import { useQuery } from '@tanstack/react-query'
import {
  Award,
  BarChart3,
  CheckCircle2,
  Download,
  FileSpreadsheet,
  Layers,
  Percent,
  PieChart,
  RefreshCw,
  TrendingUp,
  TriangleAlert,
  X,
} from 'lucide-react'
import { useState } from 'react'
import { Button, Card, cx, Dialog, EmptyState, ErrorBox, Skeleton, StatCard, Table, Td } from '../../components/ui'
import { api, errorMessage } from '../../services/api'
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

interface Props {
  asOf: string
  regionId?: string
  branchId?: string
  onClose: () => void
}

type TabType = 'overview' | 'regions' | 'workbook'

const fmtLakh = (val: number) => {
  if (val >= 10000000) return `₹${(val / 10000000).toFixed(2)} Cr`
  if (val >= 100000) return `₹${(val / 100000).toFixed(2)} L`
  return `₹${Math.round(val).toLocaleString('en-IN')}`
}

export function IrrAnalyticsModal({ asOf, regionId, branchId, onClose }: Props) {
  const [downloading, setDownloading] = useState(false)
  const [exportError, setExportError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<TabType>('overview')

  // 1. Fetch Month by Product data (HL and NHL split for company and regions)
  const monthQuery = useQuery({
    queryKey: ['irr', 'analytics-month', asOf, regionId, branchId],
    queryFn: async () =>
      (
        await api.get<MonthReport>('/irr/report/month-by-product', {
          params: { as_of: asOf || undefined, region_id: regionId || undefined, branch_id: branchId || undefined, level: 'region' },
        })
      ).data,
  })

  // 2. Fetch Period data for HL to get bands and periods
  const periodQuery = useQuery({
    queryKey: ['irr', 'analytics-periods', asOf, regionId, branchId],
    queryFn: async () =>
      (
        await api.get<PeriodReport>('/irr/report', {
          params: { as_of: asOf || undefined, region_id: regionId || undefined, branch_id: branchId || undefined, product: 'HL', level: 'company' },
        })
      ).data,
  })

  const downloadMaster = async () => {
    setExportError(null)
    setDownloading(true)
    try {
      const res = await api.get('/irr/export/complete-workbook', {
        params: { as_of: asOf || undefined, region_id: regionId || undefined, branch_id: branchId || undefined },
        responseType: 'blob',
      })
      const href = URL.createObjectURL(res.data as Blob)
      const a = document.createElement('a')
      a.href = href
      a.download = `IRR_Master_Workbook_${asOf || 'latest'}.xlsx`
      a.click()
      setTimeout(() => URL.revokeObjectURL(href), 1000)
    } catch (e) {
      setExportError(errorMessage(e))
    } finally {
      setDownloading(false)
    }
  }

  const mData = monthQuery.data
  const pData = periodQuery.data
  const isLoading = monthQuery.isLoading || periodQuery.isLoading

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
  const band = pData?.band

  return (
    <Dialog title="Executive IRR & Disbursement Analytics" onClose={onClose} wide>
      <div className="space-y-5">
        {/* Banner with Date & 1-Click Master Excel Export */}
        <div className="flex flex-wrap items-center justify-between gap-4 rounded-xl bg-gradient-to-r from-brand-950 via-brand-900 to-brand-800 p-5 text-white shadow-md">
          <div>
            <div className="flex items-center gap-2">
              <span className="rounded-full bg-gold-400/20 px-2.5 py-0.5 text-xs font-bold text-gold-300">
                EXECUTIVE ANALYTICS
              </span>
              <span className="text-xs text-brand-200">As of reporting date: {fmtDay(asOf || mData?.as_of)}</span>
            </div>
            <h2 className="mt-1 text-xl font-bold">Portfolio IRR Performance & Disbursed Volume</h2>
            <p className="text-xs text-brand-200">
              Interactive graphical analytics with instant 5-sheet corporate Excel export (.xlsx)
            </p>
          </div>

          <Button
            variant="gold"
            disabled={downloading}
            onClick={downloadMaster}
            title="Download the full 5-sheet Executive IRR Workbook in Excel format"
          >
            <FileSpreadsheet size={16} />
            {downloading ? 'Generating Excel…' : 'Master Excel (.xlsx)'}
          </Button>
        </div>

        <ErrorBox error={monthQuery.error ? errorMessage(monthQuery.error) : exportError} />

        {isLoading ? (
          <div className="space-y-4">
            <div className="grid grid-cols-4 gap-4">
              <Skeleton className="h-24" />
              <Skeleton className="h-24" />
              <Skeleton className="h-24" />
              <Skeleton className="h-24" />
            </div>
            <Skeleton className="h-64" />
          </div>
        ) : !mData ? (
          <EmptyState title="No IRR data available for this reporting period" />
        ) : (
          <>
            {/* Top 4 KPI Metric Cards */}
            <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
              <StatCard
                label="Home Loan (HL) MTD IRR"
                value={hlIrr != null ? `${fmtIrr(hlIrr)}%` : '—'}
                tone={hlIrr != null && band && (hlIrr < band.min || hlIrr > band.max) ? 'gold' : 'green'}
                hint={`${hlRecords} disbursements · ${fmtLakh(hlAmount)}`}
              />
              <StatCard
                label="Non-Home Loan (NHL) MTD IRR"
                value={nhlIrr != null ? `${fmtIrr(nhlIrr)}%` : '—'}
                tone="navy"
                hint={`${nhlRecords} disbursements · ${fmtLakh(nhlAmount)}`}
              />
              <StatCard
                label="Total Disbursed Volume"
                value={fmtLakh(totAmount)}
                tone="blue"
                hint={`${totRecords} total loans funded MTD`}
              />
              <StatCard
                label="HL Benchmark Band"
                value={band ? `${band.min}% – ${band.max}%` : 'Standard'}
                hint={
                  hlIrr != null && band
                    ? hlIrr >= band.min && hlIrr <= band.max
                      ? '✓ Within target range'
                      : 'Outside expected band'
                    : 'Configured in IRR settings'
                }
              />
            </div>

            {/* Navigation Tabs */}
            <div className="flex border-b border-slate-200 gap-1">
              <button
                type="button"
                onClick={() => setActiveTab('overview')}
                className={cx(
                  'flex items-center gap-2 border-b-2 px-4 py-2.5 text-sm font-semibold transition',
                  activeTab === 'overview'
                    ? 'border-brand-600 text-brand-700 bg-white rounded-t-lg'
                    : 'border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-700'
                )}
              >
                <TrendingUp size={16} />
                Product Mix & Rate Comparison
              </button>

              <button
                type="button"
                onClick={() => setActiveTab('regions')}
                className={cx(
                  'flex items-center gap-2 border-b-2 px-4 py-2.5 text-sm font-semibold transition',
                  activeTab === 'regions'
                    ? 'border-brand-600 text-brand-700 bg-white rounded-t-lg'
                    : 'border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-700'
                )}
              >
                <Award size={16} />
                Regional IRR Ranking ({mData.rows.length} Regions)
              </button>

              <button
                type="button"
                onClick={() => setActiveTab('workbook')}
                className={cx(
                  'flex items-center gap-2 border-b-2 px-4 py-2.5 text-sm font-semibold transition',
                  activeTab === 'workbook'
                    ? 'border-brand-600 text-brand-700 bg-white rounded-t-lg'
                    : 'border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-700'
                )}
              >
                <Layers size={16} />
                Master 5-Sheet Excel Specifications
              </button>
            </div>

            {/* Tab 1: Product Mix & Rate Comparison Visual Charts */}
            {activeTab === 'overview' && (
              <div className="grid gap-6 lg:grid-cols-2">
                {/* Visual Rate Comparison */}
                <Card title="Weighted Average IRR Comparison (MTD)">
                  <div className="p-4 space-y-6">
                    {/* SVG Rate Comparison Bar Visual */}
                    <div className="rounded-xl border border-slate-100 bg-slate-50/50 p-4">
                      <div className="space-y-4">
                        {/* HL Rate Bar */}
                        <div>
                          <div className="flex justify-between text-xs font-semibold text-slate-700 mb-1">
                            <span className="flex items-center gap-1.5">
                              <span className="h-2.5 w-2.5 rounded-full bg-emerald-600" />
                              Home Loan (HL) Weighted IRR
                            </span>
                            <span className="text-emerald-700 font-bold">{fmtIrr(hlIrr)}%</span>
                          </div>
                          <div className="h-4 w-full rounded-full bg-slate-200 overflow-hidden">
                            <div
                              className="h-full rounded-full bg-emerald-500 transition-all duration-500"
                              style={{ width: `${Math.min(100, ((hlIrr ?? 0) / 20) * 100)}%` }}
                            />
                          </div>
                          <span className="text-[11px] text-slate-400 mt-0.5 block">
                            Disbursed Amount: {fmtLakh(hlAmount)} ({hlRecords} loans)
                          </span>
                        </div>

                        {/* NHL Rate Bar */}
                        <div>
                          <div className="flex justify-between text-xs font-semibold text-slate-700 mb-1">
                            <span className="flex items-center gap-1.5">
                              <span className="h-2.5 w-2.5 rounded-full bg-purple-600" />
                              Non-Home Loan / LAP (NHL) Weighted IRR
                            </span>
                            <span className="text-purple-700 font-bold">{fmtIrr(nhlIrr)}%</span>
                          </div>
                          <div className="h-4 w-full rounded-full bg-slate-200 overflow-hidden">
                            <div
                              className="h-full rounded-full bg-purple-500 transition-all duration-500"
                              style={{ width: `${Math.min(100, ((nhlIrr ?? 0) / 20) * 100)}%` }}
                            />
                          </div>
                          <span className="text-[11px] text-slate-400 mt-0.5 block">
                            Disbursed Amount: {fmtLakh(nhlAmount)} ({nhlRecords} loans)
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Band Benchmark Status */}
                    {band && (
                      <div className="rounded-xl border border-gold-200 bg-gold-50/70 p-3.5 text-xs text-gold-900 flex items-start gap-2.5">
                        <TriangleAlert size={16} className="text-gold-700 shrink-0 mt-0.5" />
                        <div>
                          <span className="font-semibold">IRR Compliance Band:</span> Expected range for Home Loans is{' '}
                          <strong>
                            {band.min}% to {band.max}%
                          </strong>
                          . Both product classes are calculated independently using loan-level weightage without blending.
                        </div>
                      </div>
                    )}
                  </div>
                </Card>

                {/* Portfolio Mix Distribution */}
                <Card title="Disbursement Portfolio Share (HL vs NHL)">
                  <div className="p-4 flex flex-col items-center justify-center space-y-5">
                    {/* Graphical Donut / Stacked Visual */}
                    <div className="w-full space-y-3">
                      <div className="flex justify-between text-xs font-semibold text-slate-700">
                        <span>HL ({hlPctShare}%)</span>
                        <span>NHL ({nhlPctShare}%)</span>
                      </div>
                      <div className="h-6 w-full rounded-xl overflow-hidden flex shadow-inner">
                        <div
                          className="h-full bg-emerald-500 transition-all duration-500 flex items-center justify-center text-[10px] font-bold text-white"
                          style={{ width: `${hlPctShare}%` }}
                        >
                          {hlPctShare > 15 ? `HL ${hlPctShare}%` : ''}
                        </div>
                        <div
                          className="h-full bg-purple-600 transition-all duration-500 flex items-center justify-center text-[10px] font-bold text-white"
                          style={{ width: `${nhlPctShare}%` }}
                        >
                          {nhlPctShare > 15 ? `NHL ${nhlPctShare}%` : ''}
                        </div>
                      </div>
                    </div>

                    <div className="w-full grid grid-cols-2 gap-3 pt-2">
                      <div className="rounded-xl border border-emerald-100 bg-emerald-50/50 p-3 text-center">
                        <span className="text-xs font-semibold text-emerald-800 block">Home Loans</span>
                        <span className="text-lg font-bold text-emerald-900">{fmtLakh(hlAmount)}</span>
                        <span className="text-[11px] text-emerald-700 block">{hlRecords} disbursements</span>
                      </div>

                      <div className="rounded-xl border border-purple-100 bg-purple-50/50 p-3 text-center">
                        <span className="text-xs font-semibold text-purple-800 block">Non-Home Loans</span>
                        <span className="text-lg font-bold text-purple-900">{fmtLakh(nhlAmount)}</span>
                        <span className="text-[11px] text-purple-700 block">{nhlRecords} disbursements</span>
                      </div>
                    </div>
                  </div>
                </Card>
              </div>
            )}

            {/* Tab 2: Regional Performance Ranking */}
            {activeTab === 'regions' && (
              <Card flush>
                <div className="border-b border-slate-100 p-4 bg-slate-50/50 flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h3 className="font-semibold text-slate-900">Regional Weighted IRR & Disbursement Matrix</h3>
                    <p className="text-xs text-slate-500">
                      Comparison of MTD disbursement count, volume, and Weighted Average IRR across regions
                    </p>
                  </div>
                </div>

                {!mData.rows.length ? (
                  <EmptyState title="No regional disbursement figures recorded for this period." />
                ) : (
                  <Table
                    head={[
                      'Region',
                      'HL Loans',
                      'HL Amount',
                      'HL Weighted IRR',
                      'NHL Loans',
                      'NHL Amount',
                      'NHL Weighted IRR',
                      'Total Amount',
                    ]}
                  >
                    {mData.rows.map((r) => {
                      const rHl = r.classes.HL
                      const rNhl = r.classes.NHL
                      const rTotAmt = (rHl?.amount ?? 0) + (rNhl?.amount ?? 0)

                      return (
                        <tr key={r.label}>
                          <Td className="font-semibold text-slate-900">{r.label}</Td>
                          <Td className="tabular text-right">{rHl?.records ?? 0}</Td>
                          <Td className="tabular text-right">{fmtLakh(rHl?.amount ?? 0)}</Td>
                          <Td className="tabular text-right font-bold text-emerald-700">
                            {fmtIrr(rHl?.irr)}%
                          </Td>
                          <Td className="tabular text-right">{rNhl?.records ?? 0}</Td>
                          <Td className="tabular text-right">{fmtLakh(rNhl?.amount ?? 0)}</Td>
                          <Td className="tabular text-right font-bold text-purple-700">
                            {fmtIrr(rNhl?.irr)}%
                          </Td>
                          <Td className="tabular text-right font-bold text-slate-900">
                            {fmtLakh(rTotAmt)}
                          </Td>
                        </tr>
                      )
                    })}
                  </Table>
                )}
              </Card>
            )}

            {/* Tab 3: Master Excel 5-Sheet Workbook Specifications */}
            {activeTab === 'workbook' && (
              <div className="rounded-xl border border-slate-200 bg-white overflow-hidden shadow-xs">
                <div className="bg-slate-100 px-5 py-3 text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center justify-between">
                  <span>Included in your Master Excel Workbook (.xlsx)</span>
                  <span className="text-emerald-700 lowercase font-medium">5 formatted worksheets</span>
                </div>
                <div className="divide-y divide-slate-100 text-sm">
                  <div className="flex items-center justify-between px-5 py-3.5">
                    <div>
                      <span className="font-semibold text-brand-900 flex items-center gap-1.5">
                        <BarChart3 size={15} className="text-brand-600" />
                        Sheet 1: Analytics Dashboard
                      </span>
                      <p className="text-xs text-slate-500 mt-0.5">
                        Executive KPI cards, HL vs NHL volume share %, Regional ranking, and Ticket Size / ROI distribution bands.
                      </p>
                    </div>
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-brand-50 text-brand-700">
                      Analytics Tab
                    </span>
                  </div>

                  <div className="flex items-center justify-between px-5 py-3.5">
                    <div>
                      <span className="font-semibold text-slate-900 flex items-center gap-1.5">
                        <Layers size={15} className="text-slate-600" />
                        Sheet 2: All Disbursements
                      </span>
                      <p className="text-xs text-slate-500 mt-0.5">
                        Full financial year loan-level register with Loan Account, Customer, Location, Amount, Tenure, Rate & Weight calculations.
                      </p>
                    </div>
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-700">
                      Audit Register
                    </span>
                  </div>

                  <div className="flex items-center justify-between px-5 py-3.5">
                    <div>
                      <span className="font-semibold text-slate-900 flex items-center gap-1.5">
                        <FileSpreadsheet size={15} className="text-slate-600" />
                        Sheet 3: Period Disbursements
                      </span>
                      <p className="text-xs text-slate-500 mt-0.5">
                        Active period (MTD / TD) loan register filtered to current month with summary totals.
                      </p>
                    </div>
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-700">
                      Active Register
                    </span>
                  </div>

                  <div className="flex items-center justify-between px-5 py-3.5">
                    <div>
                      <span className="font-semibold text-emerald-900 flex items-center gap-1.5">
                        <CheckCircle2 size={15} className="text-emerald-600" />
                        Sheet 4: TD MTD YTD Summary
                      </span>
                      <p className="text-xs text-slate-500 mt-0.5">
                        2-tier merged headers (TD, MTD, YTD over No., volume in Lakhs, Weighted IRR) with Region to Branch hierarchy.
                      </p>
                    </div>
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700">
                      Executive Summary
                    </span>
                  </div>

                  <div className="flex items-center justify-between px-5 py-3.5">
                    <div>
                      <span className="font-semibold text-purple-900 flex items-center gap-1.5">
                        <PieChart size={15} className="text-purple-600" />
                        Sheet 5: Product MTD Summary
                      </span>
                      <p className="text-xs text-slate-500 mt-0.5">
                        2-tier merged headers (HL MTD, NHL MTD, TOTAL MTD over No., volume in Lakhs, Weighted IRR) with Regional hierarchy.
                      </p>
                    </div>
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-50 text-purple-700">
                      Product Split
                    </span>
                  </div>
                </div>
              </div>
            )}
          </>
        )}

        {/* Footer actions */}
        <div className="flex items-center justify-between border-t border-slate-200 pt-4">
          <Button variant="secondary" onClick={onClose}>
            Close
          </Button>
          <Button disabled={downloading} onClick={downloadMaster}>
            <Download size={16} />
            {downloading ? 'Downloading…' : 'Export Master Excel Workbook (.xlsx)'}
          </Button>
        </div>
      </div>
    </Dialog>
  )
}
