import { QueryClient, QueryClientProvider, useQueryClient } from '@tanstack/react-query'
import { BarChart3, Building2, ClipboardCheck, FileBarChart, LayoutDashboard, LogOut, type LucideIcon, MapPinned, Menu, ScrollText, Settings as SettingsIcon, Users, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { NavLink, Navigate, Outlet, Route, Routes, useLocation } from 'react-router-dom'
import { Avatar, BrandMark, cx, Loading } from '../components/ui'
import Analytics from '../features/analytics/Analytics'
import BranchAgents from '../features/analytics/BranchAgents'
import Audit from '../features/audit/Audit'
import Login from '../features/auth/Login'
import Dashboard from '../features/dashboard/Dashboard'
import Employees from '../features/employees/Employees'
import MapPage from '../features/map/MapPage'
import Organization from '../features/organization/Organization'
import Reports from '../features/reports/Reports'
import Settings from '../features/settings/Settings'
import SubmissionDetail from '../features/submissions/SubmissionDetail'
import SubmissionList from '../features/submissions/SubmissionList'
import { AuthProvider, useAuth } from '../services/auth'
import { useLiveUpdates } from '../services/live'

export const makeQueryClient = () => new QueryClient({ defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } } })

interface NavItem { to: string; label: string; icon: LucideIcon; end?: boolean }

// Business modules only. There is intentionally no form-builder / schema-management UI or route.
const NAV_GROUPS: { title: string; items: NavItem[] }[] = [
  { title: 'Overview', items: [{ to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true }] },
  {
    title: 'Field work',
    items: [
      { to: '/submissions', label: 'Submissions', icon: ClipboardCheck },
      { to: '/analytics', label: 'Performance', icon: BarChart3 },
      { to: '/map', label: 'Field map', icon: MapPinned },
    ],
  },
  {
    title: 'Organization',
    items: [
      { to: '/organization', label: 'Organization', icon: Building2 },
      { to: '/employees', label: 'Employees', icon: Users },
    ],
  },
  {
    title: 'Administration',
    items: [
      { to: '/reports', label: 'Reports', icon: FileBarChart },
      { to: '/settings', label: 'Settings', icon: SettingsIcon },
      { to: '/audit', label: 'Audit log', icon: ScrollText },
    ],
  },
]
const NAV = NAV_GROUPS.flatMap((g) => g.items)

function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const { me, logout } = useAuth()
  return (
    <div className="flex h-full flex-col bg-gradient-to-b from-brand-800 to-brand-900 text-brand-100">
      <div className="px-5 pb-5 pt-6"><BrandMark dark /></div>
      <nav aria-label="Main" className="flex-1 space-y-5 overflow-y-auto px-3 pb-4">
        {NAV_GROUPS.map((g) => (
          <div key={g.title}>
            <p className="mb-1.5 px-3 text-[11px] font-semibold uppercase tracking-wider text-brand-300/70">{g.title}</p>
            <div className="space-y-0.5">
              {g.items.map((n) => (
                <NavLink key={n.to} to={n.to} end={n.end} onClick={onNavigate}
                  className={({ isActive }) => cx(
                    'group relative flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition focus:outline-none focus-visible:ring-2 focus-visible:ring-gold-400',
                    isActive ? 'bg-white/10 text-white' : 'text-brand-200 hover:bg-white/5 hover:text-white')}>
                  {({ isActive }) => (
                    <>
                      <span className={cx('absolute -left-3 h-5 w-1 rounded-r-full bg-gold-400 transition-opacity', isActive ? 'opacity-100' : 'opacity-0')} aria-hidden="true" />
                      <n.icon size={18} className={isActive ? 'text-gold-400' : 'text-brand-300 group-hover:text-brand-100'} aria-hidden="true" />
                      {n.label}
                    </>
                  )}
                </NavLink>
              ))}
            </div>
          </div>
        ))}
      </nav>
      <div className="border-t border-white/10 p-3">
        <div className="flex items-center gap-3 rounded-xl bg-white/5 p-3">
          <Avatar name={me?.full_name} />
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-white">{me?.full_name}</p>
            <p className="truncate text-xs text-brand-300">{me?.email}</p>
          </div>
          <button type="button" onClick={logout} aria-label="Sign out" title="Sign out"
            className="rounded-lg p-2 text-brand-200 transition hover:bg-white/10 hover:text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-gold-400">
            <LogOut size={18} aria-hidden="true" />
          </button>
        </div>
      </div>
    </div>
  )
}

