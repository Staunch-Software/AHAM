export interface Me { id: string; company_id: string; full_name: string; email: string; role: string; branch_ids: string[] }
export interface Page<T> { items: T[]; total: number; page: number; page_size: number }
export interface Branch { id: string; organization_id: string | null; name: string; code: string; address: string | null; latitude: number | null; longitude: number | null; status: string }
export interface Organization { id: string; name: string; code: string; status: string }
export interface Company { id: string; name: string; code: string; contact_email: string | null; contact_phone: string | null; address: string | null; status: string }
export interface Employee { id: string; employee_code: string; full_name: string; email: string; phone: string | null; role: string; status: string; branch_id: string | null }
export interface ReviewFlag { path: string; note: string }
export interface SubmissionRow {
  id: string; agent_name: string; employee_code: string; branch_id: string | null; branch_name: string | null; form_title: string; form_version: number
  submitted_at_device: string; received_at_server: string; accepted_at_server: string
  status: string; review_status: string; photo_count: number; has_location: boolean
  reference: string; revision: number; is_latest: boolean; root_id: string; person_types: string[]
  review_reason_code: string | null; review_comment: string | null; review_flags: ReviewFlag[]; reviewed_at: string | null
}
export interface PhotoMeta {
  photo_id: string; group_key: string | null; field_key: string | null; original_filename: string | null
  mime_type: string; size_bytes: number | null; sha256: string | null
  photo_captured_at_device: string | null; exif_captured_at: string | null
  photo_capture_latitude: number | null; photo_capture_longitude: number | null; photo_capture_accuracy_m: number | null
  photo_location_fix_at_device: string | null; photo_location_status: string; location_source: string | null
  photo_place_name?: string | null; photo_place_status?: string
  upload_completed_at_server: string | null; url: string; thumb_url: string
}
export interface FormField { key: string; label: string; type: string; options?: { value: string; label: string }[] }
export interface FormSection { id: string; title?: string; repeatable?: boolean; fields: FormField[] }
export interface SubmissionDetail extends SubmissionRow {
  answers: Record<string, any>; schema: { title: string; sections: FormSection[] }; client_submission_id: string
  device_tz_offset_min: number | null
  submission_location: { latitude: number | null; longitude: number | null; accuracy_m: number | null; fix_at_device: string | null; status: string; place_name?: string | null; place_status?: string }
  photos: PhotoMeta[]; events: { type: string; detail: string | null; at: string }[]
  option_labels: Record<string, string>
  revisions: { id: string; revision: number; accepted_at_server: string; review_status: string; is_latest: boolean }[]
  reviews: ReviewEntry[]
}
export interface ReviewEntry {
  id: string; submission_id: string; revision: number; decision: 'approved' | 'rejected' | 'reopened'
  reason_code: string | null; reason_label: string | null; comment: string | null; flags: ReviewFlag[]; reviewer: string; created_at: string
}
export interface ReviewReason { id: string; code: string; label: string; default_message: string | null; requires_comment: boolean; active: boolean; sort_order: number }
export interface PersonTypeItem { id: string; label: string; active: boolean; sort_order: number; times_used: number }
export interface PersonTypesPayload { items: PersonTypeItem[]; settings: { required: boolean; allow_other: boolean } }
export interface PeriodMeta { key: string; from: string; to: string; timezone: string; targets_apply: boolean }
export interface Metrics {
  reports: number; active_agents: number; pending: number; approved: number; needs_correction: number
  target: number | null; achievement: number | null; reviewed_decisions: number; rejection_rate: number | null
  previous_reports: number; trend_pct: number | null
}
export interface BranchMetrics extends Metrics { branch_id: string; name: string; code: string; assigned_agents: number }
export interface AgentMetrics extends Metrics { agent_id: string; name: string; employee_code: string; status: string; last_report_at: string | null }
export interface AnalyticsOverview {
  period: PeriodMeta
  totals: { reports: number; pending: number; approved: number; needs_correction: number; assigned_agents: number; active_agents: number
    reviewed_decisions: number; rejection_rate: number | null; previous_reports: number; trend_pct: number | null }
  branches: BranchMetrics[]; person_types: { label: string; meetings: number }[]
}
export interface MapReport {
  id: string; reference: string; revision: number; agent_name: string; employee_code: string; branch_id: string | null; branch_name: string | null
  form_title: string; review_status: string; latitude: number; longitude: number; accuracy_m: number | null; location_status: string
  place_name: string | null; place_status: string; submitted_at_device: string; accepted_at_server: string; meeting_dates: string[]; person_types: string[]
}
export interface MapPhoto {
  id: string; submission_id: string; reference: string; agent_name: string; branch_name: string | null; review_status: string
  latitude: number; longitude: number; accuracy_m: number | null; place_name: string | null; place_status: string; captured_at_device: string | null
}
export interface MapBranch { id: string; name: string; code: string; status: string; latitude: number; longitude: number }
export interface MapData {
  reports: MapReport[]; photos: MapPhoto[]; branches: MapBranch[]
  counts: { reports: number; with_gps: number; without_gps: number; shown: number; truncated: boolean }; note: string
}
export interface Dashboard {
  total_agents: number; active_branches: number; submissions_today: number; pending_review: number; needs_correction: number
  recent: SubmissionRow[]; trend: { date: string; count: number }[]
}
