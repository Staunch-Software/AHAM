import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Copy, KeyRound, Pencil, Plus, UserCog } from 'lucide-react'
import { useState } from 'react'
import { Avatar, Badge, Button, Card, Confirm, Dialog, EmptyState, ErrorBox, Field, Input, PageTitle, Pager, Select, Skeleton, Table, Td } from '../../components/ui'
import { api, errorMessage } from '../../services/api'
import { nameOf, useBranches, useClusters, useRegions, useRoles } from '../../services/meta'
import type { Employee, Page } from '../../types'

const PORTAL_NAME: Record<string, string> = { mobile: 'Mobile app', manage: 'Management', callcentre: 'Call centre', admin: 'HR & Admin' }

function PasswordShown({ code, password, onClose }: { code: string; password: string; onClose: () => void }) {
  return (
    <Dialog title="Temporary password" onClose={onClose}>
      <p className="text-sm text-slate-600">Give this to <strong>{code}</strong> privately. It is shown only now. They must choose their own password at the first sign-in.</p>
      <div className="mt-4 flex items-center justify-between gap-3 rounded-xl bg-brand-50 px-4 py-3">
        <code className="text-lg font-semibold tracking-wider text-brand-900" data-testid="temp-password">{password}</code>
        <Button small variant="secondary" onClick={() => navigator.clipboard?.writeText(password)}><Copy size={14} aria-hidden="true" />Copy</Button>
      </div>
      <div className="mt-5 flex justify-end"><Button onClick={onClose}>Done</Button></div>
    </Dialog>
  )
}

