import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { Users } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Avatar, Badge, Card, EmptyState, ErrorBox, Input, PageTitle, Pager, Select, Skeleton, Table, Td } from '../../components/ui'
import { api, errorMessage } from '../../services/api'
import { allPages } from '../../services/exporting'
import { useAuth } from '../../services/auth'
import { nameOf, useBranches, useRoles } from '../../services/meta'
import type { Employee, Page } from '../../types'

/** The people placed in the branches I can see (read-only; HR maintains the roster). In the HR & Admin portal this
 *  is the whole employee roster, so the Sankalp monitor can check who is who without uploading anything. */
export default function Team() {
  const { path, portal } = useAuth()
  const hr = portal === 'admin'
  const [q, setQ] = useState('')
  const [role, setRole] = useState('')
  const [page, setPage] = useState(1)
  const { data: branches } = useBranches()
  const { data: roles } = useRoles()
  const { data, isLoading, error } = useQuery({
    queryKey: ['team', q, role, page],
    queryFn: async () => (await api.get<Page<Employee>>('/employees', { params: { q: q || undefined, role: role || undefined, page, page_size: 25 } })).data,
    placeholderData: keepPreviousData,
  })
  const label = (r: string) => roles?.roles.find((x) => x.key === r)?.label ?? r
  return (
    <>
      <PageTitle subtitle={hr ? 'Everyone on the roster (FOS Spoke): Emp ID, designation, branch, spoke, joining and exit dates. Changed by the roster upload.'
        : 'From the HR roster. Their entries are under Entries; their daily count under Daily compliance.'}>{hr ? 'Employee roster' : 'Team'}</PageTitle>
      <div className="mb-4 flex flex-wrap gap-2">
        <Input className="max-w-sm" placeholder="Search name or Emp ID" value={q} onChange={(e) => { setQ(e.target.value); setPage(1) }} />
        <Select aria-label="Role" className="w-auto" value={role} onChange={(e) => { setRole(e.target.value); setPage(1) }}>
          <option value="">All roles</option>{roles?.roles.map((r) => <option key={r.key} value={r.key}>{r.label}</option>)}
        </Select>
      </div>
      <ErrorBox error={error ? errorMessage(error) : null} />
      <Card flush>
        {isLoading || !data ? <div className="space-y-2 p-5">{Array.from({ length: 5 }, (_, i) => <Skeleton key={i} className="h-10" />)}</div>
          : data.items.length === 0 ? <EmptyState icon={<Users size={20} />} title="No one found." />
            : (
              <Table head={['Name (Emp ID)', 'Role', 'Branch', 'Spoke', 'Joining date', 'Exit date', 'Account status']} exportName="Team"
                exportAll={async () => (await allPages<Employee>('/employees', { q: q || undefined, role: role || undefined })).map((u) => [
                  `${u.full_name} (${u.employee_code})`, `${label(u.role)}${u.designation ? ` · ${u.designation}` : ''}`, nameOf(branches, u.branch_id),
                  u.spoke, u.joining_date, u.exit_date, u.status])}>
                {data.items.map((u) => (
                  <tr key={u.id}>
                    <Td><div className="flex items-center gap-3"><Avatar name={u.full_name} size="sm" /><div>
                      <Link className="font-medium text-brand-800 hover:underline" to={`${path('entries')}?q=${encodeURIComponent(u.employee_code)}`}>{u.full_name}</Link>
                      <div className="text-xs text-slate-500">{u.employee_code}</div></div></div></Td>
                    <Td>{label(u.role)}{u.designation && <div className="text-xs text-slate-500">{u.designation}</div>}</Td>
                    <Td>{nameOf(branches, u.branch_id)}</Td><Td>{u.spoke ?? '—'}</Td><Td>{u.joining_date ?? '—'}</Td><Td>{u.exit_date ?? '—'}</Td><Td><Badge value={u.status} /></Td>
                  </tr>
                ))}
              </Table>
            )}
        {data && data.total > 0 && <Pager page={page} pageSize={25} total={data.total} onChange={setPage} />}
      </Card>
    </>
  )
}
