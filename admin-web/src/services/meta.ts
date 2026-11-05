import { useQuery } from '@tanstack/react-query'
import type { Branch, Cluster, Employee, Meta, Page, Region, RoleDef } from '../types'
import { api } from './api'

const LONG = 10 * 60_000

/** The fixed lists of the business logic (categories, outcomes, questions, branch codes), from the server. */
export const useMeta = () => useQuery({ queryKey: ['meta'], staleTime: LONG, queryFn: async () => (await api.get<Meta>('/sankalp/meta')).data })
export const useBranches = () => useQuery({ queryKey: ['branches'], staleTime: LONG, queryFn: async () => (await api.get<Branch[]>('/branches')).data })
export const useRegions = () => useQuery({ queryKey: ['regions'], staleTime: LONG, queryFn: async () => (await api.get<Region[]>('/regions')).data })
export const useClusters = () => useQuery({ queryKey: ['clusters'], staleTime: LONG, queryFn: async () => (await api.get<Cluster[]>('/clusters')).data })
export const useRoles = () => useQuery({ queryKey: ['roles'], staleTime: LONG, queryFn: async () => (await api.get<{ portals: Record<string, string>; roles: RoleDef[] }>('/roles')).data })
export const useCallers = (enabled = true) => useQuery({
  queryKey: ['callers'], enabled, staleTime: 60_000,
  queryFn: async () => (await api.get<Page<Employee>>('/employees', { params: { role: 'caller', page_size: 200 } })).data.items,
})
export const useSalesOfficers = (enabled = true) => useQuery({
  queryKey: ['sales-officers'], enabled, staleTime: 60_000,
  queryFn: async () => (await api.get<Page<Employee>>('/employees', { params: { role: 'sales_officer', status: 'active', page_size: 200 } })).data.items,
})

export const nameOf = <T extends { id: string; name: string }>(list: T[] | undefined, id?: string | null) =>
  (id && list?.find((x) => x.id === id)?.name) || '—'
