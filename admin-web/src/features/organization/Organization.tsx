import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CheckCircle2, MapPin, Plus } from 'lucide-react'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { Badge, Button, Card, Confirm, Dialog, ErrorBox, Field, Input, PageTitle, Select, Skeleton, Table, Td } from '../../components/ui'
import { api, errorMessage } from '../../services/api'
import type { Branch, Company, Organization as Org } from '../../types'

const num = z.preprocess((v) => (v === '' || v == null ? null : Number(v)), z.number().nullable())
const branchSchema = z.object({
  name: z.string().min(1, 'Required').max(200), code: z.string().min(1, 'Required').max(50),
  organization_id: z.string().nullable().optional(), address: z.string().max(500).optional(),
  latitude: num.refine((v) => v == null || (v >= -90 && v <= 90), 'Must be between -90 and 90'),
  longitude: num.refine((v) => v == null || (v >= -180 && v <= 180), 'Must be between -180 and 180'),
})
type BranchValues = z.infer<typeof branchSchema>

function BranchDialog({ branch, orgs, onClose }: { branch: Branch | null; orgs: Org[]; onClose: () => void }) {
  const qc = useQueryClient()
  const { register, handleSubmit, formState: { errors } } = useForm<BranchValues>({
    resolver: zodResolver(branchSchema),
    defaultValues: branch ? { name: branch.name, code: branch.code, organization_id: branch.organization_id ?? '', address: branch.address ?? '', latitude: branch.latitude, longitude: branch.longitude } : {},
  })
  const save = useMutation({
    mutationFn: async (v: BranchValues) => {
      const body = { ...v, organization_id: v.organization_id || null, address: v.address || null }
      if (branch) { const { code, ...patch } = body; void code; await api.patch(`/branches/${branch.id}`, patch) }
      else await api.post('/branches', body)
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['branches'] }); onClose() },
  })
  return (
    <Dialog title={branch ? 'Edit branch' : 'Add branch'} onClose={onClose}>
      <ErrorBox error={save.error ? errorMessage(save.error) : null} />
      <form onSubmit={handleSubmit((v) => save.mutate(v))} className="space-y-4" noValidate>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Name" error={errors.name?.message}><Input {...register('name')} /></Field>
          <Field label="Code" error={errors.code?.message}><Input disabled={!!branch} {...register('code')} /></Field>
        </div>
        <Field label="Organization"><Select {...register('organization_id')}><option value="">None</option>{orgs.map((o) => <option key={o.id} value={o.id}>{o.name}</option>)}</Select></Field>
        <Field label="Address" error={errors.address?.message}><Input {...register('address')} /></Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Latitude" error={errors.latitude?.message}><Input inputMode="decimal" {...register('latitude')} /></Field>
          <Field label="Longitude" error={errors.longitude?.message}><Input inputMode="decimal" {...register('longitude')} /></Field>
        </div>
        <p className="text-xs text-slate-500">Coordinates place the branch on the field map.</p>
        <div className="flex justify-end gap-2 pt-1"><Button type="button" variant="secondary" onClick={onClose}>Cancel</Button><Button type="submit" disabled={save.isPending}>Save</Button></div>
      </form>
    </Dialog>
  )
}

function Branches({ orgs }: { orgs: Org[] }) {
  const qc = useQueryClient()
  const { data, isLoading } = useQuery({ queryKey: ['branches'], queryFn: async () => (await api.get<Branch[]>('/branches')).data })
  const [editing, setEditing] = useState<Branch | null | undefined>(undefined)
  const [toggle, setToggle] = useState<Branch | null>(null)
  const status = useMutation({
    mutationFn: (b: Branch) => api.patch(`/branches/${b.id}`, { status: b.status === 'active' ? 'inactive' : 'active' }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['branches'] }); setToggle(null) },
  })
  return (
    <Card title="Branches" subtitle="Where agents are based. Branch coordinates appear on the field map." flush actions={<Button className="mr-5" onClick={() => setEditing(null)}><Plus size={16} aria-hidden="true" />Add branch</Button>}>
      {isLoading ? <div className="space-y-3 p-5" role="status" aria-label="Loading branches">{Array.from({ length: 4 }, (_, i) => <Skeleton key={i} className="h-10" />)}</div> : (
        <Table head={['Name', 'Code', 'Address', 'Coordinates', 'Status', '']}>
          {data?.map((b) => (
            <tr key={b.id}>
              <Td className="whitespace-nowrap font-medium text-slate-800">{b.name}</Td><Td className="font-mono text-xs text-slate-500">{b.code}</Td><Td>{b.address ?? '—'}</Td>
              <Td className="whitespace-nowrap">{b.latitude != null && b.longitude != null
                ? <span className="inline-flex items-center gap-1 text-slate-700"><MapPin size={13} className="text-roof-500" aria-hidden="true" />{`${b.latitude}, ${b.longitude}`}</span> : '—'}</Td>
              <Td><Badge value={b.status} /></Td>
              <Td className="whitespace-nowrap space-x-2 text-right">
                <Button variant="secondary" small onClick={() => setEditing(b)}>Edit</Button>
                <Button variant="secondary" small onClick={() => setToggle(b)}>{b.status === 'active' ? 'Deactivate' : 'Activate'}</Button>
              </Td>
            </tr>
          ))}
        </Table>
      )}
      {editing !== undefined && <BranchDialog branch={editing} orgs={orgs} onClose={() => setEditing(undefined)} />}
      {toggle && <Confirm title={`${toggle.status === 'active' ? 'Deactivate' : 'Activate'} branch`} message={toggle.status === 'active' ? `Deactivate "${toggle.name}"? Historical submissions are kept.` : `Reactivate "${toggle.name}"?`} confirmLabel={toggle.status === 'active' ? 'Deactivate' : 'Activate'} busy={status.isPending} onConfirm={() => status.mutate(toggle)} onCancel={() => setToggle(null)} />}
    </Card>
  )
}

