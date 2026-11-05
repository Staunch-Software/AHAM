import { ArrowRight, Building2, Headphones, IdCard, PhoneCall, Smartphone, Sparkles, UserCheck, Users } from 'lucide-react'
import { Link } from 'react-router-dom'
import { PORTALS } from '../../app/portals'
import { BrandMark } from '../../components/ui'

const CARDS = [
  { key: 'manage', icon: Users, accent: 'from-brand-700 to-brand-900' },
  { key: 'callcentre', icon: Headphones, accent: 'from-gold-500 to-gold-700' },
  { key: 'admin', icon: Building2, accent: 'from-roof-500 to-roof-700' },
] as const

const LADDER = ['Sales Officer', 'Branch Manager', 'Cluster Manager', 'Region Manager', 'Product Manager', 'Business Manager']
const FLOW = [
  { icon: Smartphone, label: 'SO meets a customer', hint: 'Entry ID, time and GPS' },
  { icon: PhoneCall, label: 'Call centre calls', hint: 'Questions, RAG' },
  { icon: Sparkles, label: 'Lead card', hint: 'TCS lead ID' },
  { icon: UserCheck, label: 'Branch works it', hint: 'Code and date' },
  { icon: IdCard, label: 'Login confirmed', hint: 'From the MIS register' },
]

export default function PortalChooser() {
  return (
    <div className="min-h-screen bg-slate-50">
      <header className="relative overflow-hidden bg-gradient-to-br from-brand-800 via-brand-800 to-brand-900 text-white">
        <div className="pointer-events-none absolute -right-24 -top-24 h-96 w-96 rounded-full bg-brand-600/30 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-40 left-10 h-96 w-96 rounded-full bg-gold-500/10 blur-3xl" />
        <div className="relative mx-auto max-w-6xl px-6 pb-28 pt-10">
          <BrandMark dark tagline="AHAM Housing Finance" />
          <h1 className="mt-12 max-w-2xl text-4xl font-semibold leading-tight tracking-tight !text-white sm:text-5xl">
            Every field meeting, <span className="text-gold-400">followed to a login</span>.
          </h1>
          <p className="mt-4 max-w-2xl text-base text-brand-200">
            Sankalp records each person a Sales Officer meets, calls them, classifies the lead and tracks it to the branch and the
            login register. Choose your portal to sign in.
          </p>
          <ol className="mt-10 grid gap-3 sm:grid-cols-5" aria-label="How a Sankalp entry moves">
            {FLOW.map(({ icon: Icon, label, hint }, i) => (
              <li key={label} className="flex items-center gap-3 rounded-xl bg-white/5 px-3 py-3 ring-1 ring-white/10">
                <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-gold-400/15 text-gold-400"><Icon size={18} aria-hidden="true" /></span>
                <span className="min-w-0 leading-tight">
                  <span className="block text-[11px] font-semibold uppercase tracking-wider text-brand-300">Step {i + 1}</span>
                  <span className="block text-sm font-medium text-white">{label}</span>
                  <span className="block text-xs text-brand-300">{hint}</span>
                </span>
              </li>
            ))}
          </ol>
        </div>
      </header>

      <main className="relative mx-auto -mt-16 max-w-6xl px-6 pb-16">
        <div className="grid gap-5 md:grid-cols-3">
          {CARDS.map(({ key, icon: Icon, accent }) => {
            const p = PORTALS[key]
            return (
              <Link key={key} to={`/${key}/login`} data-testid={`portal-${key}`}
                className="group flex flex-col rounded-2xl border border-slate-200/80 bg-white p-6 shadow-card transition hover:-translate-y-0.5 hover:shadow-pop focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500">
                <span className={`grid h-12 w-12 place-items-center rounded-xl bg-gradient-to-br text-white shadow-sm ${accent}`}><Icon size={22} aria-hidden="true" /></span>
                <h2 className="mt-5 text-lg font-semibold text-brand-900">{p.title}</h2>
                <p className="mt-1 text-xs font-medium text-slate-500">{p.audience}</p>
                <p className="mt-3 flex-1 text-sm text-slate-600">{p.blurb}</p>
                <span className="mt-5 inline-flex items-center gap-1.5 text-sm font-semibold text-brand-700">
                  Sign in <ArrowRight size={16} className="transition group-hover:translate-x-0.5" aria-hidden="true" />
                </span>
              </Link>
            )
          })}
        </div>

        <div className="mt-6 grid gap-5 md:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)]">
          <div className="flex items-start gap-4 rounded-2xl border border-gold-300/60 bg-gold-50 p-5">
            <span className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-white text-gold-700 shadow-sm"><Smartphone size={20} aria-hidden="true" /></span>
            <div>
              <h2 className="text-sm font-semibold text-brand-900">Sales Officers use the AHAM Sankalp app</h2>
              <p className="mt-1 text-sm text-slate-600">Entries are made on the phone, offline too. The time and place are those of the Submit press, even when the entry syncs later.</p>
            </div>
          </div>
          <div className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-card">
            <h2 className="text-sm font-semibold text-brand-900">Who sees what</h2>
            <p className="mt-1 text-xs text-slate-500">Each level sees its own area: a branch, a cluster, a region, or the whole company.</p>
            <ol className="mt-4 flex flex-wrap items-center gap-1.5 text-xs font-medium">
              {LADDER.map((r, i) => (
                <li key={r} className="flex items-center gap-1.5">
                  <span className="rounded-full bg-brand-50 px-2.5 py-1 text-brand-800 ring-1 ring-inset ring-brand-200">{r}</span>
                  {i < LADDER.length - 1 && <ArrowRight size={12} className="text-slate-400" aria-hidden="true" />}
                </li>
              ))}
            </ol>
          </div>
        </div>
      </main>
    </div>
  )
}