function PersonDialog({ person, onClose, onCreated }: { person?: Employee; onClose: () => void; onCreated: (code: string, pw: string) => void }) {
  const qc = useQueryClient()
  const { data: roles } = useRoles()
  const { data: branches } = useBranches()
  const { data: clusters } = useClusters()
  const { data: regions } = useRegions()
  const [v, setV] = useState({
    employee_code: person?.employee_code ?? '', full_name: person?.full_name ?? '', email: person?.email ?? '', phone: person?.phone ?? '',
    role: person?.role ?? 'sales_officer', designation: person?.designation ?? '', branch_id: person?.branch_id ?? '', cluster_id: person?.cluster_id ?? '',
    region_id: person?.region_id ?? '', spoke: person?.spoke ?? '', joining_date: person?.joining_date ?? '', exit_date: person?.exit_date ?? '', status: person?.status ?? 'active',
  })
  const set = (k: keyof typeof v) => (e: { target: { value: string } }) => setV({ ...v, [k]: e.target.value })
  const role = roles?.roles.find((r) => r.key === v.role)
  const n = (s: string) => s.trim() || null
  const m = useMutation({
    mutationFn: async () => {
      const body = {
        full_name: v.full_name.trim(), email: n(v.email), phone: n(v.phone), role: v.role, designation: n(v.designation),
        branch_id: n(v.branch_id), cluster_id: n(v.cluster_id), region_id: n(v.region_id), spoke: n(v.spoke),
        joining_date: n(v.joining_date), exit_date: n(v.exit_date),
      }
      return person ? (await api.patch(`/employees/${person.id}`, { ...body, status: v.status })).data
        : (await api.post('/employees', { ...body, employee_code: v.employee_code.trim() })).data
    },
    onSuccess: (d) => { qc.invalidateQueries({ queryKey: ['users'] }); if (!person) onCreated(d.employee_code, d.temporary_password); onClose() },
  })
  return (
    <Dialog title={person ? `Edit ${person.full_name}` : 'Add a person'} onClose={onClose} wide>
      <ErrorBox error={m.error ? errorMessage(m.error) : null} />
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Emp ID"><Input value={v.employee_code} onChange={set('employee_code')} disabled={!!person} placeholder="AHFL01810" /></Field>
        <Field label="Name"><Input value={v.full_name} onChange={set('full_name')} /></Field>
        <Field label="Role">
          <Select value={v.role} onChange={set('role')}>
            {['mobile', 'manage', 'callcentre', 'admin'].map((p) => (
              <optgroup key={p} label={PORTAL_NAME[p]}>{roles?.roles.filter((r) => r.portal === p).map((r) => <option key={r.key} value={r.key}>{r.label}</option>)}</optgroup>
            ))}
          </Select>
        </Field>
        <Field label="Designation (as on the roster)"><Input value={v.designation} onChange={set('designation')} placeholder={v.role === 'sales_officer' ? 'RO, RM or ABM' : ''} /></Field>
        {role?.placement === 'branch' && <Field label="Branch"><Select value={v.branch_id} onChange={set('branch_id')}><option value="">Choose…</option>{branches?.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}</Select></Field>}
        {role?.placement === 'cluster' && <Field label="Cluster"><Select value={v.cluster_id} onChange={set('cluster_id')}><option value="">Choose…</option>{clusters?.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</Select></Field>}
        {role?.placement === 'region' && <Field label="Region"><Select value={v.region_id} onChange={set('region_id')}><option value="">Choose…</option>{regions?.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}</Select></Field>}
        {role?.placement === 'branch' && <Field label="Spoke"><Input value={v.spoke} onChange={set('spoke')} /></Field>}
        <Field label="Email (optional)"><Input type="email" value={v.email} onChange={set('email')} /></Field>
        <Field label="Phone (optional)"><Input value={v.phone} onChange={set('phone')} /></Field>
        <Field label="Joining date"><Input type="date" value={v.joining_date} onChange={set('joining_date')} /></Field>
        <Field label="Exit date"><Input type="date" value={v.exit_date} onChange={set('exit_date')} /></Field>
        {person && <Field label="Status"><Select value={v.status} onChange={set('status')}><option value="active">Active</option><option value="inactive">Inactive</option></Select></Field>}
      </div>
      {role && <p className="mt-4 rounded-lg bg-slate-50 px-3 py-2 text-xs text-slate-600">Signs in at: <strong>{PORTAL_NAME[role.portal]}</strong> · sees: {role.scope === 'own' ? 'own entries' : role.scope === 'allocated' ? 'entries on their calling list' : `their ${role.scope}`}</p>}
      <div className="mt-5 flex justify-end gap-2"><Button variant="secondary" onClick={onClose}>Cancel</Button><Button disabled={m.isPending || !v.full_name.trim() || (!person && !v.employee_code.trim())} onClick={() => m.mutate()}>{person ? 'Save' : 'Add and create password'}</Button></div>
    </Dialog>
  )
}

export default function Users() {
  const qc = useQueryClient()
  const { data: roles } = useRoles()
  const { data: branches } = useBranches()
  const [q, setQ] = useState('')
  const [role, setRole] = useState('')
  const [page, setPage] = useState(1)
  const [editing, setEditing] = useState<Employee | 'new' | null>(null)
  const [resetting, setResetting] = useState<Employee | null>(null)
  const [shown, setShown] = useState<{ code: string; password: string } | null>(null)
  const { data, isLoading, error } = useQuery({
    queryKey: ['users', q, role, page],
    queryFn: async () => (await api.get<Page<Employee>>('/employees', { params: { q: q || undefined, role: role || undefined, page, page_size: 25 } })).data,
    placeholderData: keepPreviousData,
  })
  const reset = useMutation({
    mutationFn: async (u: Employee) => (await api.post(`/employees/${u.id}/temporary-password`)).data,
    onSuccess: (d) => { setShown({ code: d.employee_code, password: d.temporary_password }); setResetting(null); qc.invalidateQueries({ queryKey: ['users'] }) },
  })
  const roleDef = (k: string) => roles?.roles.find((r) => r.key === k)
  return (
    <>
      <PageTitle subtitle="Most people come in through the roster upload. Each role signs in at one portal only." actions={<Button onClick={() => setEditing('new')}><Plus size={16} aria-hidden="true" />Add a person</Button>}>Users & roles</PageTitle>
      <div className="mb-4 grid gap-3 sm:grid-cols-[minmax(0,1fr)_240px]">
        <Input placeholder="Search name, Emp ID or email" value={q} onChange={(e) => { setQ(e.target.value); setPage(1) }} />
        <Select aria-label="Role" value={role} onChange={(e) => { setRole(e.target.value); setPage(1) }}><option value="">All roles</option>{roles?.roles.map((r) => <option key={r.key} value={r.key}>{r.label}</option>)}</Select>
      </div>
      <ErrorBox error={[error, reset.error].map((e) => e && errorMessage(e)).find(Boolean) ?? null} />
      <Card flush>
        {isLoading || !data ? <div className="space-y-2 p-5">{Array.from({ length: 5 }, (_, i) => <Skeleton key={i} className="h-10" />)}</div>
          : data.items.length === 0 ? <EmptyState icon={<UserCog size={20} />} title="No one found." /> : (
            <Table head={['Person', 'Role', 'Portal', 'Placed in', 'Status', '']}>
              {data.items.map((u) => {
                const r = roleDef(u.role)
                return (
                  <tr key={u.id}>
                    <Td><div className="flex items-center gap-3"><Avatar name={u.full_name} size="sm" /><div><div className="font-medium text-slate-900">{u.full_name}</div><div className="text-xs text-slate-500">{u.employee_code}{u.email && ` · ${u.email}`}</div></div></div></Td>
                    <Td>{r?.label ?? u.role}{u.designation && <div className="text-xs text-slate-500">{u.designation}</div>}</Td>
                    <Td>{PORTAL_NAME[r?.portal ?? ''] ?? '—'}</Td>
                    <Td>{u.branch_id ? nameOf(branches, u.branch_id) : u.cluster_id ? 'A cluster' : u.region_id ? 'A region' : 'Company-wide'}</Td>
                    <Td><Badge value={u.status} />{u.must_change_password && <div className="mt-1 text-[11px] text-amber-700">Password to set</div>}</Td>
                    <Td className="whitespace-nowrap">
                      <Button small variant="ghost" aria-label={`Edit ${u.full_name}`} onClick={() => setEditing(u)}><Pencil size={14} aria-hidden="true" /></Button>
                      <Button small variant="ghost" aria-label={`Temporary password for ${u.full_name}`} onClick={() => setResetting(u)}><KeyRound size={14} aria-hidden="true" /></Button>
                    </Td>
                  </tr>
                )
              })}
            </Table>
          )}
        {data && data.total > 0 && <Pager page={page} pageSize={25} total={data.total} onChange={setPage} />}
      </Card>
      {editing && <PersonDialog person={editing === 'new' ? undefined : editing} onClose={() => setEditing(null)} onCreated={(code, password) => setShown({ code, password })} />}
      {resetting && <Confirm title="New temporary password" message={`${resetting.full_name} will be signed out everywhere and must choose a new password at the next sign-in.`} confirmLabel="Create password" busy={reset.isPending} onConfirm={() => reset.mutate(resetting)} onCancel={() => setResetting(null)} />}
      {shown && <PasswordShown code={shown.code} password={shown.password} onClose={() => setShown(null)} />}
    </>
  )
}
