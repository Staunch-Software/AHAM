import {
  BarChart3, Building2, ClipboardList, Download, FileUp, GanttChartSquare, Headphones, LayoutDashboard, ListChecks,
  type LucideIcon, MapPinned, PhoneCall, ScrollText, Settings as SettingsIcon, ShieldCheck, Sparkles, UserCog, Users,
} from 'lucide-react'
import type { PortalKey } from '../types'

export interface NavItem { to: string; label: string; icon: LucideIcon; perms: string[] }
export interface PortalDef {
  key: PortalKey
  title: string
  tagline: string
  audience: string
  blurb: string
  groups: { title: string; items: NavItem[] }[]
}

export const PORTALS: Record<PortalKey, PortalDef> = {
  manage: {
    key: 'manage', title: 'Management portal', tagline: 'Management',
    audience: 'Branch Manager · Cluster Manager (RTM) · Region Manager (RBH) · Product Manager · Business Manager',
    blurb: 'Your team’s entries, daily compliance, leads to answer and numbers to correct — for your branch, cluster or region.',
    groups: [
      { title: 'Overview', items: [{ to: 'dashboard', label: 'Dashboard', icon: LayoutDashboard, perms: ['dashboard.read'] }] },
      {
        title: 'Field work', items: [
          { to: 'leads', label: 'Leads to answer', icon: ListChecks, perms: ['branch.answer'] },
          { to: 'actions', label: 'Open actions', icon: ClipboardList, perms: ['entries.read'] },
          { to: 'entries', label: 'Entries', icon: GanttChartSquare, perms: ['entries.read'] },
          { to: 'compliance', label: 'Daily compliance', icon: BarChart3, perms: ['compliance.read'] },
          { to: 'map', label: 'Field map', icon: MapPinned, perms: ['map.read'] },
        ],
      },
      { title: 'People', items: [{ to: 'team', label: 'Team', icon: Users, perms: ['team.read'] }] },
    ],
  },
  callcentre: {
    key: 'callcentre', title: 'Call-centre portal', tagline: 'Call centre',
    audience: 'Callers · Master owner (call-centre lead)',
    blurb: 'Today’s calling list, the questions and lead card on every call, allocation, follow-ups and the login register.',
    groups: [
      {
        title: 'Calling', items: [
          { to: 'calls', label: 'My calls', icon: PhoneCall, perms: ['calls.work'] },
          { to: 'run', label: 'Daily run & allocation', icon: Sparkles, perms: ['calls.manage'] },
          { to: 'tracker', label: 'Follow-up tracker', icon: ClipboardList, perms: ['calls.manage'] },
          { to: 'green-channel', label: 'Green channel', icon: ShieldCheck, perms: ['calls.manage'] },
          { to: 'cc-actions', label: 'Call-centre actions', icon: Headphones, perms: ['calls.manage'] },
        ],
      },
      {
        title: 'Insight', items: [
          { to: 'dashboard', label: 'Dashboard', icon: LayoutDashboard, perms: ['dashboard.read'] },
          { to: 'performance', label: 'Caller performance', icon: BarChart3, perms: ['calls.manage'] },
          { to: 'entries', label: 'Entries', icon: GanttChartSquare, perms: ['calls.manage'] },
        ],
      },
      { title: 'Data', items: [{ to: 'uploads', label: 'Login register', icon: FileUp, perms: ['login_register.upload'] }] },
    ],
  },
  admin: {
    key: 'admin', title: 'HR & Admin portal', tagline: 'HR & Admin',
    audience: 'Sankalp monitor (HR) · MIS (Credit / Ops) · System admin',
    blurb: 'Roster, attendance and login-register uploads, compliance, review queues, the Takeoff export, users and settings.',
    groups: [
      { title: 'Overview', items: [{ to: 'dashboard', label: 'Dashboard', icon: LayoutDashboard, perms: ['dashboard.read'] }] },
      {
        title: 'Sankalp monitor', items: [
          { to: 'entries', label: 'Entries', icon: GanttChartSquare, perms: ['entries.read'] },
          { to: 'compliance', label: 'Daily compliance', icon: BarChart3, perms: ['compliance.read'] },
          { to: 'queues', label: 'Review queues', icon: ListChecks, perms: ['category.review'] },
          { to: 'takeoff', label: 'Takeoff export', icon: Download, perms: ['takeoff.export'] },
          { to: 'map', label: 'Field map', icon: MapPinned, perms: ['map.read'] },
        ],
      },
      {
        title: 'Data', items: [
          { to: 'uploads', label: 'Uploads', icon: FileUp, perms: ['reference.import', 'login_register.upload'] },
          { to: 'team', label: 'Employee roster', icon: Users, perms: ['team.read'] },
        ],
      },
      {
        title: 'Administration', items: [
          { to: 'users', label: 'Users & roles', icon: UserCog, perms: ['users.manage'] },
          { to: 'organization', label: 'Organization', icon: Building2, perms: ['org.manage'] },
          { to: 'settings', label: 'Settings', icon: SettingsIcon, perms: ['settings.manage', 'cp_subtypes.manage', 'reference.import'] },
          { to: 'audit', label: 'Audit log', icon: ScrollText, perms: ['audit.read'] },
        ],
      },
    ],
  },
}

export const navFor = (portal: PortalKey, can: (...p: string[]) => boolean) =>
  PORTALS[portal].groups.map((g) => ({ ...g, items: g.items.filter((i) => can(...i.perms)) })).filter((g) => g.items.length)
