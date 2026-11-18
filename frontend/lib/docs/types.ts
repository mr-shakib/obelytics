// Types for the public /docs page and its admin panel (backend: app/modules/live_docs).

export type DocsGroup = "pitch" | "product" | "technical" | "operations"
export type SectionKind =
  | "markdown"
  | "demo"
  | "traction"
  | "features"
  | "diagram"
  | "api"
  | "analytics"
  | "team"
  | "contributors"
  | "changelog"

export type VisibilityState = "live" | "disabled" | "not_started" | "ended"

export type Visibility = {
  state: VisibilityState
  is_visible: boolean
  starts_at: string | null
  ends_at: string | null
  message: string
}

export type FeatureStatus = "live" | "beta" | "upcoming" | "planned"

export type FeatureItem = {
  name: string
  area: string
  status: FeatureStatus
  description: string
  signal: string | null
  ai_feature: string | null
}

export type ChangelogItem = { version: string; date: string; title: string; notes: string }

export type SectionData = {
  mermaid?: string
  video_url?: string
  demo_url?: string
  items?: unknown[]
}

export type DocsSection = {
  key: string
  group: DocsGroup
  kind: SectionKind | string
  title: string
  body: string
  data: SectionData
  version: number
  published_at: string | null
}

export type TeamMember = {
  id: string
  full_name: string
  role: string
  email: string
  position: number
  photo_url: string | null
}

export type PublicDocs = {
  product: string
  team_name: string | null
  visibility: Visibility
  sections: DocsSection[]
  team: TeamMember[]
  generated_at: string
}

export type ScheduleMode = "always" | "window" | "duration"

export type DocsSettings = {
  is_enabled: boolean
  schedule_mode: ScheduleMode
  starts_at: string | null
  ends_at: string | null
  duration_minutes: number | null
  team_name: string | null
  timezone: string
  default_starts_at: string
  default_ends_at: string
  updated_at: string | null
}

export type AdminSection = {
  id: string
  key: string
  group: DocsGroup
  kind: SectionKind | string
  position: number
  is_visible: boolean
  is_builtin: boolean
  draft_title: string
  draft_body: string
  draft_data: SectionData
  published_title: string | null
  published_body: string | null
  published_data: SectionData | null
  published_version: number
  published_at: string | null
  has_changes: boolean
  updated_at: string | null
}

export type AdminDocs = {
  settings: DocsSettings
  visibility: Visibility
  sections: AdminSection[]
  team: TeamMember[]
  public_url: string
}

export type SectionVersion = {
  version: number
  title: string
  body: string
  data: SectionData
  published_at: string
  published_by_user_id: string | null
}

export type UsageRow = { label: string; real: number; demo: number; last_at: string | null }

export type AIFeatureLive = {
  feature: string
  title: string
  provider: "hosted" | "local" | "off"
  model: string | null
  external: boolean
  calls_30d: number
  avg_latency_ms?: number
  last_call_at: string | null
}

export type LiveData = {
  generated_at: string
  system: {
    status: "operational" | "degraded"
    api: boolean
    database: boolean
    redis: boolean
    migration: string | null
    environment: string
    started_at: string
    uptime_seconds: number
  }
  api: {
    endpoints: number
    modules: number
    mcp_tools: { name: string; description: string }[]
  }
  ai: {
    features: AIFeatureLive[]
    calls_30d: number
    avg_latency_ms_30d: number | null
    redactions_30d: number
    last_call_at: string | null
    daily: { date: string; calls: number }[]
  }
  usage: Record<string, UsageRow>
  events: {
    daily: { date: string; events: number }[]
    recent: { action: string; entity_type: string; at: string; demo: boolean }[]
  }
}

export type ApiReference = {
  endpoints: number
  modules: number
  groups: {
    module: string
    endpoints: { method: string; path: string; summary: string; auth: "bearer" | "public" }[]
  }[]
}

export type DocsMode = "public" | "preview"

/** Live usage counters a feature-matrix row can link to (backend: live.SIGNALS). */
export const SIGNALS = [
  "organizations", "users", "programs", "curricula", "courses", "course_outcomes",
  "mapping_sets", "sections", "students", "marks", "result_publications",
  "published_results", "papers", "question_audits", "reviews", "rewrites",
  "outcome_suggestions", "improvement_plans", "market_analyses", "job_postings",
  "evidence_drafts", "copilot_conversations", "mcp_calls", "ai_calls",
] as const

export const AI_FEATURES = ["integrity", "authoring", "improvement", "copilot"] as const

export const GROUP_TITLES: Record<DocsGroup, string> = {
  pitch: "Pitch deck",
  product: "Product",
  technical: "Technical documentation",
  operations: "Operations",
}

export const GROUP_ORDER: DocsGroup[] = ["pitch", "product", "technical", "operations"]
