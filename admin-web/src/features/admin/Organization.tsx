import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Building2, Pencil, Plus, Search, TriangleAlert } from 'lucide-react'
import { useState } from 'react'
import { Badge, Button, Card, Dialog, ErrorBox, ExportBar, Field, Input, PageTitle, Select, Table, Td } from '../../components/ui'
import { api, errorMessage } from '../../services/api'
import { nameOf, useBranches, useClusters, useRegions } from '../../services/meta'
import type { Branch, Cluster, Region } from '../../types'

type Kind = 'region' | 'cluster' | 'branch'
type Editing = { kind: Kind; item?: Region | Cluster | Branch }

function EditDialog({ editing, onClose }: { editing: Editing; onClose: () => void }) {
  const qc = useQueryClient()
  const { data: regions } = useRegions()
  const { data: clusters } = useClusters()
  const it = editing.item as (Partial<Branch> & Partial<Cluster>) | undefined
  const [v, setV] = useState({ name: it?.name ?? '', code: it?.code ?? '', region_id: it?.region_id ?? '', cluster_id: it?.cluster_id ?? '', address: it?.address ?? '', status: it?.status ?? 'active' })
  const set = (k: keyof typeof v) => (e: { target: { value: string } }) => setV({ ...v, [k]: e.target.value })
  const url = `/${editing.kind === 'branch' ? 'branches' : `${editing.kind}s`}`
  const m = useMutation({
    mutationFn: async () => {
      const body: Record<string, unknown> = { name: v.name.trim(), code: v.code.trim() }
      if (editing.kind !== 'region') body.region_id = v.region_id || null
      if (editing.kind === 'branch') Object.assign(body, { cluster_id: v.cluster_id || null, address: v.address.trim() || null })
      if (it) body.status = v.status
      return it ? api.patch(`${url}/${it.id}`, body) : api.post(url, body)
    },
    onSuccess: () => { ['regions', 'clusters', 'branches', 'org-managers'].forEach((k) => qc.invalidateQueries({ queryKey: [k] })); onClose() },
  })
  const label = { region: 'region', cluster: 'cluster', branch: 'branch' }[editing.kind]
  return (
    <Dialog title={`${it ? 'Edit' : 'Add'} ${label}`} onClose={onClose}>
      <ErrorBox error={m.error ? errorMessage(m.error) : null} />
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Name"><Input value={v.name} onChange={set('name')} /></Field>
        <Field label="Code"><Input value={v.code} onChange={set('code')} /></Field>
        {editing.kind !== 'region' && <Field label="Region"><Select value={v.region_id} onChange={set('region_id')}><option value="">—</option>{regions?.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}</Select></Field>}
        {editing.kind === 'branch' && <Field label="Cluster (optional)"><Select value={v.cluster_id} onChange={set('cluster_id')}><option value="">No cluster</option>{clusters?.filter((c) => !v.region_id || c.region_id === v.region_id).map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</Select></Field>}
        {editing.kind === 'branch' && <div className="sm:col-span-2"><Field label="Address"><Input value={v.address} onChange={set('address')} /></Field></div>}
        {it && <Field label="Status"><Select value={v.status} onChange={set('status')}><option value="active">Active</option><option value="inactive">Inactive</option></Select></Field>}
      </div>
      {editing.kind === 'branch' && <p className="mt-3 text-xs text-slate-500">A branch's region follows its cluster. Moving a branch to another region moves its future entries, scopes and reports with it.</p>}
      <div className="mt-5 flex justify-end gap-2"><Button variant="secondary" onClick={onClose}>Cancel</Button><Button disabled={m.isPending || !v.name.trim() || !v.code.trim()} onClick={() => m.mutate()}>Save</Button></div>
    </Dialog>
  )
}

type Heads = Record<'branches' | 'clusters' | 'regions', Record<string, string[]>>

function Head({ names, none }: { names?: string[]; none: string }) {
  return names?.length ? <span className="text-xs text-slate-600">{names.join(', ')}</span>
    : <span className="rounded-full bg-gold-100 px-2 py-0.5 text-xs font-medium text-gold-700">{none}</span>
}

/** Branch–region map (section 3) with optional clusters, and who heads each (set under Users): a branch with no BM has
 *  its leads answered by the RBH; a region with no RBH would leave those leads with nobody. */
export default function Organization() {
  const { data: regions } = useRegions()
  const { data: clusters } = useClusters()
  const { data: branches } = useBranches()
  const { data: heads } = useQuery({ queryKey: ['org-managers'], queryFn: async () => (await api.get<Heads>('/org/managers')).data })
  const orphanBranches = branches?.filter((b) => !heads?.branches[b.id]?.length && b.region_id && !heads?.regions[b.region_id]?.length) ?? []
  const [editing, setEditing] = useState<Editing | null>(null)
  const [regionQuery, setRegionQuery] = useState('')
  const [clusterQuery, setClusterQuery] = useState('')
  const [branchQuery, setBranchQuery] = useState('')

  const filteredRegions = (regions ?? []).filter((r) => {
    const q = regionQuery.trim().toLowerCase()
    if (!q) return true
    const rbh = heads?.regions[r.id]?.join(' ')?.toLowerCase() ?? ''
    return r.name.toLowerCase().includes(q) || r.code.toLowerCase().includes(q) || rbh.includes(q)
  })

  const filteredClusters = (clusters ?? []).filter((c) => {
    const q = clusterQuery.trim().toLowerCase()
    if (!q) return true
    const reg = nameOf(regions, c.region_id).toLowerCase()
    const rtm = heads?.clusters[c.id]?.join(' ')?.toLowerCase() ?? ''
    return c.name.toLowerCase().includes(q) || reg.includes(q) || rtm.includes(q)
  })

  const sortedBranches = [...(branches ?? [])].sort(
    (a, b) => nameOf(regions, a.region_id).localeCompare(nameOf(regions, b.region_id)) || a.name.localeCompare(b.name)
  )

  const filteredBranches = sortedBranches.filter((b) => {
    const q = branchQuery.trim().toLowerCase()
    if (!q) return true
    const reg = nameOf(regions, b.region_id).toLowerCase()
    const clu = nameOf(clusters, b.cluster_id).toLowerCase()
    const bm = heads?.branches[b.id]?.join(' ')?.toLowerCase() ?? ''
    return (
      b.name.toLowerCase().includes(q) ||
      b.code.toLowerCase().includes(q) ||
      reg.includes(q) ||
      clu.includes(q) ||
      bm.includes(q)
    )
  })

  return (
    <div className="flex-1 flex flex-col min-h-0">
      <PageTitle subtitle="Regions, optional clusters and branches. Seeded from Annex A with placeholder branch codes: replace them with the real ones."
        actions={<><Button variant="secondary" onClick={() => setEditing({ kind: 'region' })}><Plus size={16} aria-hidden="true" />Region</Button>
          <Button variant="secondary" onClick={() => setEditing({ kind: 'cluster' })}><Plus size={16} aria-hidden="true" />Cluster</Button>
          <Button onClick={() => setEditing({ kind: 'branch' })}><Plus size={16} aria-hidden="true" />Branch</Button></>}>
        Organization
      </PageTitle>

      <div className="mb-2.5 space-y-1.5 shrink-0">
        {heads && orphanBranches.length > 0 && (
          <div className="flex items-center gap-2 rounded-lg border border-amber-200/80 bg-amber-50/80 px-3 py-1.5 text-xs text-amber-900" role="alert">
            <TriangleAlert size={14} className="shrink-0 text-amber-600" aria-hidden="true" />
            <span className="truncate">
              <strong>Nobody answers the leads of {orphanBranches.length} {orphanBranches.length === 1 ? 'branch' : 'branches'}</strong>{' '}
              ({orphanBranches.slice(0, 4).map((b) => b.name).join(', ')}{orphanBranches.length > 4 ? ` and ${orphanBranches.length - 4} more` : ''}):
              no BM in the branch and no RBH in its region. Set one under Users &amp; roles.
            </span>
          </div>
        )}
        <div className="flex items-center gap-2 rounded-lg border border-amber-200/80 bg-amber-50/80 px-3 py-1.5 text-xs text-amber-900" role="alert">
          <TriangleAlert size={14} className="shrink-0 text-amber-600" aria-hidden="true" />
          <span className="truncate">
            <strong>Open questions for Aham:</strong> Madurai (RoTN U vs RoTN C); Krishnagiri (RoTN C vs Chennai form). Edit branch once confirmed.
          </span>
        </div>
      </div>

      <div className="grid gap-3.5 lg:grid-cols-[300px_minmax(0,1fr)] flex-1 min-h-0 max-h-[calc(100vh-15rem)] h-[calc(100vh-15rem)] items-stretch">
        <div className="flex flex-col gap-3 min-h-0 h-full">
          <Card
            title={`Regions (${filteredRegions.length})`}
            flush
            className="flex-1 min-h-0 flex flex-col"
            actions={
              <div className="relative w-28 sm:w-36">
                <Search size={13} className="pointer-events-none absolute left-2 top-1/2 -translate-y-1/2 text-slate-400" aria-hidden="true" />
                <Input
                  placeholder="Search..."
                  value={regionQuery}
                  onChange={(e) => setRegionQuery(e.target.value)}
                  className="h-7 pl-6 text-xs"
                />
              </div>
            }
          >
            <div className="flex-1 min-h-0 overflow-y-auto custom-scrollbar border-t border-slate-100">
              <ul className="divide-y divide-slate-100">
                {filteredRegions.map((r) => (
                  <li key={r.id} className="flex items-center justify-between px-4 py-2 text-sm">
                    <span><span className="font-medium text-slate-900">{r.name}</span> <span className="text-xs text-slate-400">{r.code}</span>
                      <span className="block text-xs">RBH: <Head names={heads?.regions[r.id]} none="No RBH" /></span></span>
                    <Button small variant="ghost" aria-label={`Edit ${r.name}`} onClick={() => setEditing({ kind: 'region', item: r })}><Pencil size={14} aria-hidden="true" /></Button>
                  </li>
                ))}
                {!filteredRegions.length && <li className="px-4 py-3 text-xs text-slate-500">No regions match.</li>}
              </ul>
            </div>
          </Card>

          <Card
            title={`Clusters (${filteredClusters.length})`}
            flush
            className="flex-1 min-h-0 flex flex-col"
            actions={
              <div className="relative w-28 sm:w-36">
                <Search size={13} className="pointer-events-none absolute left-2 top-1/2 -translate-y-1/2 text-slate-400" aria-hidden="true" />
                <Input
                  placeholder="Search..."
                  value={clusterQuery}
                  onChange={(e) => setClusterQuery(e.target.value)}
                  className="h-7 pl-6 text-xs"
                />
              </div>
            }
          >
            <div className="flex-1 min-h-0 overflow-y-auto custom-scrollbar border-t border-slate-100">
              <ul className="divide-y divide-slate-100">
                {filteredClusters.map((c) => (
                  <li key={c.id} className="flex items-center justify-between px-4 py-2 text-sm">
                    <span><span className="font-medium text-slate-900">{c.name}</span>
                      <span className="block text-xs text-slate-500">{nameOf(regions, c.region_id)}</span>
                      <span className="block text-xs">RTM: <Head names={heads?.clusters[c.id]} none="No RTM" /></span></span>
                    <Button small variant="ghost" aria-label={`Edit ${c.name}`} onClick={() => setEditing({ kind: 'cluster', item: c })}><Pencil size={14} aria-hidden="true" /></Button>
                  </li>
                ))}
                {!filteredClusters.length && <li className="px-4 py-3 text-xs text-slate-500">No clusters yet.</li>}
              </ul>
            </div>
          </Card>
        </div>

        <Card
          title={`Branches (${filteredBranches.length})`}
          flush
          className="flex-1 min-h-0 flex flex-col h-full"
          actions={
            <div className="flex items-center gap-2">
              <div className="relative w-36 sm:w-48">
                <Search size={13} className="pointer-events-none absolute left-2 top-1/2 -translate-y-1/2 text-slate-400" aria-hidden="true" />
                <Input
                  placeholder="Search branches..."
                  value={branchQuery}
                  onChange={(e) => setBranchQuery(e.target.value)}
                  className="h-7 pl-6 text-xs"
                />
              </div>
              <ExportBar
                name="Branches"
                header={['Branch', 'Branch code', 'Region', 'Cluster', 'Branch Manager', 'Status']}
                rows={async () => filteredBranches.map((b) => [
                  b.name, b.code, nameOf(regions, b.region_id), nameOf(clusters, b.cluster_id),
                  heads?.branches[b.id]?.join(', ') || (b.region_id && heads?.regions[b.region_id]?.length ? 'No BM: RBH answers' : 'No BM, no RBH'),
                  b.status
                ])}
                className="!border-b-0 !bg-transparent !p-0"
              />
            </div>
          }
        >
          <Table
            head={['Branch', 'Branch code', 'Region', 'Cluster', 'Branch Manager', 'Status', '']}
            maxHeight="h-full flex-1"
            containerClassName="flex-1 min-h-0 flex flex-col"
            className="flex-1 min-h-0"
          >
            {filteredBranches.map((b) => (
              <tr key={b.id}>
                <Td className="font-medium text-slate-900">{b.name}</Td>
                <Td className="font-mono text-xs">{b.code}</Td>
                <Td>{nameOf(regions, b.region_id)}</Td>
                <Td>{nameOf(clusters, b.cluster_id)}</Td>
                <Td><Head names={heads?.branches[b.id]} none={b.region_id && heads?.regions[b.region_id]?.length ? 'No BM: RBH answers' : 'No BM, no RBH'} /></Td>
                <Td><Badge value={b.status} /></Td>
                <Td><Button small variant="ghost" aria-label={`Edit ${b.name}`} onClick={() => setEditing({ kind: 'branch', item: b })}><Pencil size={14} aria-hidden="true" /></Button></Td>
              </tr>
            ))}
            {!filteredBranches.length && (
              <tr>
                <td colSpan={7} className="px-4 py-4 text-center text-xs text-slate-500">No branches match.</td>
              </tr>
            )}
          </Table>
        </Card>
      </div>
      {editing && <EditDialog editing={editing} onClose={() => setEditing(null)} />}
    </div>
  )
}