function Shell() {
  const qc = useQueryClient()
  const live = useLiveUpdates(qc)
  const { pathname } = useLocation()
  const [open, setOpen] = useState(false)
  useEffect(() => setOpen(false), [pathname])
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false)
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open])
  const section = NAV.find((n) => (n.end ? pathname === n.to : pathname.startsWith(n.to)))
  const liveTone = live === 'live' ? 'bg-emerald-50 text-emerald-700 ring-emerald-600/20' : 'bg-amber-50 text-amber-800 ring-amber-600/25'
  const liveDot = live === 'live' ? 'bg-emerald-500' : 'bg-amber-500 animate-pulse'
  return (
    <div className="min-h-screen lg:flex">
      <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-[60] focus:rounded-lg focus:bg-white focus:px-3 focus:py-2 focus:text-sm focus:shadow-pop">Skip to content</a>
      <aside className="hidden w-64 shrink-0 lg:sticky lg:top-0 lg:block lg:h-screen"><Sidebar /></aside>
      {open && (
        <div className="fixed inset-0 z-40 lg:hidden" role="dialog" aria-modal="true" aria-label="Menu">
          <div className="absolute inset-0 bg-brand-950/50 backdrop-blur-[2px]" onClick={() => setOpen(false)} />
          <div className="absolute inset-y-0 left-0 w-72 max-w-[85vw] shadow-pop"><Sidebar onNavigate={() => setOpen(false)} /></div>
        </div>
      )}
      <div className="min-w-0 flex-1">
        <header className="sticky top-0 z-30 flex items-center justify-between gap-3 border-b border-slate-200/80 bg-white/80 px-4 py-3 backdrop-blur lg:px-8">
          <div className="flex items-center gap-3">
            <button type="button" className="rounded-lg p-2 text-slate-600 hover:bg-slate-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 lg:hidden" aria-label="Open menu" onClick={() => setOpen((v) => !v)}>
              {open ? <X size={20} aria-hidden="true" /> : <Menu size={20} aria-hidden="true" />}
            </button>
            <div className="lg:hidden"><BrandMark compact /></div>
            <p className="hidden text-sm text-slate-500 lg:block">
              <span className="text-slate-400">AHAM Housing Finance</span>
              {section && <><span className="mx-2 text-slate-300">/</span><span className="font-medium text-slate-700">{section.label}</span></>}
            </p>
          </div>
          <span data-testid="live-status" className={cx('inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-medium ring-1 ring-inset', liveTone)}>
            <span className={cx('h-2 w-2 rounded-full', liveDot)} aria-hidden="true" />
            {live === 'live' ? 'Live' : live === 'connecting' ? 'Connecting…' : 'Reconnecting…'}
          </span>
        </header>
        <main id="main" className="mx-auto max-w-7xl p-4 lg:p-8"><Outlet /></main>
      </div>
    </div>
  )
}

function Protected() {
  const { me, loading } = useAuth()
  if (loading) return <Loading />
  return me ? <Shell /> : <Navigate to="/login" replace />
}

export function NotFound() {
  return <p className="p-6 text-slate-600">Page not found.</p>
}

export default function App({ client }: { client: QueryClient }) {
  return (
    <QueryClientProvider client={client}>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route element={<Protected />}>
            <Route index element={<Dashboard />} />
            <Route path="submissions" element={<SubmissionList />} />
            <Route path="submissions/:id" element={<SubmissionDetail />} />
            <Route path="analytics" element={<Analytics />} />
            <Route path="analytics/branches/:id" element={<BranchAgents />} />
            <Route path="map" element={<MapPage />} />
            <Route path="organization" element={<Organization />} />
            <Route path="employees" element={<Employees />} />
            <Route path="reports" element={<Reports />} />
            <Route path="settings" element={<Settings />} />
            <Route path="audit" element={<Audit />} />
            <Route path="*" element={<NotFound />} />
          </Route>
        </Routes>
      </AuthProvider>
    </QueryClientProvider>
  )
}
