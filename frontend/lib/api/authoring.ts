import { apiFetch, PUBLIC_API_URL } from "@/lib/api/client"

// AI outcome authoring: draft COs, refine a CO statement, suggest CO-PO links.
// Suggestions are advisory — nothing is saved until the teacher accepts it.

export type BloomRef = { id: string; code: string; name: string }

type SuggestionMeta = { suggestion_id: string; model: string; prompt_version: string }

export type DraftedOutcome = {
  statement: string
  bloom_levels: BloomRef[]
  rationale: string
  /** Found by code, not by the model: vague verb, two outcomes in one, repeats a CO… */
  warnings: string[]
}

export type DraftResponse = SuggestionMeta & { outcomes: DraftedOutcome[] }

export type RefineResponse = SuggestionMeta & {
  statement: string
  bloom_levels: BloomRef[]
  changes: string[]
  warnings: string[]
  /** The same checks run on the teacher's own wording. */
  original_warnings: string[]
}

export type SuggestedAttribute = {
  id: string
  code: string
  justification: string
  /** true: the CO already has it; false: applying the link adds it. */
  already_mapped: boolean
}

export type SuggestedLink = {
  index: number
  course_outcome_id: string
  co_code: string
  program_outcome_id: string
  po_code: string
  weight: 1 | 2 | 3
  justification: string
  confidence: number | null
  knowledge_profiles: SuggestedAttribute[]
  complex_problems: SuggestedAttribute[]
  complex_activities: SuggestedAttribute[]
  /** Mapping rules the link breaks — it cannot be applied. */
  issues: string[]
  warnings: string[]
  already_mapped: boolean
  can_apply: boolean
}

export type MappingSuggestResponse = SuggestionMeta & {
  /** The COs this suggestion covers — all of the course's COs unless some were chosen. */
  course_outcome_codes: string[]
  links: SuggestedLink[]
  pos_without_knowledge_profiles: string[]
  existing_not_suggested: { co_code: string; po_code: string }[]
}

export type ApplyItem = { index: number; weight?: 1 | 2 | 3; justification?: string }

export type ApplyResponse = {
  mapping_set_id: string
  applied: number[]
  already_mapped: number[]
  added_knowledge_profiles: number
  added_complex_problems: number
  added_complex_activities: number
}

export type Decision = "ACCEPTED" | "EDITED" | "PARTIAL" | "REJECTED"

export type OutlineOutcome = {
  code: string
  statement: string
  bloom_levels: BloomRef[]
  /** false: the outline gives no level, so the AI chose one. */
  bloom_stated: boolean
  /** Already a CO of this course: importing leaves it unchanged. */
  exists: boolean
  warnings: string[]
}

export type OutlineTopic = { week: number | null; topic: string }

export type OutlinePreview = SuggestionMeta & {
  filename: string
  course_code: string | null
  course_title: string | null
  description: string | null
  objectives: string[]
  outcomes: OutlineOutcome[]
  topics: OutlineTopic[]
  warnings: string[]
  current: { has_description: boolean; objectives: number; outcome_codes: string[]; lesson_items: number }
}

export type OutlineApply = {
  description?: string
  objectives?: string[]
  outcomes?: { code: string; statement: string; bloom_level_ids: string[] }[]
  topics?: OutlineTopic[]
}

export type OutlineApplyResult = {
  description: boolean
  objectives: number
  outcomes_added: string[]
  outcomes_skipped: string[]
  syllabus: boolean
  lesson_items: number
  lesson_plan_kept: boolean
}

const API = `${PUBLIC_API_URL}/api/v1/authoring`
// A local model can take a while; the default 15 s client timeout is too short.
const AI_TIMEOUT_MS = 180_000

async function post<T>(path: string, body: unknown, timeoutMs = AI_TIMEOUT_MS): Promise<T> {
  const response = await apiFetch(`${API}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    timeoutMs,
  } as RequestInit & { timeoutMs: number })
  return response.json() as Promise<T>
}

export const authoringApi = {
  draft: (body: { curriculum_id: string; course_id: string; count: number; instruction?: string }) =>
    post<DraftResponse>("/course-outcomes/draft", body),

  refine: (body: {
    curriculum_id: string
    course_id: string
    statement: string
    bloom_level_ids: string[]
    instruction?: string
    course_outcome_id?: string
  }) => post<RefineResponse>("/course-outcomes/refine", body),

  /** Omit course_outcome_ids to map every CO; pass some to map only those (e.g. a new CO). */
  suggestMapping: (body: { curriculum_id: string; course_id: string; course_outcome_ids?: string[] }) =>
    post<MappingSuggestResponse>("/co-po/suggest", body),

  applyMapping: (suggestionId: string, items: ApplyItem[]) =>
    post<ApplyResponse>(`/co-po/suggestions/${suggestionId}/apply`, { items }, 30_000),

  readOutline: async (curriculumId: string, courseId: string, file: File) => {
    const form = new FormData()
    form.append("curriculum_id", curriculumId)
    form.append("course_id", courseId)
    form.append("file", file)
    const response = await apiFetch(`${API}/course-outline/read`, {
      method: "POST",
      body: form,
      timeoutMs: AI_TIMEOUT_MS,
    } as RequestInit & { timeoutMs: number })
    return response.json() as Promise<OutlinePreview>
  },

  applyOutline: (suggestionId: string, body: OutlineApply) =>
    post<OutlineApplyResult>(`/course-outline/suggestions/${suggestionId}/apply`, body, 30_000),

  /** Best effort: recording what the teacher did must never get in their way. */
  decide: (suggestionId: string, decision: Decision, detail?: Record<string, unknown>) =>
    post(`/suggestions/${suggestionId}/decision`, { decision, detail }, 15_000).catch(() => undefined),
}
