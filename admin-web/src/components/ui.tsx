import { Check, ChevronDown, Download, Loader2, Search, X } from 'lucide-react'
import { ButtonHTMLAttributes, Children, forwardRef, InputHTMLAttributes, isValidElement, ReactNode, RefObject, SelectHTMLAttributes, TextareaHTMLAttributes, useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { Link } from 'react-router-dom'
import { errorMessage } from '../services/api'
import { type Cells, saveCsv, saveXlsx, tableCells } from '../services/exporting'

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

function nodeToText(node: ReactNode): string {
  if (node === null || node === undefined || typeof node === 'boolean') return ''
  if (typeof node === 'string' || typeof node === 'number') return String(node)
  if (Array.isArray(node)) return node.map(nodeToText).join(' ')
  if (isValidElement(node) && (node.props as any)?.children) {
    return nodeToText((node.props as any).children)
  }
  return ''
}

interface ParsedOption {
  kind: 'option'
  value: string
  label: ReactNode
  text: string
  disabled?: boolean
}

interface ParsedGroup {
  kind: 'group'
  label: ReactNode
}

type ParsedItem = ParsedOption | ParsedGroup

function parseSelectChildren(children: ReactNode): ParsedItem[] {
  const items: ParsedItem[] = []
  Children.forEach(children, (child) => {
    if (!isValidElement(child)) return
    const props = child.props as any
    if (child.type === 'optgroup' || (props && props.label && props.children)) {
      items.push({ kind: 'group', label: props.label })
      Children.forEach(props.children, (sub) => {
        if (!isValidElement(sub)) return
        const subProps = sub.props as any
        const val = String(subProps.value ?? '')
        const lbl = subProps.children ?? subProps.label ?? val
        items.push({
          kind: 'option',
          value: val,
          label: lbl,
          text: (nodeToText(lbl) + ' ' + val).trim().toLowerCase(),
          disabled: subProps.disabled,
        })
      })
      return
    }

    const val = String(props.value ?? '')
    const lbl = props.children ?? props.label ?? val
    items.push({
      kind: 'option',
      value: val,
      label: lbl,
      text: (nodeToText(lbl) + ' ' + val).trim().toLowerCase(),
      disabled: props.disabled,
    })
  })
  return items
}

export const Select = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement>>((p, ref) => {
  const { className, value, defaultValue, onChange, disabled, children, autoFocus, ...rest } = p
  const nativeRef = useRef<HTMLSelectElement | null>(null)
  const triggerRef = useRef<HTMLButtonElement | null>(null)
  const menuRef = useRef<HTMLDivElement | null>(null)
  const searchInputRef = useRef<HTMLInputElement | null>(null)

  const [open, setOpen] = useState(false)
  const [internalVal, setInternalVal] = useState<string>(String(value ?? defaultValue ?? ''))
  const [search, setSearch] = useState('')
  const [coords, setCoords] = useState<{ top?: number; bottom?: number; left: number; width: number } | null>(null)

  useEffect(() => {
    if (value !== undefined) {
      setInternalVal(String(value))
    }
  }, [value])

  const handleRef = (el: HTMLSelectElement | null) => {
    nativeRef.current = el
    if (typeof ref === 'function') ref(el)
    else if (ref) (ref as any).current = el
  }

  const items = parseSelectChildren(children)
  const allOptions = items.filter((it): it is ParsedOption => it.kind === 'option')

  const currentVal = value !== undefined ? String(value) : internalVal
  const selected = allOptions.find((o) => o.value === currentVal)
  const displayLabel = selected?.label ?? (allOptions.find((o) => o.value === '')?.label ?? allOptions[0]?.label ?? currentVal)

  useEffect(() => {
    if (!open) return
    const update = () => {
      if (!triggerRef.current) return
      const rect = triggerRef.current.getBoundingClientRect()
      const spaceBelow = window.innerHeight - rect.bottom
      const spaceAbove = rect.top
      const menuMaxHeight = 260
      const placeAbove = spaceBelow < menuMaxHeight && spaceAbove > spaceBelow
      const margin = 4

      // Match trigger button width or at least 180px for readability
      const width = Math.max(rect.width, 180)

      // Align left edges by default; if it would overflow the right viewport edge, align right edges
      let left = rect.left
      if (left + width > window.innerWidth - margin) {
        left = rect.right - width
      }
      if (left < margin) left = margin

      if (placeAbove) {
        setCoords({
          bottom: window.innerHeight - rect.top + margin,
          left,
          width,
        })
      } else {
        setCoords({
          top: rect.bottom + margin,
          left,
          width,
        })
      }
    }

    update()

    // Requirement: close dropdown immediately on scroll of page or container
    const handleScroll = (e: Event) => {
      if (menuRef.current && (menuRef.current === e.target || menuRef.current.contains(e.target as Node))) {
        return
      }
      setOpen(false)
      setSearch('')
    }

    window.addEventListener('resize', handleScroll)
    window.addEventListener('scroll', handleScroll, true)
    return () => {
      window.removeEventListener('resize', handleScroll)
      window.removeEventListener('scroll', handleScroll, true)
    }
  }, [open])

  useEffect(() => {
    if (open && allOptions.length > 10 && searchInputRef.current) {
      searchInputRef.current.focus()
    }
  }, [open, allOptions.length])

  useEffect(() => {
    if (!open) return
    const onMouseDown = (e: MouseEvent | TouchEvent) => {
      const target = e.target as Node
      if (triggerRef.current?.contains(target) || menuRef.current?.contains(target)) return
      setOpen(false)
      setSearch('')
    }
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setOpen(false)
        setSearch('')
      }
    }
    document.addEventListener('mousedown', onMouseDown)
    document.addEventListener('touchstart', onMouseDown)
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('mousedown', onMouseDown)
      document.removeEventListener('touchstart', onMouseDown)
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [open])

  const handleSelect = (val: string) => {
    setInternalVal(val)
    if (nativeRef.current) {
      nativeRef.current.value = val
      const evt = new Event('change', { bubbles: true })
      nativeRef.current.dispatchEvent(evt)
    }
    if (onChange) {
      const synthetic = {
        target: { value: val, name: p.name },
        currentTarget: { value: val, name: p.name },
        preventDefault: () => {},
        stopPropagation: () => {},
      } as unknown as React.ChangeEvent<HTMLSelectElement>
      onChange(synthetic)
    }
    setOpen(false)
    setSearch('')
  }

  const query = search.trim().toLowerCase()
  const filteredItems = query
    ? items.filter((it) => it.kind === 'group' || it.text.includes(query))
    : items

  const isSmall = className?.includes('text-xs') || className?.includes('py-1')
  const isAutoWidth = className?.includes('w-auto') || className?.includes('w-max')
  const widthMatch = className?.match(/\b(w-(?:auto|full|max|screen|\d+|\[[^\]]+\]))\b/)
  const widthClass = widthMatch ? widthMatch[1] : (isAutoWidth ? 'w-auto' : 'w-full')
  const isShrink = className?.includes('shrink-0')
  const buttonClassName = className
    ?.replace(/\b(w-(?:auto|full|max|screen|\d+|\[[^\]]+\]))\b/g, '')
    .replace(/\bshrink-0\b/g, '')
    .replace(/\bpr-8\b/g, '')
    .trim()

  return (
    <div className={cx('relative', isAutoWidth ? 'inline-block' : 'block', widthClass, isShrink && 'shrink-0')}>
      <select
        ref={handleRef}
        {...rest}
        value={currentVal}
        disabled={disabled}
        onChange={(e) => {
          setInternalVal(e.target.value)
          onChange?.(e)
        }}
        className="sr-only"
        tabIndex={-1}
        aria-hidden="true"
      >
        {children}
      </select>

      <button
        ref={triggerRef}
        type="button"
        disabled={disabled}
        autoFocus={autoFocus}
        aria-label={p['aria-label']}
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => !disabled && setOpen((o) => !o)}
        className={cx(
          'group relative flex items-center justify-between gap-2 rounded-lg border border-slate-300 bg-white text-left font-normal shadow-sm transition',
          'hover:border-slate-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20 active:bg-slate-50',
          disabled ? 'cursor-not-allowed border-slate-200 bg-slate-50 text-slate-400' : 'cursor-pointer text-slate-800',
          isSmall ? 'px-2.5 py-1 text-xs' : 'px-3 py-2 text-sm',
          'w-full',
          buttonClassName
        )}
      >
        <span className="truncate">{displayLabel}</span>
        <ChevronDown
          size={isSmall ? 13 : 15}
          className={cx(
            'shrink-0 text-slate-400 transition-transform duration-200',
            open && 'rotate-180 text-brand-700'
          )}
        />
      </button>

      {open && coords && createPortal(
        <div
          ref={menuRef}
          style={{
            position: 'fixed',
            top: coords.top !== undefined ? `${coords.top}px` : undefined,
            bottom: coords.bottom !== undefined ? `${coords.bottom}px` : undefined,
            left: `${coords.left}px`,
            width: `${coords.width}px`,
            zIndex: 9999,
          }}
          className="rounded-xl border border-slate-200 bg-white py-1 shadow-xl ring-1 ring-black/5"
          role="listbox"
        >
          {allOptions.length > 10 && (
            <div className="border-b border-slate-100 p-1.5">
              <div className="relative flex items-center">
                <Search size={13} className="pointer-events-none absolute left-2.5 text-slate-400" />
                <input
                  ref={searchInputRef}
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Filter..."
                  className="w-full rounded-md border border-slate-200 bg-slate-50 py-1 pl-7 pr-2 text-xs text-slate-800 placeholder:text-slate-400 focus:border-brand-500 focus:bg-white focus:outline-none focus:ring-1 focus:ring-brand-500"
                />
              </div>
            </div>
          )}

          <div className="max-h-56 overflow-y-auto overscroll-contain custom-scrollbar px-1 py-1 space-y-0.5">
            {filteredItems.length === 0 ? (
              <div className="px-3 py-2 text-center text-xs text-slate-400">No matches</div>
            ) : (
              filteredItems.map((item, idx) => {
                if (item.kind === 'group') {
                  return (
                    <div
                      key={`grp-${idx}`}
                      className="px-2.5 pt-2 pb-1 text-[10px] font-semibold uppercase tracking-wider text-slate-400"
                    >
                      {item.label}
                    </div>
                  )
                }

                const isSelected = item.value === currentVal
                return (
                  <button
                    key={`${item.value}-${idx}`}
                    type="button"
                    role="option"
                    aria-selected={isSelected}
                    disabled={item.disabled}
                    onClick={() => handleSelect(item.value)}
                    className={cx(
                      'flex w-full items-center justify-between rounded-lg px-2.5 py-1.5 text-left text-xs sm:text-sm transition-colors',
                      isSelected
                        ? 'bg-brand-50 font-medium text-brand-900'
                        : 'text-slate-700 hover:bg-slate-100 hover:text-slate-900',
                      item.disabled && 'cursor-not-allowed opacity-40 hover:bg-transparent'
                    )}
                  >
                    <span className="truncate pr-2">{item.label}</span>
                    {isSelected && <Check size={14} className="shrink-0 text-brand-700" />}
                  </button>
                )
              })
            )}
          </div>
        </div>,
        document.body
      )}
    </div>
  )
})

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>((p, ref) => <textarea ref={ref} {...p} className={cx(field, 'resize-y', p.className)} />)

