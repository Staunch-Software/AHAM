import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus, Trash2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Button, Card, ErrorBox, Field, Input, Loading, Note, PageTitle, Select } from '../../components/ui'
import { api, errorMessage } from '../../services/api'
import { useAuth } from '../../services/auth'
import { useBranches } from '../../services/meta'
import { CLASS_LABELS, CLASSES, ProductClass } from './shared'

type TenureUnit = 'months' | 'years'
interface Band { min: number; max: number }
interface Config {
  product_map: Record<string, ProductClass>; bands: Partial<Record<ProductClass, Band>>; fy_start_month: number; decimals: number
  tenure_unit: TenureUnit; branch_aliases: Record<string, string>
}
interface Form {
  products: { name: string; cls: ProductClass }[]; bands: Record<ProductClass, { min: string; max: string }>; fy_start_month: number; decimals: number
  tenure_unit: TenureUnit; aliases: { name: string; branch: string }[]
}

const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']

const toForm = (c: Config): Form => ({
  products: Object.entries(c.product_map).map(([name, cls]) => ({ name, cls })),
  bands: Object.fromEntries(CLASSES.map((k) => [k, { min: c.bands[k]?.min?.toString() ?? '', max: c.bands[k]?.max?.toString() ?? '' }])) as Form['bands'],
  fy_start_month: c.fy_start_month, decimals: c.decimals,
  tenure_unit: c.tenure_unit ?? 'years', aliases: Object.entries(c.branch_aliases ?? {}).map(([name, branch]) => ({ name, branch })),
})

const toConfig = (f: Form): Config => ({
  tenure_unit: f.tenure_unit,
  branch_aliases: Object.fromEntries(f.aliases.filter((a) => a.name.trim() && a.branch).map((a) => [a.name.trim(), a.branch])),
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
  const { data: branches } = useBranches()
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
  const setAlias = (i: number, p: Partial<Form['aliases'][number]>) => set({ aliases: form.aliases.map((x, j) => (j === i ? { ...x, ...p } : x)) })
  // a saved name may point at a branch by its code, or at one this company does not have: keep it choosable as written
  const branchOptions = (current: string) => {
    const names = (branches ?? []).map((b) => b.name)
    const known = (branches ?? []).some((b) => b.name === current || b.code === current)
    return current && !known ? [...names, current] : names
  }
  const branchValue = (current: string) => branches?.find((b) => b.code === current && b.name !== current)?.name ?? current
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

        <Card title="Reading the register" subtitle="Aham's register can be uploaded as it is. Set here what its columns do not say.">
          <div className="max-w-md">
            <Field label="A column headed just “Tenure” is in" hint="A heading that says “in months” or “in years” always wins. Tenures are kept in months; the IRR is the same either way.">
              <Select value={form.tenure_unit} disabled={!edit} onChange={(e) => set({ tenure_unit: e.target.value as TenureUnit })}>
                <option value="years">Years (Aham's register)</option>
                <option value="months">Months</option>
              </Select>
            </Field>
          </div>
          <p className="mt-5 text-sm font-medium text-slate-700">Branch names in the register</p>
          <p className="mb-3 text-xs text-slate-500">For branches the register spells differently from HR & Admin › Organization. A row whose branch is in neither is refused at upload.</p>
          <ul className="space-y-2">
            {form.aliases.map((a, i) => (
              <li key={i} className="flex flex-wrap items-center gap-2">
                <Input className="max-w-xs" aria-label={`Branch name in the register ${i + 1}`} value={a.name} disabled={!edit} onChange={(e) => setAlias(i, { name: e.target.value })} />
                <span className="text-slate-400" aria-hidden="true">→</span>
                <Select className="w-auto" aria-label={`Branch for ${a.name || `name ${i + 1}`}`} value={branchValue(a.branch)} disabled={!edit} onChange={(e) => setAlias(i, { branch: e.target.value })}>
                  <option value="">Choose a branch</option>
                  {branchOptions(branchValue(a.branch)).map((n) => <option key={n} value={n}>{n}</option>)}
                </Select>
                {edit && <Button small variant="ghost" aria-label={`Remove ${a.name || 'this branch name'}`} onClick={() => set({ aliases: form.aliases.filter((_, j) => j !== i) })}><Trash2 size={14} aria-hidden="true" /></Button>}
              </li>
            ))}
          </ul>
          {edit && <Button className="mt-3" small variant="secondary" onClick={() => set({ aliases: [...form.aliases, { name: '', branch: '' }] })}><Plus size={14} aria-hidden="true" />Add branch name</Button>}
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
