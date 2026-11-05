import { Download } from 'lucide-react'
import { useState } from 'react'
import { Button, Card, ErrorBox, Input, KV, PageTitle } from '../../components/ui'
import { download, errorMessage } from '../../services/api'
import { useMeta } from '../../services/meta'

const firstOfMonth = () => { const d = new Date(); return new Date(d.getFullYear(), d.getMonth(), 1, 12).toISOString().slice(0, 10) }
const today = () => new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 10)

/** Section 10: the flags the incentive needs. The money is calculated outside the app. */
export default function Takeoff() {
  const [range, setRange] = useState({ from: firstOfMonth(), to: today() })
  const days = useMeta().data?.limits.repeat_window_days ?? 30
  const [error, setError] = useState<string | null>(null)
  const go = async () => {
    setError(null)
    try { await download('/takeoff/export.csv', { date_from: range.from, date_to: range.to }, `sankalp_takeoff_${range.from}_${range.to}.csv`) } catch (e) { setError(errorMessage(e)) }
  }
  return (
    <>
      <PageTitle subtitle="One row per entry made in the period, with the flags the incentive team needs.">Takeoff export</PageTitle>
      <ErrorBox error={error} />
      <Card title="Download">
        <div className="flex flex-wrap items-end gap-3">
          <label className="text-xs text-slate-500">Entries made from<Input type="date" value={range.from} onChange={(e) => setRange({ ...range, from: e.target.value })} /></label>
          <label className="text-xs text-slate-500">to<Input type="date" value={range.to} onChange={(e) => setRange({ ...range, to: e.target.value })} /></label>
          <Button onClick={go}><Download size={16} aria-hidden="true" />Download CSV</Button>
        </div>
      </Card>
      <Card title="What the flags mean" className="mt-6">
        <KV items={[
          ['Customer validated', `Status starts with “Validated” (all four kinds), or the entry logged in and is not LAP. Never for a repeat entry by the same SO within ${days} days.`],
          ['First validation for this number', 'Validated, and no earlier validated entry exists for the same phone, from any SO. Pay once per customer.'],
          ['Validated on', 'The date of the first call that validated it (or the login date when only the login validates it).'],
          ['Counts as Sankalp success', 'Logged in, entry on or after Takeoff start, and the earliest entry for that TCS ID (ties: the lower Entry ID). A LAP login is a success but does not validate.'],
          ['Credited SO', 'The SO on the entry now: a wrong-SO correction moves the credit; the Entry ID never changes.'],
          ['Payout', 'Not calculated here: Aham / HR still has to confirm the rule.'],
        ]} />
      </Card>
    </>
  )
}
