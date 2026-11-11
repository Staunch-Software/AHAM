import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus, Trash2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Button, Card, ErrorBox, Field, Input, Loading, Note, PageTitle, Select } from '../../components/ui'
import { api, errorMessage } from '../../services/api'
import { useAuth } from '../../services/auth'
import { CLASS_LABELS, CLASSES, ProductClass } from './shared'

interface Band { min: number; max: number }
interface Config { product_map: Record<string, ProductClass>; bands: Partial<Record<ProductClass, Band>>; fy_start_month: number; decimals: number }
interface Form { products: { name: string; cls: ProductClass }[]; bands: Record<ProductClass, { min: string; max: string }>; fy_start_month: number; decimals: number }

const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']

const toForm = (c: Config): Form => ({
  products: Object.entries(c.product_map).map(([name, cls]) => ({ name, cls })),
  bands: Object.fromEntries(CLASSES.map((k) => [k, { min: c.bands[k]?.min?.toString() ?? '', max: c.bands[k]?.max?.toString() ?? '' }])) as Form['bands'],
  fy_start_month: c.fy_start_month, decimals: c.decimals,
})

const toConfig = (f: Form): Config => ({
  product_map: Object.fromEntries(f.products.filter((p) => p.name.trim()).map((p) => [p.name.trim(), p.cls])),
  bands: Object.fromEntries(CLASSES.filter((k) => f.bands[k].min.trim() || f.bands[k].max.trim())
    .map((k) => [k, { min: Number(f.bands[k].min), max: Number(f.bands[k].max) }])),
  fy_start_month: f.fy_start_month, decimals: f.decimals,
})

/** Product mapping, expected ranges, financial-year start and decimals (docs/irr-module.md, assumptions 3, 8 and 9). */
export default function IrrSettings() {
  const { can } = useAuth()
  const qc = useQueryClient()
  const edit = can('irr.manage')
  const { data, error } = useQuery({ queryKey: ['irr', 'settings'], queryFn: async () => (await api.get<Config>('/irr/settings')).data })
  const [form, setForm] = useState<Form | null>(null)
  const [saved, setSaved] = useState<string | null>(null)
  useEffect(() => { if (data) setForm(toForm(data)) }, [data])
  const save = useMutation({
    mutationFn: async () => (await api.put<Config & { reclassified: number }>('/irr/settings', toConfig(form!))).data,
    onSuccess: (r) => {
      setSaved(`Saved.${r.reclassified ? ` ${r.reclassified} uploaded disbursement${r.reclassified > 1 ? 's' : ''} moved to the new product class.` : ''}`)
      qc.invalidateQueries({ queryKey: ['irr'] })
    },
    onMutate: () => setSaved(null),
  })
  if (error) return <ErrorBox error={errorMessage(error)} />
  if (!form) return <Loading />
  const set = (f: Partial<Form>) => setForm({ ...form, ...f })
  const setProduct = (i: number, p: Partial<Form['products'][number]>) => set({ products: form.products.map((x, j) => (j === i ? { ...x, ...p } : x)) })
  return (
    <>
      <PageTitle subtitle="How the Disbursement Register is read and how the IRR report is shown. Changes apply from the next report you open.">IRR settings</PageTitle>
      <ErrorBox error={save.error ? errorMessage(save.error) : null} />
      {saved && <Note>{saved}</Note>}
      <div className="space-y-6">
        <Card title="Product mapping" subtitle="Which products of the register are Home Loans (HL) and which are Non-Home Loans / LAP (NHL). Capitals, spaces and punctuation do not matter. A row whose product is not listed here is refused at upload. Changing a product's class also moves the disbursements already uploaded under that name.">
          <ul className="space-y-2">
            {form.products.map((p, i) => (
              <li key={i} className="flex flex-wrap items-center gap-2">
                <Input className="max-w-xs" aria-label={`Product name ${i + 1}`} value={p.name} disabled={!edit} onChange={(e) => setProduct(i, { name: e.target.value })} />
                <Select className="w-auto" aria-label={`Class of ${p.name || `product ${i + 1}`}`} value={p.cls} disabled={!edit} onChange={(e) => setProduct(i, { cls: e.target.value as ProductClass })}>
                  {CLASSES.map((c) => <option key={c} value={c}>{CLASS_LABELS[c]}</option>)}
                </Select>
                {edit && <Button small variant="ghost" aria-label={`Remove ${p.name || 'this product'}`} onClick={() => set({ products: form.products.filter((_, j) => j !== i) })}><Trash2 size={14} aria-hidden="true" /></Button>}
              </li>
            ))}
          </ul>
          {edit && <Button className="mt-3" small variant="secondary" onClick={() => set({ products: [...form.products, { name: '', cls: 'NHL' }] })}><Plus size={14} aria-hidden="true" />Add product</Button>}
        </Card>

        <Card title="Expected range (reasonableness check)" subtitle="When a branch, region or total falls outside the range, the report shows a warning. It never blocks or changes a figure. Leave both blank for no check.">
          <div className="grid gap-4 sm:grid-cols-2">
            {CLASSES.map((c) => (
              <fieldset key={c} className="rounded-xl border border-slate-200 p-4">
                <legend className="px-1 text-xs font-semibold text-brand-900">{CLASS_LABELS[c]}</legend>
                <div className="grid grid-cols-2 gap-3">
                  <Field label="Lowest IRR (%)"><Input inputMode="decimal" disabled={!edit} value={form.bands[c].min} onChange={(e) => set({ bands: { ...form.bands, [c]: { ...form.bands[c], min: e.target.value } } })} /></Field>
                  <Field label="Highest IRR (%)"><Input inputMode="decimal" disabled={!edit} value={form.bands[c].max} onChange={(e) => set({ bands: { ...form.bands, [c]: { ...form.bands[c], max: e.target.value } } })} /></Field>
                </div>
              </fieldset>
            ))}
          </div>
        </Card>

        <Card title="Periods and display">
          <div className="grid max-w-xl gap-4 sm:grid-cols-2">
            <Field label="Financial year starts on the 1st of" hint="Year to date runs from this day.">
              <Select value={form.fy_start_month} disabled={!edit} onChange={(e) => set({ fy_start_month: Number(e.target.value) })}>
                {MONTHS.map((m, i) => <option key={m} value={i + 1}>{m}</option>)}
              </Select>
            </Field>
            <Field label="Decimals shown" hint="On screen and in exports. The calculation itself is never rounded.">
              <Select value={form.decimals} disabled={!edit} onChange={(e) => set({ decimals: Number(e.target.value) })}>
                {[0, 1, 2, 3, 4].map((d) => <option key={d} value={d}>{d}</option>)}
              </Select>
            </Field>
          </div>
        </Card>
      </div>
      {edit && (
        <div className="mt-6 flex justify-end gap-2">
          <Button variant="secondary" onClick={() => data && setForm(toForm(data))}>Undo changes</Button>
          <Button disabled={save.isPending} onClick={() => save.mutate()}>Save settings</Button>
        </div>
      )}
    </>
  )
}
