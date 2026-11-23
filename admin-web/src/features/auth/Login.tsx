import { zodResolver } from '@hookform/resolvers/zod'
import type { AxiosError } from 'axios'
import { Building2, ShieldCheck } from 'lucide-react'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Navigate, useNavigate } from 'react-router-dom'
import { z } from 'zod'
import { BrandMark, Button, Field, Input } from '../../components/ui'
import { errorMessage } from '../../services/api'
import { useAuth } from '../../services/auth'

const schema = z.object({
  identifier: z.string().trim().min(1, 'Enter your Emp ID or email'),
  password: z.string().min(1, 'Password is required'),
})
type Values = z.infer<typeof schema>

export default function Login() {
  const { me, login, portal } = useAuth()
  const nav = useNavigate()
  const [error, setError] = useState<string | null>(null)
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<Values>({ resolver: zodResolver(schema) })

  // If already authenticated, redirect to the user's home portal
  if (me) {
    const target = me.portal || portal || 'manage'
    return <Navigate to={`/${target}`} replace />
  }

  const onSubmit = async (v: Values) => {
    setError(null)
    try {
      const targetPortal = await login(v.identifier.trim(), v.password)
      nav(`/${targetPortal}`)
    } catch (e) {
      const d = (e as AxiosError<any>)?.response?.data?.detail
      if (d?.code === 'mobile_only') {
        setError(d.message || 'This account is configured for the AHAM Sankalp mobile app.')
      } else if (d?.code === 'wrong_portal') {
        setError(d.message || errorMessage(e))
      } else {
        setError(errorMessage(e))
      }
    }
  }

  return (
    <div className="grid min-h-screen bg-white grid-cols-1 md:grid-cols-2">
      {/* Left Column: Brand Visual & Enterprise Welcome (No Operational Data Leaks) */}
      <section className="relative overflow-hidden bg-gradient-to-br from-brand-800 via-brand-800 to-brand-900 p-8 sm:p-12 text-white flex flex-col justify-between">
        <div className="pointer-events-none absolute -right-24 -top-24 h-96 w-96 rounded-full bg-brand-600/30 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-32 -left-16 h-96 w-96 rounded-full bg-gold-500/10 blur-3xl" />
        
        <div className="relative">
          <BrandMark dark tagline="Housing Finance" />
        </div>

        <div className="relative my-8 space-y-6">
          <div className="inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1 text-xs font-medium text-gold-300 backdrop-blur-sm ring-1 ring-white/15">
            <ShieldCheck size={14} aria-hidden="true" />
            <span>Enterprise Portal</span>
          </div>
          <div>
            <h2 className="max-w-md text-3xl sm:text-4xl font-semibold leading-tight tracking-tight !text-white">
              Unified Portal <span className="text-gold-400">Access</span>.
            </h2>
            <p className="mt-4 max-w-md text-sm sm:text-base text-brand-200">
              Sign in with your employee credentials to securely access your designated workspace.
            </p>
          </div>
          <div className="max-w-sm rounded-2xl bg-white/5 p-4 sm:p-5 ring-1 ring-white/10 backdrop-blur-sm">
            <div className="flex items-center gap-3.5">
              <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-gold-400/15 text-gold-400">
                <Building2 size={20} aria-hidden="true" />
              </span>
              <div>
                <div className="text-sm font-semibold text-white">Central Operations</div>
                <div className="text-xs text-brand-300">Management · Call Centre · Administration</div>
              </div>
            </div>
          </div>
        </div>

        <p className="relative text-xs text-brand-300">AHAM Housing Finance · Sankalp</p>
      </section>

      {/* Right Column: Unified Login Form for All User Types */}
      <section className="flex items-center justify-center p-6 sm:p-12">
        <div className="w-full max-w-sm">
          <div className="mb-8 md:hidden"><BrandMark tagline="Housing Finance" /></div>
          <h1 className="text-2xl font-semibold tracking-tight text-brand-900">Sign in</h1>
          <p className="mt-1.5 text-sm text-slate-500">Enter your employee credentials to continue</p>
          
          <div className="mt-6">
            {error && (
              <div role="alert" className="mb-4 rounded-lg border border-roof-200 bg-roof-50 px-3 py-2 text-sm text-roof-700">
                {error}
              </div>
            )}
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
              <Field label="Emp ID or email" error={errors.identifier?.message}>
                <Input autoComplete="username" placeholder="e.g. AHFL01810" {...register('identifier')} />
              </Field>
              <Field label="Password" error={errors.password?.message}>
                <Input type="password" autoComplete="current-password" {...register('password')} />
              </Field>
              <Button type="submit" disabled={isSubmitting} className="w-full py-2.5">
                {isSubmitting ? 'Signing in…' : 'Sign in'}
              </Button>
            </form>
          </div>

          <p className="mt-6 text-center text-xs text-slate-500">
            New here? HR gives you a temporary password; you choose your own at the first sign-in.
          </p>
        </div>
      </section>
    </div>
  )
}
