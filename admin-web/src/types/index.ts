export type PortalKey = 'manage' | 'callcentre' | 'admin'
export type Rag = 'PENDING' | 'NA' | 'RED' | 'AMBER' | 'RNR' | 'GREEN'

export interface Me {
  id: string
  company_id: string
  employee_code: string
  full_name: string
  email: string | null
  role: string
  role_label: string
  portal: string
  permissions: string[]
  designation: string | null
  branch_id: string | null
  cluster_id: string | null
  region_id: string | null
  branch_name: string | null
  cluster_name: string | null
  region_name: string | null
  company_name: string | null
  must_change_password: boolean
}

export interface Page<T> { items: T[]; total: number; page: number; page_size: number }

export interface EntryRow {
  id: string
  entry_code: string
  emp_code: string
  so_user_id: string
  so_name: string | null
  so_employee_code: string | null
  branch_id: string
  branch_name: string | null
  region_name: string | null
  category: string
  category_label: string
  cp_subtype_label: string | null
  call_group: 'lead' | 'dsa_cp' | 'none'
  person_name: string
  phone: string
  submitted_at_device: string
  received_at_server: string
  entry_date: string
  count_date: string
  device_time_suspect: boolean
  selection_status: string | null
  status: string | null
  /** the one status shown for the entry (login outcome, else latest call, else selection) */
  current_status: string
  rag: Rag
  rag_overridden: boolean
  priority: boolean
  priority_reason?: string | null
  handling_branch_id?: string | null
  expired_action?: string | null
  expired_on?: string | null
  so_action: string | null
  so_action_date: string | null
  so_action_until: string | null
  cc_action: string | null
  cc_action_date: string | null
  lead_outcome: string | null
  tcs_id: string | null
  customer_validated: boolean
  sankalp_success: boolean
  photo_count: number
  /** app: made on the phone; import: a bulk upload by HR or the admin */
  source?: 'app' | 'import'
  has_location: boolean
  place_name: string | null
}

export interface Photo {
  photo_id: string
  photo_captured_at_device: string | null
  exif_captured_at: string | null
  latitude: number | null
  longitude: number | null
  accuracy_m: number | null
  location_status: string
  place_name: string | null
  place_status: string
  url: string
  thumb_url: string
}

export interface Attempt {
  id: string
  call_date: string
  slot: string
  outcome: string
  cycle: number
  next_date: string | null
  answers: Record<string, string> | null
  row_status: string | null
  caller: string | null
  at: string
}

export interface BranchAnswerRow {
  id: string
  code: string
  meaning: string
  answer_date: string | null
  responded_on: string
  note: string | null
  by: string | null
  green_channel: string | null
}

export interface Tracker {
  owner: string | null
  action_type: string | null
  caller_id: string | null
  caller: string | null
  followup_date: string | null
  outcome: string | null
  tcs_id: string | null
  reject_reason: string | null
  rag_override: Rag | null
  immediate_callback: boolean
  notes: string | null
  updated_at: string
}

export interface EntryDetail extends EntryRow {
  description: string
  keka_photo_time: string | null
  phone_raw: string
  device_tz_offset_min: number | null
  spoke: string | null
  location: { latitude: number | null; longitude: number | null; accuracy_m: number | null; fix_at_device: string | null; status: string; place_name: string | null; place_status: string }
  original_so_user_id: string
  call_cycle: number
  unanswered_count: number
  callback_date: string | null
  validated_on: string | null
  first_validation: boolean
  login_date: string | null
  login_source: string | null
  category_review: string | null
  photos: Photo[]
  history: { kind: string; at: string; by: string | null; detail: Record<string, unknown> | null }[]
  first_caller: string | null
  converted?: boolean
  on_list_of: { caller_id: string | null; caller: string | null; kind: string; run_date: string }[]
  attempts: Attempt[]
  lead_card: (Record<string, unknown> & { loan_requirement: number | null; lead_id: string | null; handling_branch_id: string | null }) | null
  branch_answers: BranchAnswerRow[]
  tracker: Tracker | null
  same_number: { id: string; entry_code: string; so_name: string; entry_date: string; category: string; status: string | null; rag: Rag }[]
}

export interface Meta {
  categories: { key: string; label: string; call_group: string }[]
  slots: string[]
  outcomes: string[]
  unanswered: string[]
  questions: Record<string, string[]>
  branch_codes: { code: string; meaning: string; date_label: string | null }[]
  statuses: string[]
  lead_outcomes: string[]
  rags: Rag[]
  tracker: { owners: string[]; outcomes: string[]; action_types?: string[]; reject_reasons?: string[] }
  /** Current windows and limits (section 14), so screen texts follow the settings. */
  limits: Limits
}

export interface Limits {
  repeat_window_days: number
  max_unanswered_lead: number
  tries_per_day_lead: number
  tries_per_day_dsa: number
  max_slots_per_day: number
  first_attempt_target_days: number
  action_window_days: number
  correct_number_window_days: number
  amber_correction_window_days: number
  branch_date_threshold_days: number
  daily_entry_target: number
  daily_lead_target: number
  green_channel_construction_limit: number
  green_channel_purchase_limit: number
}

export interface Branch { id: string; region_id: string | null; cluster_id: string | null; name: string; code: string; status: string; address: string | null; latitude: number | null; longitude: number | null }
export interface Region { id: string; name: string; code: string; status: string }
export interface Cluster { id: string; region_id: string; name: string; code: string; status: string }

export interface Employee {
  id: string
  employee_code: string
  full_name: string
  email: string | null
  phone: string | null
  role: string
  designation: string | null
  branch_id: string | null
  cluster_id: string | null
  region_id: string | null
  spoke: string | null
  joining_date: string | null
  exit_date: string | null
  must_change_password: boolean
  status: string
}

export interface RoleDef { key: string; label: string; portal: string; level: number; scope: string; placement: string | null; permissions: string[] }

export interface CallRow extends EntryRow {
  allocation_id: string
  kind: 'priority' | 'retry' | 'followup' | 'fresh'
  run_date: string
  caller_id: string | null
  caller: string | null
  tries_today: number
  unanswered_count: number
  first_try_overdue?: boolean
}
