import { apiFetch, PUBLIC_API_URL } from "@/lib/api/client"

export type Skill = { name: string; category: "technical" | "professional"; required: boolean }

export type JobPosting = {
  id: string
  program_id: string
  title: string
  employer: string | null
  source: string | null
  posted_on: string | null
  text: string
  /** null until the AI has read it (retried at the next analysis). */
  skills: Skill[] | null
  skills_model: string | null
  skills_prompt_version: string | null
  created_at: string
}

export type OutcomeRef = {
  ref: string
  co_id: string
  co_code: string
  course_id: string
  course_code: string
  course_title: string
  statement: string
}

export type SkillCoverage = {
  skill: string
  category: string
  postings: number
  required: number
  example_titles: string[]
  coverage: "covered" | "partial" | "gap" | "unjudged"
  outcomes: OutcomeRef[]
  program_outcomes: string[]
  reason: string
  suggested_course: { id: string; code: string; title: string } | null
  notes: string[]
}

export type MarketAnalysis = {
  id: string
  program_id: string
  curriculum_id: string
  posting_count: number
  skills: SkillCoverage[]
  summary: {
    skills: number
    covered: number
    partial: number
    gap: number
    unjudged: number
    coverage_pct: number | null
  }
  program_outcomes: { code: string; statement: string; skills: string[]; demand: number }[]
  model: string
  prompt_version: string
  created_at: string
}

const API = `${PUBLIC_API_URL}/api/v1/workforce`
const AI_TIMEOUT_MS = 240_000

async function call<T>(path: string, init?: RequestInit & { timeoutMs?: number }): Promise<T> {
  const response = await apiFetch(`${API}${path}`, init)
  return (response.status === 204 ? undefined : response.json()) as Promise<T>
}

function json(method: string, body: unknown, timeoutMs = AI_TIMEOUT_MS) {
  return {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    timeoutMs,
  }
}

export const workforceApi = {
  postings: (programId: string) => call<JobPosting[]>(`/programs/${programId}/postings`),
  addPosting: (
    programId: string,
    body: { title: string; employer?: string; source?: string; text: string },
  ) => call<JobPosting>(`/programs/${programId}/postings`, json("POST", body, 120_000)),
  deletePosting: (id: string) => call<void>(`/postings/${id}`, { method: "DELETE" }),
  analyze: (programId: string, curriculumId: string) =>
    call<MarketAnalysis>(`/programs/${programId}/analysis`, json("POST", { curriculum_id: curriculumId })),
  latest: (programId: string, curriculumId: string) =>
    call<MarketAnalysis | null>(`/programs/${programId}/analysis?curriculum_id=${curriculumId}`),
}
