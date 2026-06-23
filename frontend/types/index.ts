// ─── Auth & Identity ─────────────────────────────────────────────────────────

export interface UserProfile {
  id: string
  email: string
  first_name: string
  last_name: string
  full_name?: string
  employee_id?: string
  faculty_type: string
  title?: string
  designation?: string
  department: { id: string; name: string } | null
  status?: string
}

export interface PermissionManifest {
  permissions: string[]
  scope: {
    programs: { id: string; name: string; acronym: string }[]
    is_global: boolean
  }
  offering_ids: string[]
}

export interface MeResponse extends UserProfile {
  permissions: string[]
  scope: {
    programs: { id: string; name: string; acronym: string }[]
    is_global: boolean
  }
  offering_ids: string[]
}

// ─── Pagination ───────────────────────────────────────────────────────────────

export interface PagedResponse<T> {
  items: T[]
  total: number
  page: number
  size: number
}

// ─── API Errors ───────────────────────────────────────────────────────────────

export interface ApiError {
  code: string
  message: string
  details?: Record<string, string[]>
}

// ─── Entity Status Values ─────────────────────────────────────────────────────

export type COStatus = "DRAFT" | "SUBMITTED" | "UNDER_REVIEW" | "APPROVED" | "PUBLISHED" | "LOCKED"
export type ResultStatus = "DRAFT" | "SUBMITTED" | "ML_APPROVED" | "PC_APPROVED" | "PUBLISHED"
export type AttainmentStatus = "INITIATED" | "CALCULATED" | "PUBLISHED"
export type ReportRunStatus = "PENDING" | "RUNNING" | "COMPLETED" | "FAILED"
export type UserStatus = "ACTIVE" | "INACTIVE"
export type CurriculumStatus = "DRAFT" | "ACTIVE" | "ARCHIVED"
export type AccreditationStatus = "PLANNING" | "IN_PROGRESS" | "SUBMITTED" | "COMPLETED"
export type ApprovalType = "CO_REVIEW" | "RESULT_PUBLICATION"

// ─── Approval Inbox ───────────────────────────────────────────────────────────

export interface ApprovalItem {
  id: string
  type: ApprovalType
  entity_id: string
  entity_label: string
  submitted_by: string
  submitted_at: string
  priority: "HIGH" | "MEDIUM" | "LOW"
  context: string
}

// ─── Notification ─────────────────────────────────────────────────────────────

export interface Notification {
  id: string
  type: string
  title: string
  body: string
  is_read: boolean
  created_at: string
  action_url?: string
}
