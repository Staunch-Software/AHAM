import { Loader2, X } from 'lucide-react'
import { ButtonHTMLAttributes, forwardRef, InputHTMLAttributes, ReactNode, SelectHTMLAttributes, TextareaHTMLAttributes, useEffect, useRef } from 'react'

export const cx = (...c: (string | false | null | undefined)[]) => c.filter(Boolean).join(' ')

/* ---------- buttons and form controls ---------- */

type Variant = 'primary' | 'secondary' | 'danger' | 'ghost' | 'gold'
const VARIANTS: Record<Variant, string> = {
  primary: 'bg-brand-700 text-white shadow-sm hover:bg-brand-800 active:bg-brand-900',
  secondary: 'bg-white text-slate-700 shadow-sm ring-1 ring-inset ring-slate-300 hover:bg-slate-50 active:bg-slate-100',
  danger: 'bg-roof-600 text-white shadow-sm hover:bg-roof-700',
  ghost: 'text-slate-600 hover:bg-slate-100 hover:text-slate-900',
  gold: 'bg-gold-500 font-semibold text-brand-900 shadow-sm hover:bg-gold-400',
}

export function Button({ variant = 'primary', small, className, ...p }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; small?: boolean }) {
  return (
    <button
      {...p}
      className={cx(
        'inline-flex items-center justify-center gap-2 rounded-lg font-medium transition focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50',
        small ? 'px-2.5 py-1.5 text-xs' : 'px-3.5 py-2 text-sm',
        VARIANTS[variant], className,
      )}
    />
  )
}

const field = 'block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm placeholder:text-slate-400 transition focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20 disabled:bg-slate-50 disabled:text-slate-500'

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>((p, ref) => <input ref={ref} {...p} className={cx(field, p.className)} />)
export const Select = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement>>((p, ref) => <select ref={ref} {...p} className={cx(field, 'pr-8', p.className)} />)

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>((p, ref) => <textarea ref={ref} {...p} className={cx(field, 'resize-y', p.className)} />)

export function Field({ label, error, children }: { label: string; error?: string; children: ReactNode }) {
  return (
    <label className="block text-sm">
      <span className="mb-1.5 block text-xs font-medium text-slate-600">{label}</span>
      {children}
      {error && <span role="alert" className="mt-1 block text-xs text-roof-600">{error}</span>}
    </label>
  )
}

/** On/off switch backed by a real checkbox, so it works with keyboards, screen readers and form libraries. */
export function Toggle({ checked, onChange, label, disabled }: { checked: boolean; onChange: (v: boolean) => void; label: string; disabled?: boolean }) {
  return (
    <label className={cx('flex cursor-pointer items-center gap-3 text-sm text-slate-700', disabled && 'cursor-not-allowed opacity-60')}>
      <span className="relative inline-flex h-6 w-11 shrink-0 items-center">
        <input type="checkbox" className="peer sr-only" checked={checked} disabled={disabled} onChange={(e) => onChange(e.target.checked)} />
        <span className="absolute inset-0 rounded-full bg-slate-300 transition peer-checked:bg-brand-700 peer-focus-visible:ring-2 peer-focus-visible:ring-brand-500 peer-focus-visible:ring-offset-2" />
        <span className="absolute left-0.5 h-5 w-5 rounded-full bg-white shadow transition peer-checked:translate-x-5" />
      </span>
      {label}
    </label>
  )
}

/* ---------- layout ---------- */

export const Card = ({ title, subtitle, actions, children, className, flush }: { title?: string; subtitle?: string; actions?: ReactNode; children: ReactNode; className?: string; flush?: boolean }) => (
  <section className={cx('rounded-2xl border border-slate-200/80 bg-white shadow-card', flush ? 'overflow-hidden' : 'p-5', className)}>
    {(title || actions) && (
      <header className={cx('flex flex-wrap items-start justify-between gap-2', flush ? 'px-5 pt-5' : '', 'mb-4')}>
        <div>
          {title && <h2 className="text-sm font-semibold text-brand-900">{title}</h2>}
          {subtitle && <p className="mt-0.5 text-xs text-slate-500">{subtitle}</p>}
        </div>
        {actions}
      </header>
    )}
    {children}
  </section>
)

