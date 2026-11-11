/**
 * Preview of the status a connected call will produce (section 8), so the caller sees it before saving.
 * The server classifies again on save and its answer is the one that counts.
 */
export type Answers = Record<string, string | undefined>

export function leadLogic(a: Answers): string {
  const need = a.loan_need
  if (!need) return 'Amber – answers missing'
  if (need === 'Not looking for a loan') return 'Red'
  if (need === 'LAP' || need === 'BT + LAP') return 'Not counted – LAP'
  if (a.documents === 'File already logged with Aham') return 'Already in process'
  if (a.relationship === 'Yes – the same officer') return 'Amber – knows SO'
  if ((a.name_check ?? '').startsWith('Different person')) return 'Validated – different person'
  if (a.visit === 'No') return 'Validated – visit not confirmed'
  return 'Validated'
}

export function dsaLogic(a: Answers): string {
  if (a.needs_home_loan === 'Yes') {
    const st = leadLogic(a)
    return st.startsWith('Validated') ? 'Validated – converted from DSA/CP' : st
  }
  return ({ Green: 'DSA/CP – Green', NA: 'DSA/CP – NA', Amber: 'DSA/CP – Amber', Red: 'DSA/CP – Red' } as Record<string, string>)[a.dsa_rag ?? ''] ?? 'DSA/CP – no RAG'
}

export const previewStatus = (group: string, a: Answers) => (group === 'dsa_cp' ? dsaLogic(a) : leadLogic(a))

/** The lead card opens once Loan need shows a loan type (7.4). */
export const hasLoanType = (a?: Answers | null) => !!a?.loan_need && a.loan_need !== 'Not looking for a loan'

/** The slot of the current hour (09-10 ... 06-07), or the first slot outside calling hours. */
export function currentSlot(slots: string[], now = new Date()): string {
  const h = now.getHours()
  const fmt = (n: number) => String(((n + 11) % 12) + 1).padStart(2, '0')
  const s = `${fmt(h)}-${fmt(h + 1)}`
  return slots.includes(s) ? s : slots[0] ?? ''
}

// 7.2 as the Takeoff call sheet asks them: these only once the loan need is a loan (not LAP, BT + LAP or no loan),
// and own contribution only for a purchase or construction; the server keeps the same rule
const LOAN_QUESTIONS = ['timeline', 'income', 'documents', 'next_step', 'purpose']
const OWN_CONTRIBUTION_NEEDS = ['Home purchase', 'Self-construction', 'Plot + construction']
export function questionApplies(key: string, loanNeed?: string): boolean {
  const loan = !!loanNeed && !['LAP', 'BT + LAP', 'Not looking for a loan'].includes(loanNeed)
  if (key === 'own_contribution') return loan && OWN_CONTRIBUTION_NEEDS.includes(loanNeed!)
  return LOAN_QUESTIONS.includes(key) ? loan : true
}
