import { C } from './theme'

/** What the server says about an entry (status, RAG, next action). */
export interface ServerRow {
  id: string; entry_code: string; person_name: string; phone: string; category: string; submitted_at_device: string
  status: string | null; selection_status: string | null; current_status?: string; rag: string; so_action: string | null; so_action_date: string | null; lead_outcome: string | null
}

type CloudIcon = 'cloud-clock-outline' | 'cloud-upload-outline' | 'cloud-check-outline' | 'cloud-alert'
export const STATE_PILL: Record<string, { text: string; color: string; bg: string; icon: CloudIcon }> = {
  queued: { text: 'Waiting to send', color: C.gold700, bg: C.gold100, icon: 'cloud-clock-outline' },
  sync_pending: { text: 'Waiting to send', color: C.gold700, bg: C.gold100, icon: 'cloud-clock-outline' },
  uploading: { text: 'Sending', color: C.navy700, bg: C.navy50, icon: 'cloud-upload-outline' },
  accepted: { text: 'Sent', color: C.green700, bg: C.green50, icon: 'cloud-check-outline' },
  failed: { text: 'Needs attention', color: C.roof700, bg: C.roof50, icon: 'cloud-alert' },
}

/** The entry's one current status, as the server works it out (login outcome, else the latest call, else the
 *  selection); older servers send only the raw fields. */
export const statusText = (r?: ServerRow | null) =>
  !r ? null : r.current_status ?? r.status ?? (r.selection_status === 'Allocate' || !r.selection_status ? 'Waiting for the call centre' : r.selection_status)
