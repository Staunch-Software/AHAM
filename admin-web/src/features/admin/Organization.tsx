import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Building2, Pencil, Plus } from 'lucide-react'
import { useState } from 'react'
import { Badge, Button, Card, Dialog, ErrorBox, Field, Input, Note, PageTitle, Select, Table, Td } from '../../components/ui'
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
  return (
    <>
      <PageTitle subtitle="Regions, optional clusters and branches. Seeded from Annex A with placeholder branch codes: replace them with the real ones."
        actions={<><Button variant="secondary" onClick={() => setEditing({ kind: 'region' })}><Plus size={16} aria-hidden="true" />Region</Button>
          <Button variant="secondary" onClick={() => setEditing({ kind: 'cluster' })}><Plus size={16} aria-hidden="true" />Cluster</Button>
          <Button onClick={() => setEditing({ kind: 'branch' })}><Plus size={16} aria-hidden="true" />Branch</Button></>}>
        Organization
      </PageTitle>
      {heads && orphanBranches.length > 0 && (
        <Note tone="gold"><strong>Nobody answers the leads of {orphanBranches.length} {orphanBranches.length === 1 ? 'branch' : 'branches'}</strong>{' '}
          ({orphanBranches.slice(0, 5).map((b) => b.name).join(', ')}{orphanBranches.length > 5 ? ` and ${orphanBranches.length - 5} more` : ''}):
          no BM in the branch and no RBH in its region. Set one under Users &amp; roles.</Note>
      )}
      <Note tone="gold">Open questions for Aham: <strong>Madurai</strong> is under RoTN U here (call-centre allocation) but under RoTN C in the regional pipeline files; <strong>Krishnagiri</strong> is under RoTN C here but appears in the Chennai Sankalp form. Edit the branch once confirmed.</Note>
      <div className="grid gap-6 lg:grid-cols-[320px_minmax(0,1fr)]">
        <div className="space-y-6">
          <Card title={`Regions (${regions?.length ?? 0})`} flush>
            <ul className="divide-y divide-slate-100">
              {regions?.map((r) => (
                <li key={r.id} className="flex items-center justify-between px-5 py-2.5 text-sm">
                  <span><span className="font-medium text-slate-900">{r.name}</span> <span className="text-xs text-slate-400">{r.code}</span>
                    <span className="block">RBH: <Head names={heads?.regions[r.id]} none="No RBH" /></span></span>
                  <Button small variant="ghost" aria-label={`Edit ${r.name}`} onClick={() => setEditing({ kind: 'region', item: r })}><Pencil size={14} aria-hidden="true" /></Button>
                </li>
              ))}
            </ul>
          </Card>
          <Card title={`Clusters (${clusters?.length ?? 0})`} subtitle="Not every branch has one" flush>
            <ul className="divide-y divide-slate-100">
              {clusters?.map((c) => (
                <li key={c.id} className="flex items-center justify-between px-5 py-2.5 text-sm">
                  <span><span className="font-medium text-slate-900">{c.name}</span><span className="block text-xs text-slate-500">{nameOf(regions, c.region_id)}</span>
                    <span className="block">RTM: <Head names={heads?.clusters[c.id]} none="No RTM" /></span></span>
                  <Button small variant="ghost" aria-label={`Edit ${c.name}`} onClick={() => setEditing({ kind: 'cluster', item: c })}><Pencil size={14} aria-hidden="true" /></Button>
                </li>
              ))}
              {!clusters?.length && <li className="px-5 py-4 text-sm text-slate-500">No clusters yet.</li>}
            </ul>
          </Card>
        </div>
        <Card title={`Branches (${branches?.length ?? 0})`} flush actions={<Building2 size={18} className="text-slate-400" />}>
          <Table head={['Branch', 'Code', 'Region', 'Cluster', 'BM', 'Status', '']}>
            {[...(branches ?? [])].sort((a, b) => nameOf(regions, a.region_id).localeCompare(nameOf(regions, b.region_id)) || a.name.localeCompare(b.name)).map((b) => (
              <tr key={b.id}><Td className="font-medium text-slate-900">{b.name}</Td><Td className="font-mono text-xs">{b.code}</Td><Td>{nameOf(regions, b.region_id)}</Td><Td>{nameOf(clusters, b.cluster_id)}</Td><Td><Head names={heads?.branches[b.id]} none={b.region_id && heads?.regions[b.region_id]?.length ? 'No BM: RBH answers' : 'No BM, no RBH'} /></Td><Td><Badge value={b.status} /></Td>
                <Td><Button small variant="ghost" aria-label={`Edit ${b.name}`} onClick={() => setEditing({ kind: 'branch', item: b })}><Pencil size={14} aria-hidden="true" /></Button></Td></tr>
            ))}
          </Table>
        </Card>
      </div>
      {editing && <EditDialog editing={editing} onClose={() => setEditing(null)} />}
    </>
  )
}
