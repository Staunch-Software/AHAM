import { useQueryClient } from '@tanstack/react-query'
import { LogOut, Menu, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { Avatar, BrandMark, cx } from '../components/ui'
import { useAuth } from '../services/auth'
import { useLiveUpdates } from '../services/live'
import { PORTALS, navFor } from './portals'

function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const { me, logout, portal, can, path } = useAuth()
  const where = me?.branch_name ?? me?.cluster_name ?? me?.region_name
  return (
    <div className="flex h-full flex-col bg-gradient-to-b from-brand-800 to-brand-900 text-brand-100">
      <div className="px-5 pb-5 pt-6"><BrandMark dark tagline={PORTALS[portal].tagline} /></div>
      <nav aria-label="Main" className="flex-1 space-y-5 overflow-y-auto px-3 pb-4">
        {navFor(portal, can).map((g) => (
          <div key={g.title}>
            <p className="mb-1.5 px-3 text-[11px] font-semibold uppercase tracking-wider text-brand-300/70">{g.title}</p>
            <div className="space-y-0.5">
              {g.items.map((n) => (
                <NavLink key={n.to} to={path(n.to)} onClick={onNavigate}
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
            <p className="truncate text-xs text-brand-300" data-testid="role-line">{me?.role_label}{where ? ` · ${where}` : ''}</p>
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

export default function Shell() {
  const qc = useQueryClient()
  const { portal, can } = useAuth()
  const live = useLiveUpdates(qc, can('dashboard.read', 'calls.work'))
  const { pathname } = useLocation()
  const [open, setOpen] = useState(false)
  useEffect(() => setOpen(false), [pathname])
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false)
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open])
  const seg = pathname.split('/')[2]
  const section = PORTALS[portal].groups.flatMap((g) => g.items).find((n) => n.to === seg)
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
              <span className="text-slate-400">{PORTALS[portal].title}</span>
              {section && <><span className="mx-2 text-slate-300">/</span><span className="font-medium text-slate-700">{section.label}</span></>}
            </p>
          </div>
          {live !== 'off' && (
            <span data-testid="live-status" className={cx('inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-medium ring-1 ring-inset', liveTone)}>
              <span className={cx('h-2 w-2 rounded-full', liveDot)} aria-hidden="true" />
              {live === 'live' ? 'Live' : live === 'connecting' ? 'Connecting…' : 'Reconnecting…'}
            </span>
          )}
        </header>
        <main id="main" className="mx-auto max-w-7xl p-4 lg:p-8"><Outlet /></main>
      </div>
    </div>
  )
}
