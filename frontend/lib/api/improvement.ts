import { apiFetch, PUBLIC_API_URL } from "@/lib/api/client"

export type EvidenceItem = { tool: string | null; ref: string; detail: string; verified: boolean }

export type Intervention = {
  id: string
  action: string
  kind: "teaching" | "assessment" | "outcome" | "mapping"
  effort: "low" | "medium" | "high"
  success_measure: string
  decision: "ACCEPTED" | "REJECTED" | null
  note: string | null
}

export type Diagnosis = {
  id: string
  co: string
  problem: string
  likely_cause: string
  confidence: number | null
  evidence: EvidenceItem[]
  /** false: none of its evidence was found in what the tools returned. */
  supported: boolean
  interventions: Intervention[]
}

export type AgentStep = {
  thought: string | null
  tool: string | null
  co: string | null
  action: string | null
  chosen_by: "fixed" | "model" | "code"
  result: Record<string, unknown> | null
}

export type ImprovementPlan = {
  id: string
  section_offering_id: string
  summary: string
  follow_up: string | null
  diagnoses: Diagnosis[]
  steps: AgentStep[]
  model: string
  prompt_version: string
  created_at: string
}

const API = `${PUBLIC_API_URL}/api/v1/improvement`

async function call<T>(path: string, init?: RequestInit & { timeoutMs?: number }): Promise<T> {
  const response = await apiFetch(`${API}${path}`, init)
  return response.json() as Promise<T>
}

export const improvementApi = {
  latest: (sectionId: string) => call<ImprovementPlan | null>(`/sections/${sectionId}/plan`),
  /** Several model calls (up to six tool steps and the plan). */
  run: (sectionId: string) => call<ImprovementPlan>(`/sections/${sectionId}/plan`, { method: "POST", timeoutMs: 300_000 }),
  decide: (planId: string, interventionId: string, decision: "ACCEPTED" | "REJECTED", note?: string) =>
    call<ImprovementPlan>(`/plans/${planId}/interventions/${interventionId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ decision, note }),
    }),
}
