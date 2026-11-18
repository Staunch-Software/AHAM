import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { Percent, TriangleAlert } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Card, cx, Dialog, EmptyState, ErrorBox, Input, Note, PageTitle, Pager, Segmented, Select, Skeleton, Table, Td } from '../../components/ui'
import { api, errorMessage } from '../../services/api'
import { useAuth } from '../../services/auth'
import { useBranches, useRegions } from '../../services/meta'
import {
  CLASS_LABELS, CLASSES, ClassRow, ExportButtons, fmtDay, fmtIrr, fmtNum, GroupedTable, Level, LEVELS, MonthReport, Period, PERIOD_LABELS,
  PERIODS, PeriodReport, PeriodRow, ProductClass, ReportPeriod,
} from './shared'

type Tab = 'periods' | 'month'
/** BRD 3.1 "Reporting period": all three periods, one of them, or a date range */
type Show = 'ALL' | Period | 'RANGE'
const SHOW_OPTIONS: { value: Show; label: string }[] = [
  { value: 'ALL', label: 'TD, MTD and YTD' }, { value: 'TD', label: 'TD' }, { value: 'MTD', label: 'MTD' }, { value: 'YTD', label: 'YTD' },
  { value: 'RANGE', label: 'Date range' },
]
const SPAN: Record<ReportPeriod, string> = { TD: 'day', MTD: 'month to date', YTD: 'year to date', RANGE: 'date range' }
interface DetailTarget { title: string; params: Record<string, string | undefined>; period: ReportPeriod }
interface DetailItem { id: string; loan_account: string; disbursement_ref: string | null; disbursement_date: string; branch: string; branch_code: string; region: string; product: string; product_class: string; amount: number; tenure_months: number; roi: number; weight: number; weighted_roi: number }
interface Detail { as_of: string; from: string; to: string; decimals: number; total: number; items: DetailItem[]; totals: { records: number; amount: number; tenure: number; average_tenure: number | null; denominator: number; weighted_roi: number; irr: number | null } }

const ACC = 'Number of disbursements'
const IRR = 'Weighted average IRR (%)'

const lead = (level: Level) => (level === 'branch' ? ['Branch', 'Region'] : level === 'region' ? ['Region'] : ['Scope'])
const rowTarget = (r: { branch_id?: string; region_id?: string | null }, level: Level) =>
  level === 'branch' ? { branch_id: r.branch_id } : level === 'region' && r.region_id ? { region_id: r.region_id } : {}

/** The row's name, as a button that opens the loans behind the row (the whole row is clickable with a mouse too). */
function RowLabel({ r, level, total, onOpen }: { r: PeriodRow | ClassRow; level: Level; total?: boolean; onOpen: () => void }) {
  return (
    <>
      <Td className={cx('whitespace-nowrap', total ? 'font-semibold text-brand-900' : 'font-medium text-slate-900')}>
        <button type="button" className="text-left hover:text-brand-700 hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
          aria-label={`Loans of ${r.label}`} onClick={(e) => { e.stopPropagation(); onOpen() }}>{r.label}</button>
        {level === 'branch' && r.code && <span className="ml-1.5 text-xs font-normal text-slate-500">{r.code}</span>}
      </Td>
      {level === 'branch' && <Td className="whitespace-nowrap text-slate-500">{total ? '' : r.region}</Td>}
    </>
  )
}

function Cells({ cell, decimals, flagged }: { cell: { records: number; irr: number | null }; decimals: number; flagged: boolean }) {
  return (
    <>
      <Td className="tabular border-l border-slate-100 text-right">{cell.records}</Td>
      <Td className={cx('tabular text-right font-semibold', flagged ? 'text-amber-700' : 'text-slate-900')}>
        {flagged && <TriangleAlert size={13} className="mr-1 inline align-[-2px]" aria-label="Outside the expected range" />}
        {fmtIrr(cell.irr, decimals)}
      </Td>
    </>
  )
}

