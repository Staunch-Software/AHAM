import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactElement } from 'react'
import { Link, Navigate, Route, Routes } from 'react-router-dom'
import { Loading } from '../components/ui'
import Audit from '../features/admin/Audit'
import Organization from '../features/admin/Organization'
import Queues from '../features/admin/Queues'
import Settings from '../features/admin/Settings'
import Takeoff from '../features/admin/Takeoff'
import Uploads from '../features/admin/Uploads'
import Users from '../features/admin/Users'
import ChangePassword from '../features/auth/ChangePassword'
import Login from '../features/auth/Login'
import PortalChooser from '../features/auth/PortalChooser'
import Actions from '../features/branch/Actions'
import BranchLeads from '../features/branch/BranchLeads'
import CallPerformance from '../features/callcentre/CallPerformance'
import CallScreen from '../features/callcentre/CallScreen'
import CcActions from '../features/callcentre/CcActions'
import DailyRun from '../features/callcentre/DailyRun'
import GreenChannel from '../features/callcentre/GreenChannel'
import MyCalls from '../features/callcentre/MyCalls'
import TrackerList from '../features/callcentre/TrackerList'
import Compliance from '../features/compliance/Compliance'
import Dashboard from '../features/dashboard/Dashboard'
import EntryDetail from '../features/entries/EntryDetail'
import EntryList from '../features/entries/EntryList'
import DisbursementRegister from '../features/irr/DisbursementRegister'
import IrrExceptions from '../features/irr/IrrExceptions'
import IrrReport from '../features/irr/IrrReport'
import IrrSettings from '../features/irr/IrrSettings'
import MapPage from '../features/map/MapPage'
import Team from '../features/team/Team'
import { AuthProvider, useAuth } from '../services/auth'
import type { PortalKey } from '../types'
import { PORTALS, navFor } from './portals'
import Shell from './Shell'

export const makeQueryClient = () => new QueryClient({ defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } } })

const PAGES: Record<string, () => ReactElement> = {
  dashboard: () => <Dashboard />, leads: () => <BranchLeads />, actions: () => <Actions />, entries: () => <EntryList />,
  compliance: () => <Compliance />, map: () => <MapPage />, team: () => <Team />, calls: () => <MyCalls />,
  run: () => <DailyRun />, tracker: () => <TrackerList />, 'green-channel': () => <GreenChannel />,
  'cc-actions': () => <CcActions />, performance: () => <CallPerformance />, uploads: () => <Uploads />,
  queues: () => <Queues />, takeoff: () => <Takeoff />, users: () => <Users />, organization: () => <Organization />,
  settings: () => <Settings />, audit: () => <Audit />,
  irr: () => <IrrReport />, 'irr-data': () => <DisbursementRegister />, 'irr-exceptions': () => <IrrExceptions />,
  'irr-settings': () => <IrrSettings />,
}

export function NotFound() {
  return <p className="p-6 text-slate-600">Page not found. <Link className="font-medium text-brand-700 underline" to="/">Go to the portals</Link></p>
}

/** A page the signed-in role may not open shows a plain message instead (the server refuses the data anyway). */
function Gate({ perms, children }: { perms: string[]; children: ReactElement }) {
  const { can } = useAuth()
  return can(...perms) ? children : <p className="p-6 text-slate-600" role="alert">Your role cannot open this page.</p>
}

function Protected() {
  const { me, loading, portal, path } = useAuth()
  if (loading) return <Loading />
  if (!me) return <Navigate to={path('login')} replace />
  if (me.must_change_password) return <ChangePassword />
  if (me.portal !== portal) return <Navigate to="/" replace />
  return <Shell />
}

function PortalHome() {
  const { portal, can, path } = useAuth()
  const first = navFor(portal, can)[0]?.items[0]
  return first ? <Navigate to={path(first.to)} replace /> : <p className="p-6 text-slate-600">Your role has no pages in this portal.</p>
}

function PortalRoutes({ portal }: { portal: PortalKey }) {
  const items = PORTALS[portal].groups.flatMap((g) => g.items)
  return (
    <Routes>
      <Route path="login" element={<Login />} />
      <Route element={<Protected />}>
        <Route index element={<PortalHome />} />
        {items.map((i) => <Route key={i.to} path={i.to} element={<Gate perms={i.perms}>{PAGES[i.to]()}</Gate>} />)}
        <Route path="entries/:id" element={<Gate perms={['entries.read']}><EntryDetail /></Gate>} />
        {portal === 'callcentre' && <Route path="calls/:id" element={<Gate perms={['calls.work']}><CallScreen /></Gate>} />}
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  )
}

export default function App({ client }: { client: QueryClient }) {
  return (
    <QueryClientProvider client={client}>
      <Routes>
        <Route path="/" element={<PortalChooser />} />
        {(Object.keys(PORTALS) as PortalKey[]).map((p) => (
          <Route key={p} path={`/${p}/*`} element={<AuthProvider key={p} portal={p}><PortalRoutes portal={p} /></AuthProvider>} />
        ))}
        <Route path="/login" element={<Navigate to="/" replace />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </QueryClientProvider>
  )
}
