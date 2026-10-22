import { zodResolver } from '@hookform/resolvers/zod'
import { Camera, CheckCircle2, CloudOff, MapPin, ShieldCheck } from 'lucide-react'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Navigate, useNavigate } from 'react-router-dom'
import { z } from 'zod'
import { BrandMark, Button, ErrorBox, Field, Input } from '../../components/ui'
import { errorMessage } from '../../services/api'
import { useAuth } from '../../services/auth'

const schema = z.object({ email: z.string().email('Enter a valid email'), password: z.string().min(1, 'Password is required') })
type Values = z.infer<typeof schema>

const POINTS = [
  { icon: Camera, text: 'Photo evidence with its own time and place' },
  { icon: CloudOff, text: 'Reports are saved offline and sync when signal returns' },
  { icon: ShieldCheck, text: 'Review, correct and approve in one place' },
]

/** Decorative preview of a verified visit: it shows what the product records, no real data. */
function VisitPreview() {
  return (
    <div aria-hidden="true" className="relative mx-auto w-full max-w-sm select-none">
      <div className="absolute -inset-6 rounded-[2rem] bg-gold-400/10 blur-2xl" />
      <div className="relative overflow-hidden rounded-2xl bg-white shadow-pop">
        <div className="relative h-36 bg-gradient-to-br from-brand-100 to-sky-100">
          <svg className="absolute inset-0 h-full w-full" viewBox="0 0 320 144" fill="none">
            <path d="M0 96 C60 80 90 120 160 100 S280 70 320 90" stroke="#fff" strokeWidth="10" strokeLinecap="round" />
            <path d="M70 0 C80 40 60 80 90 144" stroke="#fff" strokeWidth="8" strokeLinecap="round" />
            <path d="M230 0 C220 50 250 90 240 144" stroke="#fff" strokeWidth="6" strokeLinecap="round" />
            <circle cx="205" cy="82" r="30" fill="#283079" fillOpacity="0.08" />
            <circle cx="205" cy="82" r="14" fill="#283079" fillOpacity="0.14" />
          </svg>
          <span className="absolute left-[188px] top-[34px] grid h-9 w-9 place-items-center rounded-full rounded-bl-none bg-roof-500 text-white shadow-lg [transform:rotate(-45deg)]">
            <MapPin size={18} className="[transform:rotate(45deg)]" />
          </span>
        </div>
        <div className="space-y-2.5 p-4 text-sm">
          <div className="flex items-center justify-between">
            <span className="font-semibold text-brand-900">Field meeting report</span>
            <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-medium text-emerald-700 ring-1 ring-inset ring-emerald-600/20">
              <CheckCircle2 size={12} />Approved
            </span>
          </div>
          <div className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2">
            <span className="flex items-center gap-2 text-slate-600"><Camera size={14} className="text-brand-600" />Photo taken</span>
            <span className="tabular text-xs text-slate-500">11:42 · ±5 m</span>
          </div>
          <div className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2">
            <span className="flex items-center gap-2 text-slate-600"><MapPin size={14} className="text-roof-500" />Submitted</span>
            <span className="tabular text-xs text-slate-500">11:46 · ±8 m</span>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function Login() {
  const { me, login } = useAuth()
  const nav = useNavigate()
  const [error, setError] = useState<string | null>(null)
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<Values>({ resolver: zodResolver(schema) })
  if (me) return <Navigate to="/" replace />
  const onSubmit = async (v: Values) => {
    setError(null)
    try { await login(v.email, v.password); nav('/') } catch (e) { setError(errorMessage(e)) }
  }
  return (
    <div className="grid min-h-screen bg-white lg:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)]">
      <section className="relative hidden overflow-hidden bg-gradient-to-br from-brand-800 via-brand-800 to-brand-900 p-12 text-white lg:flex lg:flex-col lg:justify-between">
        <div className="pointer-events-none absolute -right-24 -top-24 h-96 w-96 rounded-full bg-brand-600/30 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-32 -left-16 h-96 w-96 rounded-full bg-gold-500/10 blur-3xl" />
        <div className="relative"><BrandMark dark /></div>
        <div className="relative space-y-10">
          <div>
            <h2 className="max-w-md text-4xl font-semibold leading-tight tracking-tight !text-white">Field visits you can <span className="text-gold-400">verify</span>.</h2>
            <p className="mt-4 max-w-md text-base text-brand-200">Every meeting is recorded where and when it happened, so reviewers can approve with confidence.</p>
          </div>
          <VisitPreview />
          <ul className="space-y-3">
            {POINTS.map(({ icon: Icon, text }) => (
              <li key={text} className="flex items-center gap-3 text-sm text-brand-100">
                <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-white/10 text-gold-400"><Icon size={16} aria-hidden="true" /></span>{text}
              </li>
            ))}
          </ul>
        </div>
        <p className="relative text-xs text-brand-300">AHAM Housing Finance · FieldSync</p>
      </section>

      <section className="flex items-center justify-center p-6 sm:p-12">
        <div className="w-full max-w-sm">
          <div className="mb-8 lg:hidden"><BrandMark /></div>
          <h1 className="text-2xl font-semibold tracking-tight text-brand-900">Welcome back</h1>
          <p className="mt-1.5 text-sm text-slate-500">Sign in to the FieldSync admin portal.</p>
          <div className="mt-6">
            <ErrorBox error={error} />
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
              <Field label="Email" error={errors.email?.message}><Input type="email" autoComplete="username" placeholder="you@company.com" {...register('email')} /></Field>
              <Field label="Password" error={errors.password?.message}><Input type="password" autoComplete="current-password" {...register('password')} /></Field>
              <Button type="submit" disabled={isSubmitting} className="w-full py-2.5">{isSubmitting ? 'Signing in…' : 'Sign in'}</Button>
            </form>
          </div>
          <p className="mt-6 text-center text-xs text-slate-500">Administrators only. Field agents sign in on the FieldSync mobile app.</p>
        </div>
      </section>
    </div>
  )
}