function DetailDialog({ target, asOf, onClose }: { target: DetailTarget; asOf: string; onClose: () => void }) {
  const [period, setPeriod] = useState<ReportPeriod>(target.period)
  // one product class at a time: HL and NHL are never added together
  const [cls, setCls] = useState<ProductClass>((target.params.product as ProductClass | undefined) ?? 'HL')
  const [page, setPage] = useState(1)
  const range = period === 'RANGE'  // the loans of a chosen date range (target.params has date_from and date_to)
  const params = range ? { ...target.params, product: cls } : { ...target.params, product: cls, as_of: asOf, period }
  const { data, error, isLoading } = useQuery({
    queryKey: ['irr', 'detail', params, page],
    queryFn: async () => (await api.get<Detail>('/irr/detail', { params: { ...params, page, page_size: 25 } })).data,
    placeholderData: keepPreviousData,
  })
  const t = data?.totals
  return (
    <Dialog title={`Loans behind the figure: ${target.title}`} onClose={onClose} wide>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap gap-3">
          {!range && <Segmented label="Period" value={period} onChange={(p) => { setPeriod(p); setPage(1) }} options={PERIODS.map((p) => ({ value: p as ReportPeriod, label: PERIOD_LABELS[p] }))} />}
          <Segmented label="Product" value={cls} onChange={(c) => { setCls(c); setPage(1) }} options={CLASSES.map((c) => ({ value: c, label: c }))} />
        </div>
        <ExportButtons url="/irr/detail" params={params} name={range ? `irr_loans_${cls}_${target.params.date_from}_to_${target.params.date_to}` : `irr_loans_${period}_${cls}_${asOf}`} />
      </div>
      <ErrorBox error={error ? errorMessage(error) : null} />
      {data && t && (
        <p className="mb-3 text-sm text-slate-600" data-testid="detail-totals">
          {fmtDay(data.from)} to {fmtDay(data.to)}, {CLASS_LABELS[cls]}: {t.records} disbursement{t.records === 1 ? '' : 's'}, amount ₹{fmtNum(t.amount)},
          {' '}average tenure {fmtNum(t.average_tenure)} months ({fmtNum(t.tenure)} ÷ {t.records}).
          {' '}Weighted average IRR <strong className="text-brand-900">{fmtIrr(t.irr, data.decimals)}%</strong>
          {t.irr != null && <> = {fmtNum(t.weighted_roi)} ÷ {fmtNum(t.denominator)} (sum of Transaction IRR ÷ amount × average tenure)</>}
        </p>
      )}
      <div className="-mx-6 border-y border-slate-200">
        {isLoading ? <div className="space-y-2 p-4">{Array.from({ length: 4 }, (_, i) => <Skeleton key={i} className="h-8" />)}</div>
          : !data?.items.length ? <EmptyState title="No disbursements count in this period." />
            : (
<Table head={['Loan account', 'Date', 'Branch', 'Product', 'Amount (₹)', 'Tenure (months)', 'ROI (%)', 'Weight (amount × tenure)', 'Transaction IRR (amount × tenure × ROI)']} maxHeight="max-h-[min(450px,50vh)]">
                {data.items.map((i) => (
                  <tr key={i.id}>
                    <Td className="whitespace-nowrap font-medium text-slate-900">{i.loan_account || <span className="font-normal text-slate-400">no loan account</span>}{i.disbursement_ref && <span className="ml-1 text-xs text-slate-500">#{i.disbursement_ref}</span>}</Td>
                    <Td className="tabular whitespace-nowrap">{fmtDay(i.disbursement_date)}</Td>
                    <Td className="whitespace-nowrap">{i.branch}<div className="text-xs text-slate-500">{i.region}</div></Td>
                    <Td className="whitespace-nowrap">{i.product} <span className="text-xs text-slate-500">({i.product_class})</span></Td>
                    <Td className="tabular text-right">{fmtNum(i.amount)}</Td>
                    <Td className="tabular text-right">{fmtNum(i.tenure_months)}</Td>
                    <Td className="tabular text-right">{fmtNum(i.roi, 4)}</Td>
                    <Td className="tabular text-right">{fmtNum(i.weight)}</Td>
                    <Td className="tabular text-right">{fmtNum(i.weighted_roi, 4)}</Td>
                  </tr>
                ))}
              </Table>
            )}
        {data && data.total > 25 && <Pager page={page} pageSize={25} total={data.total} onChange={setPage} />}
      </div>
    </Dialog>
  )
}

/** BRD "Weighted average IRR – HL & NHL (LAP)": for the day (TD), month to date and year to date from the Disbursement Register. */
export default function IrrReport() {
  const { can, path } = useAuth()
  const { data: branches } = useBranches()
  const { data: regions } = useRegions()
  const [tab, setTab] = useState<Tab>('periods')
  const [asOf, setAsOf] = useState('')
  const [product, setProduct] = useState<ProductClass>('HL')
  const [level, setLevel] = useState<Level>('branch')
  const [region, setRegion] = useState('')
  const [branch, setBranch] = useState('')
  const [detail, setDetail] = useState<DetailTarget | null>(null)
  const [show, setShow] = useState<Show>('ALL')
  const [range, setRange] = useState({ from: '', to: '' })
  const filters = { as_of: asOf || undefined, level, region_id: region || undefined, branch_id: branch || undefined }
  const isRange = tab === 'periods' && show === 'RANGE'
  const rangeReady = !!range.from && !!range.to
  // what the TD / MTD / YTD layout asks for: some periods, or a date range in place of the as-of date
  const choice: Record<string, string | undefined> = isRange ? { date_from: range.from, date_to: range.to, as_of: undefined }
    : show === 'ALL' ? {} : { periods: show }
  const periods = useQuery({
    queryKey: ['irr', 'report', filters, product, choice], enabled: tab === 'periods' && (!isRange || rangeReady), placeholderData: keepPreviousData,
    queryFn: async () => (await api.get<PeriodReport>('/irr/report', { params: { ...filters, product, ...choice } })).data,
  })
  const month = useQuery({
    queryKey: ['irr', 'month', filters], enabled: tab === 'month', placeholderData: keepPreviousData,
    queryFn: async () => (await api.get<MonthReport>('/irr/report/month-by-product', { params: filters })).data,
  })
  const current = tab === 'periods' ? periods : month
  const data = current.data
  const pd = tab === 'periods' ? periods.data : undefined
  const md = tab === 'month' ? month.data : undefined
  const day = asOf || data?.as_of || ''
  const shownBranches = branches?.filter((b) => !region || b.region_id === region)
  const scope = (r: { branch_id?: string; region_id?: string | null }) => ({ ...filters, as_of: day, ...rowTarget(r, level) })
  const open = (title: string, params: Record<string, string | undefined>, period: ReportPeriod, cls?: ProductClass) =>
    () => setDetail({ title, params: { ...params, as_of: undefined, level: undefined, product: cls }, period })
  const keys = pd ? (Object.keys(pd.periods) as ReportPeriod[]) : []
  const widest: ReportPeriod = keys.at(-1) ?? 'YTD'
  const exceptions = pd ? pd.open_exceptions[widest] ?? 0 : md?.open_exceptions ?? 0
  const label = (p: ReportPeriod) => (p === 'RANGE' ? `${fmtDay(pd?.periods.RANGE?.from)} to ${fmtDay(pd?.periods.RANGE?.to)}` : PERIOD_LABELS[p])
  const firstOfMonth = (d: string) => (d ? `${d.slice(0, 8)}01` : '')
  const pick = (v: Show) => {
    setShow(v)
    if (v === 'RANGE' && !rangeReady) setRange({ from: firstOfMonth(day), to: day })
  }
  const periodsTitle = isRange ? `${CLASS_LABELS[product]}: disbursed in a date range`
    : show === 'ALL' ? `${CLASS_LABELS[product]}: for the day, month to date and year to date` : `${CLASS_LABELS[product]}: ${PERIOD_LABELS[show as Period]}`
  const periodsSubtitle = !pd ? undefined : isRange ? `Disbursed from ${fmtDay(pd.periods.RANGE?.from)} to ${fmtDay(pd.periods.RANGE?.to)}.`
    : [`As of ${fmtDay(day)}.`, pd.periods.MTD && `Month to date from ${fmtDay(pd.periods.MTD.from)}.`, pd.periods.YTD && `Year to date from ${fmtDay(pd.periods.YTD.from)}.`].filter(Boolean).join(' ')
  const exportName = isRange ? `irr_${product}_${level}_${range.from}_to_${range.to}` : `irr_${product}_${level}_${day}`

  return (
    <>
      <PageTitle subtitle="Weighted average IRR of Home Loans (HL) and Non-Home Loans / LAP (NHL), from the Disbursement Register."
        actions={<>
          {!isRange && <label className="flex items-center gap-2 text-xs text-slate-500">As of<Input type="date" aria-label="As of date" value={day} onChange={(e) => setAsOf(e.target.value)} className="w-auto" /></label>}
          {(regions?.length ?? 0) > 1 && (
            <Select aria-label="Region" value={region} onChange={(e) => { setRegion(e.target.value); setBranch('') }} className="w-auto">
              <option value="">All regions</option>{regions?.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
            </Select>
          )}
          <Select aria-label="Branch" value={branch} onChange={(e) => setBranch(e.target.value)} className="w-auto">
            <option value="">All my branches</option>{shownBranches?.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
          </Select>
        </>}>
        IRR report
      </PageTitle>

      <section aria-label="How the IRR is worked out" className="mb-4 rounded-xl bg-brand-50 px-4 py-3 text-sm text-brand-800">
        <p className="font-semibold text-brand-900">Weighted average IRR = Σ Transaction IRR ÷ (Σ disbursed amount × average tenure)</p>
        <ul className="mt-2 grid list-disc gap-x-8 gap-y-1 pl-5 md:grid-cols-2">
          <li><strong>Transaction IRR</strong> = disbursed amount × that loan's tenure (months) × ROI</li>
          <li><strong>Average tenure</strong> = plain average of the tenures in the period</li>
          <li><strong>No.</strong> = number of disbursements (a loan paid in two tranches counts twice)</li>
          <li><strong>HL and NHL</strong> are always worked out separately</li>
          <li><strong>MTD and YTD</strong> use every disbursement of the period, never an average of daily, branch or region figures</li>
          <li><strong>Cancelled or reversed</strong> disbursements are left out</li>
        </ul>
        <p className="mt-2 text-xs text-brand-700">Click a row to see the loans behind it.</p>
      </section>

      <div className="mb-4 flex flex-wrap items-center gap-3">
        <Segmented label="Report layout" value={tab} onChange={setTab} options={[{ value: 'periods', label: 'TD / MTD / YTD' }, { value: 'month', label: 'HL & NHL month to date' }]} />
        {tab === 'periods' && <Segmented label="Product" value={product} onChange={setProduct} options={CLASSES.map((c) => ({ value: c, label: CLASS_LABELS[c] }))} />}
        <Segmented label="Level" value={level} onChange={setLevel} options={LEVELS} />
      </div>
      {tab === 'periods' && (
        <div className="mb-4 flex flex-wrap items-center gap-3">
          <Segmented label="Show" value={show} onChange={pick} options={SHOW_OPTIONS} />
          {isRange && (
            <>
              <label className="flex items-center gap-2 text-xs text-slate-500">Disbursed from<Input type="date" aria-label="Disbursed from" value={range.from} onChange={(e) => setRange({ ...range, from: e.target.value })} className="w-auto" /></label>
              <label className="flex items-center gap-2 text-xs text-slate-500">to<Input type="date" aria-label="Disbursed to" value={range.to} onChange={(e) => setRange({ ...range, to: e.target.value })} className="w-auto" /></label>
            </>
          )}
        </div>
      )}

      <ErrorBox error={current.error ? errorMessage(current.error) : null} />
      {exceptions > 0 && (
        <Note tone="gold">
          {exceptions} disbursement{exceptions > 1 ? 's' : ''} of this {tab === 'periods' ? SPAN[widest] : 'month to date'} {exceptions > 1 ? 'are' : 'is'} left out because the tenure or ROI is missing, zero or negative.
          {can('irr.manage') && <> <Link to={path('irr-exceptions')} className="font-semibold text-brand-700 underline">Correct them under IRR exceptions</Link>.</>}
        </Note>
      )}
      {!!data?.warnings.length && (
        <div className="mb-4 rounded-xl border border-amber-300/70 bg-amber-50 px-4 py-3 text-sm text-amber-900" role="status">
          <p className="flex items-center gap-2 font-semibold"><TriangleAlert size={16} aria-hidden="true" />Outside the expected range (a warning only: the figures are still correct)</p>
          <ul className="mt-1 list-disc pl-6">{data.warnings.map((w) => <li key={w}>{w}</li>)}</ul>
        </div>
      )}

      <Card flush title={tab === 'periods' ? periodsTitle : 'HL and NHL, month to date'}
        subtitle={pd ? periodsSubtitle : md ? `${fmtDay(md.period.from)} to ${fmtDay(md.period.to)}.` : undefined}
        actions={data && <ExportButtons url={tab === 'periods' ? '/irr/report' : '/irr/report/month-by-product'} params={{ ...filters, as_of: day, ...(tab === 'periods' ? { product, ...choice } : {}) }}
          name={tab === 'periods' ? exportName : `irr_HL_NHL_MTD_${level}_${day}`} />}>
        {isRange && !rangeReady ? <EmptyState title="Choose both dates of the range." />
          : current.isLoading || !data ? <div className="space-y-2 p-5">{Array.from({ length: 5 }, (_, i) => <Skeleton key={i} className="h-10" />)}</div>
          : !data.rows.length ? <EmptyState icon={<Percent size={20} />} title="No branches in your scope." />
            : tab === 'periods' && pd ? (
              <GroupedTable lead={lead(level)} groups={keys.map((p) => ({ label: label(p), cols: [ACC, IRR] }))}>
                {[...pd.rows, ...(level !== 'company' ? [pd.total] : [])].map((r, i) => {
                  const total = level !== 'company' && i === pd.rows.length
                  const target = total ? { ...filters, as_of: day } : scope(r)
                  const o = isRange ? open(r.label, { ...target, date_from: range.from, date_to: range.to }, 'RANGE', product)
                    : open(r.label, target, keys.includes('MTD') ? 'MTD' : keys[0], product)
                  return (
                    <tr key={total ? 'total' : r.branch_id ?? r.region_id ?? r.label} className={cx('cursor-pointer', total && 'bg-slate-50/80')} onClick={o}>
                      <RowLabel r={r} level={level} total={total} onOpen={o} />
                      {keys.map((p) => <Cells key={p} cell={r.periods[p] ?? { records: 0, irr: null }} decimals={pd.decimals} flagged={r.flags.includes(p)} />)}
                    </tr>
                  )
                })}
              </GroupedTable>
            ) : md && (
              <GroupedTable lead={lead(level)} groups={CLASSES.map((c) => ({ label: CLASS_LABELS[c], cols: [ACC, IRR] }))}>
                {[...md.rows, ...(level !== 'company' ? [md.total] : [])].map((r, i) => {
                  const total = level !== 'company' && i === md.rows.length
                  const o = open(r.label, total ? { ...filters, as_of: day } : scope(r), 'MTD')
                  return (
                    <tr key={total ? 'total' : r.branch_id ?? r.region_id ?? r.label} className={cx('cursor-pointer', total && 'bg-slate-50/80')} onClick={o}>
                      <RowLabel r={r} level={level} total={total} onOpen={o} />
                      {CLASSES.map((c) => <Cells key={c} cell={r.classes[c]} decimals={md.decimals} flagged={r.flags.includes(c)} />)}
                    </tr>
                  )
                })}
              </GroupedTable>
            )}
      </Card>
      {pd?.band && <p className="mt-3 text-xs text-slate-500">Expected range for {product}: {pd.band.min}% to {pd.band.max}% (IRR settings).</p>}
      {detail && <DetailDialog target={detail} asOf={day} onClose={() => setDetail(null)} />}
    </>
  )
}
