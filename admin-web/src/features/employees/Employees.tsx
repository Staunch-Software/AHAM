import { zodResolver } from '@hookform/resolvers/zod'
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus, UserX } from 'lucide-react'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { Avatar, Badge, Button, Card, Confirm, Dialog, EmptyState, ErrorBox, Field, Input, PageTitle, Pager, Select, Skeleton, Table, Td } from '../../components/ui'
import { api, errorMessage } from '../../services/api'
import { useAuth } from '../../services/auth'
import type { Branch, Employee, Page } from '../../types'

const base = {
  full_name: z.string().min(1, 'Required').max(200), phone: z.string().max(30).optional(),
  role: z.enum(['admin', 'agent']), branch_id: z.string().optional(), branch_ids: z.array(z.string()).default([]),
}
const createSchema = z.object({
  ...base, employee_code: z.string().min(1, 'Required').max(50), email: z.string().email('Enter a valid email'),
  password: z.string().min(8, 'At least 8 characters'),
})
const editSchema = z.object({ ...base, password: z.string().min(8, 'At least 8 characters').or(z.literal('')).optional() })
type Values = z.infer<typeof createSchema>

function EmployeeDialog({ emp, branches, onClose }: { emp: Employee | null; branches: Branch[]; onClose: () => void }) {
  const qc = useQueryClient()
  const { register, handleSubmit, formState: { errors } } = useForm<Values>({
    resolver: zodResolver(emp ? (editSchema as unknown as typeof createSchema) : createSchema),
    defaultValues: emp
      ? { full_name: emp.full_name, phone: emp.phone ?? '', role: emp.role as 'admin' | 'agent', branch_id: emp.branch_id ?? '', branch_ids: [] }
      : { role: 'agent', branch_ids: [] },
  })
  const save = useMutation({
    mutationFn: (v: Values) => {
      const body: Record<string, unknown> = { ...v, branch_id: v.branch_id || null, phone: v.phone || null }
      if (emp) {
        if (!v.password) delete body.password
        delete body.branch_ids // assignments are managed on create; edit keeps the primary branch only
        delete body.employee_code; delete body.email
        return api.patch(`/employees/${emp.id}`, body)
      }
      body.branch_ids = v.branch_id ? [v.branch_id] : []
      return api.post('/employees', body)
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['employees'] }); onClose() },
  })
  return (
    <Dialog title={emp ? 'Edit employee' : 'Add employee'} onClose={onClose}>
      <ErrorBox error={save.error ? errorMessage(save.error) : null} />
      <form onSubmit={handleSubmit((v) => save.mutate(v))} className="space-y-4" noValidate>
        {!emp && <Field label="Employee ID" error={errors.employee_code?.message}><Input {...register('employee_code')} /></Field>}
        <Field label="Full name" error={errors.full_name?.message}><Input {...register('full_name')} /></Field>
        {!emp && <Field label="Email (login)" error={errors.email?.message}><Input type="email" {...register('email')} /></Field>}
        <Field label="Phone" error={errors.phone?.message}><Input {...register('phone')} /></Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Role"><Select {...register('role')}><option value="agent">Agent</option><option value="admin">Admin</option></Select></Field>
          <Field label="Branch"><Select {...register('branch_id')}><option value="">None</option>{branches.filter((b) => b.status === 'active').map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}</Select></Field>
        </div>
        <Field label={emp ? 'New password (leave blank to keep)' : 'Initial password'} error={errors.password?.message}><Input type="password" autoComplete="new-password" {...register('password')} /></Field>
        <div className="flex justify-end gap-2 pt-1"><Button type="button" variant="secondary" onClick={onClose}>Cancel</Button><Button type="submit" disabled={save.isPending}>Save</Button></div>
      </form>
    </Dialog>
  )
}