export const PageTitle = ({ children, subtitle, actions }: { children: ReactNode; subtitle?: ReactNode; actions?: ReactNode }) => (
  <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
    <div>
      <h1 className="text-2xl font-semibold tracking-tight text-brand-900">{children}</h1>
      {subtitle && <p className="mt-1 text-sm text-slate-500">{subtitle}</p>}
    </div>
    {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
  </div>
)

const STAT_TONES = {
  navy: 'bg-brand-50 text-brand-700',
  gold: 'bg-gold-100 text-gold-700',
  green: 'bg-emerald-50 text-emerald-600',
  red: 'bg-roof-50 text-roof-600',
  blue: 'bg-sky-50 text-sky-600',
} as const

/** Headline number with an icon: used on the dashboard and the performance page. */
export function StatCard({ label, value, hint, icon, tone = 'navy', testId, to }: { label: string; value: ReactNode; hint?: ReactNode; icon?: ReactNode; tone?: keyof typeof STAT_TONES; testId?: string; to?: ReactNode }) {
  return (
    <div className="rounded-2xl border border-slate-200/80 bg-white p-4 shadow-card">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-sm text-slate-500">{label}</div>
          <div className="tabular mt-1.5 text-3xl font-semibold tracking-tight text-brand-900" data-testid={testId}>{value}</div>
        </div>
        {icon && <span className={cx('grid h-10 w-10 shrink-0 place-items-center rounded-xl', STAT_TONES[tone])} aria-hidden="true">{icon}</span>}
      </div>
      {hint && <div className="mt-2 text-xs text-slate-500">{hint}</div>}
      {to}
    </div>
  )
}

export function EmptyState({ icon, title, hint, action }: { icon?: ReactNode; title: string; hint?: string; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center px-6 py-12 text-center">
      {icon && <span className="mb-3 grid h-12 w-12 place-items-center rounded-2xl bg-brand-50 text-brand-600" aria-hidden="true">{icon}</span>}
      <p className="text-sm font-medium text-slate-800">{title}</p>
      {hint && <p className="mt-1 max-w-sm text-sm text-slate-500">{hint}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}

export const Skeleton = ({ className }: { className?: string }) => (
  <div className={cx('relative overflow-hidden rounded-lg bg-slate-200/70', className)} aria-hidden="true">
    <div className="absolute inset-0 -translate-x-full animate-shimmer bg-gradient-to-r from-transparent via-white/60 to-transparent" />
  </div>
)

export function Progress({ value, tone = 'brand' }: { value: number; tone?: 'brand' | 'green' | 'gold' }) {
  const bar = { brand: 'bg-brand-600', green: 'bg-emerald-500', gold: 'bg-gold-500' }[tone]
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-100" role="presentation">
      <div className={cx('h-full rounded-full transition-all', bar)} style={{ width: `${Math.max(0, Math.min(100, value))}%` }} />
    </div>
  )
}

/** Pill-style tabs for a handful of mutually exclusive options (for example the period on the performance page). */
export function Segmented<T extends string>({ options, value, onChange, label }: { options: { value: T; label: string }[]; value: T; onChange: (v: T) => void; label: string }) {
  return (
    <div role="group" aria-label={label} className="inline-flex flex-wrap rounded-xl border border-slate-200 bg-white p-1 shadow-sm">
      {options.map((o) => (
        <button key={o.value} type="button" aria-pressed={o.value === value} onClick={() => onChange(o.value)}
          className={cx('rounded-lg px-3.5 py-1.5 text-sm font-medium transition focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500',
            o.value === value ? 'bg-brand-700 text-white shadow-sm' : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900')}>
          {o.label}
        </button>
      ))}
    </div>
  )
}

/* ---------- identity ---------- */

const AVATAR_TONES = ['bg-brand-100 text-brand-700', 'bg-gold-100 text-gold-700', 'bg-emerald-100 text-emerald-700', 'bg-sky-100 text-sky-700', 'bg-roof-100 text-roof-700', 'bg-violet-100 text-violet-700']
export const initials = (name?: string | null) => (name ?? '?').split(/\s+/).filter(Boolean).slice(0, 2).map((p) => p[0]!.toUpperCase()).join('') || '?'

export function Avatar({ name, size = 'md' }: { name?: string | null; size?: 'sm' | 'md' | 'lg' }) {
  const hash = [...(name ?? '')].reduce((a, c) => (a * 31 + c.charCodeAt(0)) >>> 0, 7)
  const dim = { sm: 'h-7 w-7 text-[11px]', md: 'h-9 w-9 text-xs', lg: 'h-11 w-11 text-sm' }[size]
  return <span aria-hidden="true" className={cx('grid shrink-0 place-items-center rounded-full font-semibold', dim, AVATAR_TONES[hash % AVATAR_TONES.length])}>{initials(name)}</span>
}

/** The AHAM logo in a white tile (the supplied logo has a white background) next to the product name. */
export function BrandMark({ dark = false, compact = false }: { dark?: boolean; compact?: boolean }) {
  return (
    <div className="flex items-center gap-3">
      <span className="grid h-11 w-11 shrink-0 place-items-center overflow-hidden rounded-xl bg-white shadow-sm ring-1 ring-black/5">
        <img src="/aham-logo.jpg" alt="AHAM Housing Finance" className="h-full w-full object-cover" />
      </span>
      {!compact && (
        <div className="leading-tight">
          <div className={cx('text-base font-semibold tracking-tight', dark ? 'text-white' : 'text-brand-900')}>FieldSync</div>
          <div className={cx('text-[11px] font-medium uppercase tracking-wider', dark ? 'text-gold-400' : 'text-slate-500')}>Field operations</div>
        </div>
      )}
    </div>
  )
}

/* ---------- status ---------- */

const tones: Record<string, { pill: string; dot: string }> = {
  active: { pill: 'bg-emerald-50 text-emerald-700 ring-emerald-600/20', dot: 'bg-emerald-500' },
  accepted: { pill: 'bg-emerald-50 text-emerald-700 ring-emerald-600/20', dot: 'bg-emerald-500' },
  approved: { pill: 'bg-emerald-50 text-emerald-700 ring-emerald-600/20', dot: 'bg-emerald-500' },
  pending: { pill: 'bg-amber-50 text-amber-800 ring-amber-600/25', dot: 'bg-amber-500' },
  reopened: { pill: 'bg-amber-50 text-amber-800 ring-amber-600/25', dot: 'bg-amber-500' },
  rejected: { pill: 'bg-roof-50 text-roof-700 ring-roof-500/20', dot: 'bg-roof-500' },
  inactive: { pill: 'bg-slate-100 text-slate-600 ring-slate-500/20', dot: 'bg-slate-400' },
}
/** Wording for statuses: a rejected report is "Needs correction" because the agent can fix and resubmit it. */
export const STATUS_LABELS: Record<string, string> = { rejected: 'Needs correction', pending: 'Pending review', approved: 'Approved', reopened: 'Reopened' }
export const statusLabel = (v: string) => STATUS_LABELS[v] ?? v
export const Badge = ({ value }: { value: string }) => {
  const t = tones[value] ?? { pill: 'bg-slate-100 text-slate-700 ring-slate-500/20', dot: 'bg-slate-400' }
  return (
    <span className={cx('inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset', t.pill)}>
      <span className={cx('h-1.5 w-1.5 rounded-full', t.dot)} aria-hidden="true" />
      {statusLabel(value)}
    </span>
  )
}

/* ---------- tables ---------- */

/** Flat table: put it inside `<Card flush>` for the rounded border. */
export const Table = ({ head, children }: { head: string[]; children: ReactNode }) => (
  <div className="overflow-x-auto">
    <table className="w-full text-left text-sm">
      <thead className="bg-slate-50/80 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
        <tr>{head.map((h) => <th key={h} scope="col" className="whitespace-nowrap border-y border-slate-200 px-4 py-3">{h}</th>)}</tr>
      </thead>
      <tbody className="divide-y divide-slate-100 [&>tr]:transition-colors [&>tr:hover]:bg-brand-50/40">{children}</tbody>
    </table>
  </div>
)
export const Td = ({ children, className }: { children?: ReactNode; className?: string }) => <td className={cx('px-4 py-3 align-top text-slate-700', className)}>{children}</td>

export function Pager({ page, pageSize, total, onChange }: { page: number; pageSize: number; total: number; onChange: (p: number) => void }) {
  const pages = Math.max(1, Math.ceil(total / pageSize))
  return (
    <div className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-200 px-4 py-3 text-sm text-slate-600">
      <span>{total} total</span>
      <div className="flex items-center gap-2">
        <Button variant="secondary" small disabled={page <= 1} onClick={() => onChange(page - 1)}>Previous</Button>
        <span className="tabular">Page {page} of {pages}</span>
        <Button variant="secondary" small disabled={page >= pages} onClick={() => onChange(page + 1)}>Next</Button>
      </div>
    </div>
  )
}

/* ---------- dialogs and states ---------- */

export function Dialog({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null)
  const closeRef = useRef(onClose)
  closeRef.current = onClose // the latest handler, without re-running the effect below on every render
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && closeRef.current()
    document.addEventListener('keydown', onKey)
    // focus the first field once when the dialog opens (re-focusing on every render would steal the cursor while typing)
    ref.current?.querySelector<HTMLElement>('input,select,textarea,button:not([data-dialog-close])')?.focus()
    return () => document.removeEventListener('keydown', onKey)
  }, [])
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-brand-950/50 p-4 backdrop-blur-[2px]" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div ref={ref} role="dialog" aria-modal="true" aria-label={title} className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-2xl bg-white p-6 shadow-pop">
        <div className="mb-4 flex items-start justify-between gap-4">
          <h2 className="text-lg font-semibold text-brand-900">{title}</h2>
          <button type="button" data-dialog-close aria-label="Close dialog" onClick={onClose} className="-mr-1 -mt-1 rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500">
            <X size={18} aria-hidden="true" />
          </button>
        </div>
        {children}
      </div>
    </div>
  )
}

export function Confirm({ title, message, confirmLabel, onConfirm, onCancel, busy }: { title: string; message: string; confirmLabel: string; onConfirm: () => void; onCancel: () => void; busy?: boolean }) {
  return (
    <Dialog title={title} onClose={onCancel}>
      <p className="mb-5 text-sm text-slate-600">{message}</p>
      <div className="flex justify-end gap-2">
        <Button variant="secondary" onClick={onCancel}>Cancel</Button>
        <Button variant="danger" disabled={busy} onClick={onConfirm}>{confirmLabel}</Button>
      </div>
    </Dialog>
  )
}

export const ErrorBox = ({ error }: { error: string | null }) => error ? <p role="alert" className="mb-4 rounded-lg border border-roof-200 bg-roof-50 px-3 py-2 text-sm text-roof-700">{error}</p> : null
export const Loading = () => (
  <p className="flex items-center gap-2 p-6 text-sm text-slate-500" role="status">
    <Loader2 size={16} className="animate-spin" aria-hidden="true" />Loading…
  </p>
)