export function Field({ label, error, hint, children }: { label: string; error?: string; hint?: ReactNode; children: ReactNode }) {
  return (
    <label className="block text-sm">
      <span className="mb-1.5 block text-xs font-medium text-slate-600">{label}</span>
      {children}
      {error && <span role="alert" className="mt-1 block text-xs text-roof-600">{error}</span>}
      {!error && hint && <span className="mt-1 block text-xs text-slate-500">{hint}</span>}
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

export function Card({
  title,
  subtitle,
  actions,
  children,
  className,
  flush,
  collapsible,
  defaultOpen = true,
  open: controlledOpen,
  onToggle,
}: {
  title?: string
  subtitle?: string
  actions?: ReactNode
  children: ReactNode
  className?: string
  flush?: boolean
  collapsible?: boolean
  defaultOpen?: boolean
  open?: boolean
  onToggle?: (open: boolean) => void
}) {
  const [uncontrolledOpen, setUncontrolledOpen] = useState(defaultOpen)
  const isOpen = controlledOpen !== undefined ? controlledOpen : uncontrolledOpen

  const handleToggle = () => {
    const next = !isOpen
    if (controlledOpen === undefined) setUncontrolledOpen(next)
    onToggle?.(next)
  }

  return (
    <section className={cx('rounded-2xl border border-slate-200/80 bg-white shadow-card transition-all', flush ? 'overflow-hidden' : 'p-4 sm:p-5', className)}>
      {(title || actions || collapsible) && (
        <header
          className={cx(
            'flex flex-wrap items-start justify-between gap-2',
            flush ? 'px-4 sm:px-5 pt-4 sm:pt-5' : '',
            isOpen && children ? 'mb-4' : 'mb-0',
            collapsible && 'cursor-pointer select-none group/hdr'
          )}
          onClick={collapsible ? handleToggle : undefined}
        >
          <div className="flex-1 min-w-0">
            {title && (
              <h2 className={cx('text-sm font-semibold text-brand-900 transition-colors', collapsible && 'group-hover/hdr:text-brand-700')}>
                {title}
              </h2>
            )}
            {subtitle && (!collapsible || isOpen) && <p className="mt-0.5 text-xs text-slate-500">{subtitle}</p>}
          </div>
          <div className="flex items-center gap-2 shrink-0" onClick={(e) => collapsible && e.stopPropagation()}>
            {actions}
            {collapsible && (
              <button
                type="button"
                aria-expanded={isOpen}
                aria-label={isOpen ? `Collapse ${title}` : `Expand ${title}`}
                onClick={handleToggle}
                className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-brand-700 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
              >
                <ChevronDown
                  size={18}
                  className={cx(
                    'transition-transform duration-200 text-slate-400 group-hover/hdr:text-brand-700',
                    isOpen && 'rotate-180 text-brand-700'
                  )}
                />
              </button>
            )}
          </div>
        </header>
      )}
      {(!collapsible || isOpen) && children}
    </section>
  )
}

export const PageTitle = ({
  children,
  subtitle,
  actions,
  className,
}: {
  children: ReactNode
  subtitle?: ReactNode
  actions?: ReactNode
  className?: string
}) => (
  <div className={cx('mb-3 sm:mb-4 flex flex-wrap items-start justify-between gap-2.5 shrink-0', className)}>
    <div className="flex-1 min-w-0">
      <h1 className="text-xl sm:text-2xl font-semibold tracking-tight text-brand-900">{children}</h1>
      {subtitle && <p className="mt-0.5 text-xs sm:text-sm text-slate-500">{subtitle}</p>}
    </div>
    {actions && <div className="flex flex-wrap items-center gap-2 shrink-0">{actions}</div>}
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
export function StatCard({
  label,
  value,
  hint,
  icon,
  tone = 'navy',
  testId,
  to,
  linkTo,
}: {
  label: string
  value: ReactNode
  hint?: ReactNode
  icon?: ReactNode
  tone?: keyof typeof STAT_TONES
  testId?: string
  to?: ReactNode
  linkTo?: string
}) {
  const content = (
    <>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-1.5 text-sm text-slate-500 group-hover:text-brand-700 transition">
            <span>{label}</span>
            {linkTo && <span className="text-xs text-brand-600 opacity-0 group-hover:opacity-100 transition" aria-hidden="true">&rarr;</span>}
          </div>
          <div className="tabular mt-1.5 text-3xl font-semibold tracking-tight text-brand-900 group-hover:text-brand-950 transition" data-testid={testId}>{value}</div>
        </div>
        {icon && <span className={cx('grid h-10 w-10 shrink-0 place-items-center rounded-xl transition group-hover:scale-105', STAT_TONES[tone])} aria-hidden="true">{icon}</span>}
      </div>
      {hint && <div className="mt-2 text-xs text-slate-500">{hint}</div>}
      {to}
    </>
  )

  if (linkTo) {
    return (
      <Link
        to={linkTo}
        className="group block rounded-2xl border border-slate-200/80 bg-white p-4 shadow-card transition duration-150 hover:border-brand-400 hover:shadow-md focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
      >
        {content}
      </Link>
    )
  }

  return (
    <div className="rounded-2xl border border-slate-200/80 bg-white p-4 shadow-card">
      {content}
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
export function BrandMark({ dark = false, compact = false, tagline = 'Field to lead' }: { dark?: boolean; compact?: boolean; tagline?: string }) {
  return (
    <div className="flex items-center gap-3">
      <span className="grid h-11 w-11 shrink-0 place-items-center overflow-hidden rounded-xl bg-white shadow-sm ring-1 ring-black/5">
        <img src="/aham-logo.jpg" alt="AHAM Housing Finance" className="h-full w-full object-cover" />
      </span>
      {!compact && (
        <div className="leading-tight">
          <div className={cx('text-base font-semibold tracking-tight', dark ? 'text-white' : 'text-brand-900')}>AHAM Sankalp</div>
          <div className={cx('text-[11px] font-medium uppercase tracking-wider', dark ? 'text-gold-400' : 'text-slate-500')}>{tagline}</div>
        </div>
      )}
    </div>
  )
}

/* ---------- Sankalp status ---------- */

const RAG_TONES: Record<string, string> = {
  RED: 'bg-roof-50 text-roof-700 ring-roof-500/25',
  AMBER: 'bg-amber-50 text-amber-800 ring-amber-600/30',
  GREEN: 'bg-emerald-50 text-emerald-700 ring-emerald-600/25',
  RNR: 'bg-violet-50 text-violet-700 ring-violet-600/20',
  NA: 'bg-slate-100 text-slate-600 ring-slate-500/20',
  PENDING: 'bg-sky-50 text-sky-700 ring-sky-600/20',
}
const RAG_DOTS: Record<string, string> = { RED: 'bg-roof-500', AMBER: 'bg-amber-500', GREEN: 'bg-emerald-500', RNR: 'bg-violet-500', NA: 'bg-slate-400', PENDING: 'bg-sky-500' }
// the same words as the server's RAG_LABELS (rules.py)
export const RAG_LABEL: Record<string, string> = { RED: 'Red', AMBER: 'Amber', GREEN: 'Green', RNR: 'No answer', NA: 'Not applicable', PENDING: 'Not called yet' }

/** Section 9 RAG. `overridden` marks a manual override by the master owner. */
export function RagBadge({ value, overridden }: { value: string; overridden?: boolean }) {
  return (
    <span title={overridden ? 'Set by the master owner' : undefined} className={cx('inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset', RAG_TONES[value] ?? RAG_TONES.NA)}>
      <span className={cx('h-1.5 w-1.5 rounded-full', RAG_DOTS[value] ?? RAG_DOTS.NA)} aria-hidden="true" />
      {RAG_LABEL[value] ?? value}{overridden && '*'}
    </span>
  )
}

/** An entry's one current status (worked out by the server: login outcome, else the latest call, else the selection). */
export function StatusText({ value }: { value: string | null | undefined }) {
  const text = value ?? '—'
  const tone = text.startsWith('Validated') || text === 'Logged in' ? 'text-emerald-700'
    : text.startsWith('Amber') || text.startsWith('Red') || text === 'Rejected' ? 'text-roof-700'
      : text.startsWith('Waiting') || text.startsWith('Not called') ? 'text-slate-500' : 'text-slate-700'
  return <span className={cx('text-sm', tone)}>{text}</span>
}

/** Label/value rows for detail pages. */
export function KV({ items }: { items: [string, ReactNode][] }) {
  return (
    <dl className="grid gap-x-6 gap-y-3 text-sm sm:grid-cols-2">
      {items.map(([k, v]) => (
        <div key={k} className="min-w-0">
          <dt className="text-xs font-medium text-slate-500">{k}</dt>
          <dd className="mt-0.5 break-words text-slate-800">{v ?? '—'}</dd>
        </div>
      ))}
    </dl>
  )
}

/** A short line telling the user something about the page (not an error). */
export const Note = ({ children, tone = 'brand' }: { children: ReactNode; tone?: 'brand' | 'gold' }) => (
  <p className={cx('mb-4 rounded-xl px-4 py-3 text-sm', tone === 'gold' ? 'border border-gold-300/70 bg-gold-50 text-slate-700' : 'bg-brand-50 text-brand-800')}>{children}</p>
)

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
export const STATUS_LABELS: Record<string, string> = { pending: 'Pending', active: 'Active', inactive: 'Inactive' }
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

/** Flat table: put it inside `<Card flush>` for the rounded border.
 *  `exportName` adds "Export: CSV / Excel". It exports the rows on screen (columns with an empty heading, such as
 *  buttons, are left out), or, for a paged list, `exportAll`: every row, in the order of the non-empty headings. */
export function Table({
  head,
  children,
  exportName,
  exportAll,
  exportHeader,
  className,
  containerClassName,
  maxHeight = 'max-h-[calc(100vh-16.5rem)]',
  stickyFirstColumn = true,
  hideExportBar,
  tableRef: externalRef,
}: {
  head: string[]
  children: ReactNode
  exportName?: string
  exportAll?: () => Promise<Cells[]>
  exportHeader?: string[]
  className?: string
  containerClassName?: string
  maxHeight?: string
  stickyFirstColumn?: boolean
  /** Skip the built-in "Export: CSV / Excel" row above the table — pass `tableRef` and render an `<ExportBar>` elsewhere (e.g. in the enclosing `Card`'s `actions`) instead. */
  hideExportBar?: boolean
  /** Lets a caller that renders its own `<ExportBar>` (with `hideExportBar`) read the same table's rows. */
  tableRef?: RefObject<HTMLTableElement>
}) {
  const internalRef = useRef<HTMLTableElement>(null)
  const ref = externalRef ?? internalRef
  const columns = head.filter((h) => h !== '')
  const rows = async () => (exportAll ? exportAll() : tableCells(ref.current!, head.map((h) => h !== '')))
  return (
    <div className={cx('flex flex-col w-full min-h-0', containerClassName)}>
      {exportName && !hideExportBar && <ExportBar name={exportName} header={exportHeader ?? columns} rows={rows} className="shrink-0" />}
      <div className={cx('overflow-x-auto overflow-y-auto custom-scrollbar min-h-0', maxHeight, className)}>
        <table
          ref={ref}
          className={cx(
            'w-full text-left text-sm border-separate border-spacing-0',
            stickyFirstColumn &&
              '[&_tbody_tr>td:first-child]:sticky [&_tbody_tr>td:first-child]:left-0 [&_tbody_tr>td:first-child]:z-10 [&_tbody_tr>td:first-child]:bg-white [&_tbody_tr:hover>td:first-child]:!bg-brand-50 [&_tbody_tr>td:first-child]:border-r [&_tbody_tr>td:first-child]:border-slate-200 [&_tbody_tr>td:first-child]:shadow-[2px_0_5px_-2px_rgba(0,0,0,0.08)]'
          )}
        >
          <thead className="sticky top-0 z-20 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
            <tr>
              {head.map((h, i) => (
                <th
                  key={`${h}${i}`}
                  scope="col"
                  className={cx(
                    'whitespace-nowrap sticky top-0 border-b border-slate-200 px-4 py-3 bg-slate-50',
                    i === 0 && stickyFirstColumn
                      ? 'left-0 z-30 bg-slate-50 border-r border-slate-200 shadow-[2px_0_5px_-2px_rgba(0,0,0,0.08)]'
                      : 'z-20'
                  )}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 [&>tr]:transition-colors [&>tr:hover]:bg-brand-50 [&_td]:border-b [&_td]:border-slate-100">
            {children}
          </tbody>
        </table>
      </div>
    </div>
  )
}

/** "Export: CSV · Excel" for any list: `rows` gives every row to export (fetching all pages when needed).
 *  `compact` drops the row's own padding, for embedding it in a `Card`'s `actions` instead of above the table. */
export function ExportBar({ name, header, rows, className, compact }: { name: string; header: string[]; rows: () => Promise<Cells[]> | Cells[]; className?: string; compact?: boolean }) {
  const [busy, setBusy] = useState<'csv' | 'xlsx' | null>(null)
  const [error, setError] = useState<string | null>(null)
  const go = async (kind: 'csv' | 'xlsx') => {
    setBusy(kind); setError(null)
    try {
      const data = await rows()
      if (kind === 'csv') saveCsv(name, header, data)
      else await saveXlsx(name, header, data)
    } catch (e) {
      setError(errorMessage(e))
    } finally {
      setBusy(null)
    }
  }
  return (
    <div className={cx('flex flex-wrap items-center justify-end gap-2 text-xs text-slate-500', !compact && 'px-4 py-2', className)}>
      {error && <span role="alert" className="text-roof-600">Export failed: {error}</span>}
      <span>Export:</span>
      <button type="button" disabled={!!busy} onClick={() => go('csv')} className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-2.5 py-1 font-semibold text-brand-700 hover:bg-brand-50 disabled:opacity-50"><Download size={12} aria-hidden="true" />{busy === 'csv' ? 'Preparing…' : 'CSV'}</button>
      <button type="button" disabled={!!busy} onClick={() => go('xlsx')} className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-2.5 py-1 font-semibold text-brand-700 hover:bg-brand-50 disabled:opacity-50"><Download size={12} aria-hidden="true" />{busy === 'xlsx' ? 'Preparing…' : 'Excel'}</button>
    </div>
  )
}
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

export function Dialog({ title, onClose, children, wide }: { title: string; onClose: () => void; children: ReactNode; wide?: boolean }) {
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
      <div ref={ref} role="dialog" aria-modal="true" aria-label={title} className={cx('max-h-[90vh] w-full overflow-y-auto rounded-2xl bg-white p-6 shadow-pop', wide ? 'max-w-2xl' : 'max-w-lg')}>
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
