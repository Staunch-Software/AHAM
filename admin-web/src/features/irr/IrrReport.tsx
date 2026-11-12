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
  PERIODS, PeriodReport, PeriodRow, ProductClass,
} from './shared'

type Tab = 'periods' | 'month'
interface DetailTarget { title: string; params: Record<string, string | undefined>; period: Period }
interface DetailItem { id: string; loan_account: string; disbursement_ref: string | null; disbursement_date: string; branch: string; branch_code: string; region: string; product: string; product_class: string; amount: number; tenure_months: number; roi: number; weighted_roi: number }
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
  const [period, setPeriod] = useState<Period>(target.period)
  // one product class at a time: HL and NHL are never added together
  const [cls, setCls] = useState<ProductClass>((target.params.product as ProductClass | undefined) ?? 'HL')
  const [page, setPage] = useState(1)
  const params = { ...target.params, product: cls, as_of: asOf, period }
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
          <Segmented label="Period" value={period} onChange={(p) => { setPeriod(p); setPage(1) }} options={PERIODS.map((p) => ({ value: p, label: PERIOD_LABELS[p] }))} />
          <Segmented label="Product" value={cls} onChange={(c) => { setCls(c); setPage(1) }} options={CLASSES.map((c) => ({ value: c, label: c }))} />
        </div>
        <ExportButtons url="/irr/detail" params={params} name={`irr_loans_${period}_${cls}_${asOf}`} />
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
              <Table head={['Loan account', 'Date', 'Branch', 'Product', 'Amount (₹)', 'Tenure (months)', 'ROI (%)', 'Transaction IRR (amount × tenure × ROI)']}>
                {data.items.map((i) => (
                  <tr key={i.id}>
                    <Td className="whitespace-nowrap font-medium text-slate-900">{i.loan_account}{i.disbursement_ref && <span className="ml-1 text-xs text-slate-500">#{i.disbursement_ref}</span>}</Td>
                    <Td className="tabular whitespace-nowrap">{fmtDay(i.disbursement_date)}</Td>
                    <Td className="whitespace-nowrap">{i.branch}<div className="text-xs text-slate-500">{i.region}</div></Td>
                    <Td className="whitespace-nowrap">{i.product} <span className="text-xs text-slate-500">({i.product_class})</span></Td>
                    <Td className="tabular text-right">{fmtNum(i.amount)}</Td>
                    <Td className="tabular text-right">{fmtNum(i.tenure_months)}</Td>
                    <Td className="tabular text-right">{fmtNum(i.roi, 4)}</Td>
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
  const filters = { as_of: asOf || undefined, level, region_id: region || undefined, branch_id: branch || undefined }
  const periods = useQuery({
    queryKey: ['irr', 'report', filters, product], enabled: tab === 'periods', placeholderData: keepPreviousData,
    queryFn: async () => (await api.get<PeriodReport>('/irr/report', { params: { ...filters, product } })).data,
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
  const open = (title: string, params: Record<string, string | undefined>, period: Period, cls?: ProductClass) =>
    () => setDetail({ title, params: { ...params, as_of: undefined, level: undefined, product: cls }, period })
  const exceptions = pd ? pd.open_exceptions.YTD : md?.open_exceptions ?? 0

  return (
    <>
      <PageTitle subtitle="Weighted average IRR of Home Loans (HL) and Non-Home Loans / LAP (NHL), from the Disbursement Register."
        actions={<>
          <label className="flex items-center gap-2 text-xs text-slate-500">As of<Input type="date" aria-label="As of date" value={day} onChange={(e) => setAsOf(e.target.value)} className="w-auto" /></label>
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

      <Note>
        Weighted average IRR = sum of Transaction IRR (disbursed amount × that loan's tenure in months × ROI) ÷ (sum of disbursed amount × average tenure),
        where the average tenure is the plain average of the tenures of the period's disbursements. &ldquo;No.&rdquo; counts disbursements, so a loan paid in
        two tranches counts twice. HL and NHL are always worked out separately. Month and year to date use all the disbursements since the 1st of the
        month and the start of the financial year; they are never an average of daily, branch or region figures. Cancelled and reversed disbursements
        are left out. Click a row to see its loans.
      </Note>

      <div className="mb-4 flex flex-wrap items-center gap-3">
        <Segmented label="Report layout" value={tab} onChange={setTab} options={[{ value: 'periods', label: 'TD / MTD / YTD' }, { value: 'month', label: 'HL & NHL month to date' }]} />
        {tab === 'periods' && <Segmented label="Product" value={product} onChange={setProduct} options={CLASSES.map((c) => ({ value: c, label: CLASS_LABELS[c] }))} />}
        <Segmented label="Level" value={level} onChange={setLevel} options={LEVELS} />
      </div>

      <ErrorBox error={current.error ? errorMessage(current.error) : null} />
      {exceptions > 0 && (
        <Note tone="gold">
          {exceptions} disbursement{exceptions > 1 ? 's' : ''} of this {tab === 'periods' ? 'year to date' : 'month to date'} {exceptions > 1 ? 'are' : 'is'} left out because the tenure or ROI is missing, zero or negative.
          {can('irr.manage') && <> <Link to={path('irr-exceptions')} className="font-semibold text-brand-700 underline">Correct them under IRR exceptions</Link>.</>}
        </Note>
      )}
      {!!data?.warnings.length && (
        <div className="mb-4 rounded-xl border border-amber-300/70 bg-amber-50 px-4 py-3 text-sm text-amber-900" role="status">
          <p className="flex items-center gap-2 font-semibold"><TriangleAlert size={16} aria-hidden="true" />Outside the expected range (a warning only: the figures are still correct)</p>
          <ul className="mt-1 list-disc pl-6">{data.warnings.map((w) => <li key={w}>{w}</li>)}</ul>
        </div>
      )}

      <Card flush title={tab === 'periods' ? `${CLASS_LABELS[product]}: for the day, month to date and year to date` : 'HL and NHL, month to date'}
        subtitle={pd ? `As of ${fmtDay(day)}. Month to date from ${fmtDay(pd.periods.MTD.from)}, year to date from ${fmtDay(pd.periods.YTD.from)}.`
          : md ? `${fmtDay(md.period.from)} to ${fmtDay(md.period.to)}.` : undefined}
        actions={data && <ExportButtons url={tab === 'periods' ? '/irr/report' : '/irr/report/month-by-product'} params={{ ...filters, as_of: day, ...(tab === 'periods' ? { product } : {}) }}
          name={tab === 'periods' ? `irr_${product}_${level}_${day}` : `irr_HL_NHL_MTD_${level}_${day}`} />}>
        {current.isLoading || !data ? <div className="space-y-2 p-5">{Array.from({ length: 5 }, (_, i) => <Skeleton key={i} className="h-10" />)}</div>
          : !data.rows.length ? <EmptyState icon={<Percent size={20} />} title="No branches in your scope." />
            : tab === 'periods' && pd ? (
              <GroupedTable lead={lead(level)} groups={PERIODS.map((p) => ({ label: PERIOD_LABELS[p], cols: [ACC, IRR] }))}>
                {[...pd.rows, ...(level !== 'company' ? [pd.total] : [])].map((r, i) => {
                  const total = level !== 'company' && i === pd.rows.length
                  const o = open(r.label, total ? { ...filters, as_of: day } : scope(r), 'MTD', product)
                  return (
                    <tr key={total ? 'total' : r.branch_id ?? r.region_id ?? r.label} className={cx('cursor-pointer', total && 'bg-slate-50/80')} onClick={o}>
                      <RowLabel r={r} level={level} total={total} onOpen={o} />
                      {PERIODS.map((p) => <Cells key={p} cell={r.periods[p]} decimals={pd.decimals} flagged={r.flags.includes(p)} />)}
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