export default function Employees() {
  const { me } = useAuth()
  const qc = useQueryClient()
  const [q, setQ] = useState('')
  const [branch, setBranch] = useState('')
  const [status, setStatus] = useState('')
  const [page, setPage] = useState(1)
  const [editing, setEditing] = useState<Employee | null | undefined>(undefined)
  const [toggle, setToggle] = useState<Employee | null>(null)
  const branches = useQuery({ queryKey: ['branches'], queryFn: async () => (await api.get<Branch[]>('/branches')).data })
  const { data, isLoading, error } = useQuery({
    queryKey: ['employees', { q, branch, status, page }],
    queryFn: async () => (await api.get<Page<Employee>>('/employees', { params: { q: q || undefined, branch_id: branch || undefined, status: status || undefined, page, page_size: 25 } })).data,
    placeholderData: keepPreviousData,
  })
  const flip = useMutation({
    mutationFn: (e: Employee) => api.patch(`/employees/${e.id}`, { status: e.status === 'active' ? 'inactive' : 'active' }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['employees'] }); setToggle(null) },
  })
  const bName = (id: string | null) => branches.data?.find((b) => b.id === id)?.name ?? '—'
  return (
    <>
      <PageTitle subtitle="People who can sign in to the field app or this portal." actions={<Button onClick={() => setEditing(null)}><Plus size={16} aria-hidden="true" />Add employee</Button>}>Employees</PageTitle>
      <div className="mb-5 grid gap-3 rounded-2xl border border-slate-200/80 bg-white p-4 shadow-card md:grid-cols-3">
        <Field label="Search"><Input placeholder="Name, email or employee ID" value={q} onChange={(e) => { setQ(e.target.value); setPage(1) }} /></Field>
        <Field label="Branch"><Select value={branch} onChange={(e) => { setBranch(e.target.value); setPage(1) }}><option value="">All</option>{branches.data?.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}</Select></Field>
        <Field label="Status"><Select value={status} onChange={(e) => { setStatus(e.target.value); setPage(1) }}><option value="">All</option><option value="active">Active</option><option value="inactive">Inactive</option></Select></Field>
      </div>
      <ErrorBox error={error ? errorMessage(error) : null} />
      {isLoading ? (
        <Card flush><div className="space-y-3 p-5" role="status" aria-label="Loading employees">{Array.from({ length: 5 }, (_, i) => <Skeleton key={i} className="h-12" />)}</div></Card>
      ) : (
        <Card flush>
          <Table head={['Employee ID', 'Name', 'Email', 'Role', 'Branch', 'Status', '']}>
            {data?.items.map((e) => (
              <tr key={e.id}>
                <Td className="whitespace-nowrap font-mono text-xs text-slate-500">{e.employee_code}</Td>
                <Td><div className="flex items-center gap-2.5"><Avatar name={e.full_name} size="sm" /><span className="font-medium text-slate-800">{e.full_name}</span></div></Td>
                <Td className="text-slate-500">{e.email}</Td>
                <Td><span className={`rounded-md px-2 py-0.5 text-xs font-medium ${e.role === 'admin' ? 'bg-brand-100 text-brand-800' : 'bg-slate-100 text-slate-700'}`}>{e.role}</span></Td>
                <Td className="whitespace-nowrap">{bName(e.branch_id)}</Td>
                <Td><Badge value={e.status} /></Td>
                <Td className="whitespace-nowrap space-x-2 text-right">
                  <Button variant="secondary" small onClick={() => setEditing(e)}>Edit</Button>
                  {e.id !== me?.id && <Button variant="secondary" small onClick={() => setToggle(e)}>{e.status === 'active' ? 'Deactivate' : 'Activate'}</Button>}
                </Td>
              </tr>
            ))}
          </Table>
          {data?.items.length === 0 && <EmptyState icon={<UserX size={22} />} title="No employees match." hint="Try a different search or clear the filters." />}
          {data && <Pager page={data.page} pageSize={data.page_size} total={data.total} onChange={setPage} />}
        </Card>
      )}
      {editing !== undefined && <EmployeeDialog emp={editing} branches={branches.data ?? []} onClose={() => setEditing(undefined)} />}
      {toggle && <Confirm title={`${toggle.status === 'active' ? 'Deactivate' : 'Activate'} employee`} message={toggle.status === 'active' ? `Deactivate ${toggle.full_name}? They will be signed out immediately; their submissions are kept.` : `Reactivate ${toggle.full_name}?`} confirmLabel={toggle.status === 'active' ? 'Deactivate' : 'Activate'} busy={flip.isPending} onConfirm={() => flip.mutate(toggle)} onCancel={() => setToggle(null)} />}
    </>
  )
}