function CompanyCard() {
  const qc = useQueryClient()
  const { data } = useQuery({ queryKey: ['company'], queryFn: async () => (await api.get<Company[]>('/companies')).data[0] })
  const { register, handleSubmit } = useForm<Partial<Company>>()
  const [saved, setSaved] = useState(false)
  const save = useMutation({
    mutationFn: (v: Partial<Company>) => api.patch(`/companies/${data!.id}`, { name: v.name, contact_email: v.contact_email || null, contact_phone: v.contact_phone || null, address: v.address || null }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['company'] }); setSaved(true) },
  })
  if (!data) return <Skeleton className="h-72" />
  return (
    <Card title="Company" subtitle="Shown to your team; the code cannot be changed.">
      <ErrorBox error={save.error ? errorMessage(save.error) : null} />
      <form className="grid gap-4 md:grid-cols-2" onSubmit={handleSubmit((v) => { setSaved(false); save.mutate(v) })}>
        <Field label="Name"><Input defaultValue={data.name} {...register('name')} /></Field>
        <Field label="Code"><Input value={data.code} disabled readOnly /></Field>
        <Field label="Contact email"><Input defaultValue={data.contact_email ?? ''} {...register('contact_email')} /></Field>
        <Field label="Contact phone"><Input defaultValue={data.contact_phone ?? ''} {...register('contact_phone')} /></Field>
        <div className="md:col-span-2"><Field label="Address"><Input defaultValue={data.address ?? ''} {...register('address')} /></Field></div>
        <div className="flex items-center gap-3"><Button type="submit" disabled={save.isPending}>Save company</Button>{saved && <span role="status" className="inline-flex items-center gap-1.5 text-sm font-medium text-emerald-700"><CheckCircle2 size={16} aria-hidden="true" />Saved</span>}</div>
      </form>
    </Card>
  )
}

function Organizations({ orgs }: { orgs: Org[] }) {
  const qc = useQueryClient()
  const { register, handleSubmit, reset, formState: { errors } } = useForm<{ name: string; code: string }>({ resolver: zodResolver(z.object({ name: z.string().min(1, 'Required'), code: z.string().min(1, 'Required') })) })
  const add = useMutation({ mutationFn: (v: { name: string; code: string }) => api.post('/organizations', v), onSuccess: () => { qc.invalidateQueries({ queryKey: ['organizations'] }); reset() } })
  return (
    <Card title="Organizations (optional divisions)" subtitle="Group branches into divisions if you need to.">
      <ErrorBox error={add.error ? errorMessage(add.error) : null} />
      {orgs.length > 0
        ? <div className="mb-4 overflow-hidden rounded-xl border border-slate-200"><Table head={['Name', 'Code', 'Status']}>{orgs.map((o) => <tr key={o.id}><Td className="font-medium text-slate-800">{o.name}</Td><Td className="font-mono text-xs text-slate-500">{o.code}</Td><Td><Badge value={o.status} /></Td></tr>)}</Table></div>
        : <p className="mb-4 rounded-xl bg-slate-50 px-4 py-3 text-sm text-slate-500">No divisions yet. Branches work fine without them.</p>}
      <form className="flex flex-wrap items-end gap-3 rounded-xl border border-dashed border-slate-300 p-4" onSubmit={handleSubmit((v) => add.mutate(v))} noValidate>
        <Field label="Name" error={errors.name?.message}><Input {...register('name')} /></Field>
        <Field label="Code" error={errors.code?.message}><Input {...register('code')} /></Field>
        <Button type="submit" disabled={add.isPending}><Plus size={16} aria-hidden="true" />Add organization</Button>
      </form>
    </Card>
  )
}

export default function Organization() {
  const { data: orgs = [] } = useQuery({ queryKey: ['organizations'], queryFn: async () => (await api.get<Org[]>('/organizations')).data })
  return (
    <>
      <PageTitle subtitle="Your company, its divisions and branches.">Organization</PageTitle>
      <div className="mb-6 grid gap-6 xl:grid-cols-2"><CompanyCard /><Organizations orgs={orgs} /></div>
      <Branches orgs={orgs} />
    </>
  )
}
