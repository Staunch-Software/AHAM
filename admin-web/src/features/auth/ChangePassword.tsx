import { zodResolver } from '@hookform/resolvers/zod'
import { KeyRound } from 'lucide-react'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { BrandMark, Button, ErrorBox, Field, Input } from '../../components/ui'
import { errorMessage } from '../../services/api'
import { useAuth } from '../../services/auth'

const schema = z.object({
  current: z.string().min(1, 'Enter the temporary password'),
  next: z.string().min(8, 'At least 8 characters'),
  again: z.string(),
}).refine((v) => v.next === v.again, { path: ['again'], message: 'The two passwords differ' })
type Values = z.infer<typeof schema>

/** Shown instead of the portal while the account still has a temporary password. */
export default function ChangePassword() {
  const { me, changePassword, logout } = useAuth()
  const [error, setError] = useState<string | null>(null)
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<Values>({ resolver: zodResolver(schema) })
  const onSubmit = async (v: Values) => {
    setError(null)
    try { await changePassword(v.current, v.next) } catch (e) { setError(errorMessage(e)) }
  }
  return (
    <div className="grid min-h-screen place-items-center bg-slate-50 p-6">
      <div className="w-full max-w-md rounded-2xl border border-slate-200/80 bg-white p-8 shadow-card">
        <BrandMark />
        <div className="mt-8 flex items-start gap-3">
          <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-gold-100 text-gold-700"><KeyRound size={18} aria-hidden="true" /></span>
          <div>
            <h1 className="text-xl font-semibold text-brand-900">Choose your own password</h1>
            <p className="mt-1 text-sm text-slate-500">Welcome, {me?.full_name}. Replace the temporary password HR gave you before you continue.</p>
          </div>
        </div>
        <div className="mt-6">
          <ErrorBox error={error} />
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
            <Field label="Temporary password" error={errors.current?.message}><Input type="password" autoComplete="current-password" {...register('current')} /></Field>
            <Field label="New password" error={errors.next?.message}><Input type="password" autoComplete="new-password" {...register('next')} /></Field>
            <Field label="New password again" error={errors.again?.message}><Input type="password" autoComplete="new-password" {...register('again')} /></Field>
            <Button type="submit" disabled={isSubmitting} className="w-full py-2.5">{isSubmitting ? 'Saving…' : 'Save and continue'}</Button>
          </form>
          <button type="button" onClick={logout} className="mt-4 w-full text-center text-sm text-slate-500 hover:text-brand-700">Sign out</button>
        </div>
      </div>
    </div>
  )
}
