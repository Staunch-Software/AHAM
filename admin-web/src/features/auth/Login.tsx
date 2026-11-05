import { zodResolver } from '@hookform/resolvers/zod'
import type { AxiosError } from 'axios'
import { ArrowLeft, CheckCircle2, MapPin, PhoneCall, ShieldCheck } from 'lucide-react'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { z } from 'zod'
import { PORTALS } from '../../app/portals'
import { BrandMark, Button, Field, Input } from '../../components/ui'
import { errorMessage } from '../../services/api'
import { useAuth } from '../../services/auth'

const schema = z.object({
  identifier: z.string().trim().min(1, 'Enter your Emp ID or email'),
  password: z.string().min(1, 'Password is required'),
})
type Values = z.infer<typeof schema>

const POINTS = [
  { icon: MapPin, text: 'Entries keep the time and place of the Submit press' },
  { icon: PhoneCall, text: 'Calls, questions and RAG in one record' },
  { icon: ShieldCheck, text: 'Each role sees only its own branch, cluster or region' },
]

/** Decorative entry card: shows what an entry carries, no real data. */
function EntryPreview() {
  return (
    <div aria-hidden="true" className="relative mx-auto w-full max-w-sm select-none">
      <div className="absolute -inset-6 rounded-[2rem] bg-gold-400/10 blur-2xl" />
      <div className="relative space-y-3 overflow-hidden rounded-2xl bg-white p-4 text-sm shadow-pop">
        <div className="flex items-center justify-between">
          <span className="font-mono text-xs font-semibold text-brand-800">AHFL01810-20261015-090706</span>
          <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-700 ring-1 ring-inset ring-emerald-600/20">
            <CheckCircle2 size={12} />Green
          </span>
        </div>
        <div className="grid grid-cols-2 gap-2 text-xs">
          {[['Category', 'Lead'], ['Status', 'Validated'], ['Next step', 'SO / branch visit'], ['Lead ID', 'TCS-48213']].map(([k, v]) => (
            <div key={k} className="rounded-lg bg-slate-50 px-3 py-2"><div className="text-slate-500">{k}</div><div className="font-medium text-slate-800">{v}</div></div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default function Login() {
  const { me, login, portal, path } = useAuth()
  const p = PORTALS[portal]
  const nav = useNavigate()
  const [error, setError] = useState<{ text: string; portal?: string } | null>(null)
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<Values>({ resolver: zodResolver(schema) })
  if (me) return <Navigate to={path()} replace />
  const onSubmit = async (v: Values) => {
    setError(null)
    try {
      await login(v.identifier.trim(), v.password)
      nav(path())
    } catch (e) {
      const d = (e as AxiosError<any>)?.response?.data?.detail
      setError({ text: errorMessage(e), portal: d?.code === 'wrong_portal' ? d.portal : undefined })
    }
  }
  return (
    <div className="grid min-h-screen bg-white lg:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)]">
      <section className="relative hidden overflow-hidden bg-gradient-to-br from-brand-800 via-brand-800 to-brand-900 p-12 text-white lg:flex lg:flex-col lg:justify-between">
        <div className="pointer-events-none absolute -right-24 -top-24 h-96 w-96 rounded-full bg-brand-600/30 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-32 -left-16 h-96 w-96 rounded-full bg-gold-500/10 blur-3xl" />
        <div className="relative"><BrandMark dark tagline={p.tagline} /></div>
        <div className="relative space-y-10">
          <div>
            <h2 className="max-w-md text-4xl font-semibold leading-tight tracking-tight !text-white">From the field to a <span className="text-gold-400">login</span>.</h2>
            <p className="mt-4 max-w-md text-base text-brand-200">{p.blurb}</p>
          </div>
          <EntryPreview />
          <ul className="space-y-3">
            {POINTS.map(({ icon: Icon, text }) => (
              <li key={text} className="flex items-center gap-3 text-sm text-brand-100">
                <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-white/10 text-gold-400"><Icon size={16} aria-hidden="true" /></span>{text}
              </li>
            ))}
          </ul>
        </div>
        <p className="relative text-xs text-brand-300">AHAM Housing Finance · Sankalp</p>
      </section>

      <section className="flex items-center justify-center p-6 sm:p-12">
        <div className="w-full max-w-sm">
          <Link to="/" className="mb-8 inline-flex items-center gap-1.5 text-sm font-medium text-slate-500 hover:text-brand-700"><ArrowLeft size={16} aria-hidden="true" />All portals</Link>
          <div className="mb-8 lg:hidden"><BrandMark tagline={p.tagline} /></div>
          <p className="text-xs font-semibold uppercase tracking-wider text-gold-700">{p.title}</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight text-brand-900">Sign in</h1>
          <p className="mt-1.5 text-sm text-slate-500">{p.audience}</p>
          <div className="mt-6">
            {error && (
              <div role="alert" className="mb-4 rounded-lg border border-roof-200 bg-roof-50 px-3 py-2 text-sm text-roof-700">
                {error.text}
                {error.portal && error.portal !== 'mobile' && (
                  <> <Link className="font-semibold underline" to={`/${error.portal}/login`}>Go to the {PORTALS[error.portal as keyof typeof PORTALS]?.title}</Link></>
                )}
                {error.portal === 'mobile' && <> Use the AHAM Sankalp app on your phone.</>}
              </div>
            )}
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
              <Field label="Emp ID or email" error={errors.identifier?.message}><Input autoComplete="username" placeholder="AHFL01810" {...register('identifier')} /></Field>
              <Field label="Password" error={errors.password?.message}><Input type="password" autoComplete="current-password" {...register('password')} /></Field>
              <Button type="submit" disabled={isSubmitting} className="w-full py-2.5">{isSubmitting ? 'Signing in…' : 'Sign in'}</Button>
            </form>
          </div>
          <p className="mt-6 text-center text-xs text-slate-500">New here? HR gives you a temporary password; you choose your own at the first sign-in.</p>
        </div>
      </section>
    </div>
  )
}
