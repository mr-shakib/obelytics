import { apiFetch, PUBLIC_API_URL } from "@/lib/api/client"

export type ReferenceDocument = {
  id: string
  title: string
  filename: string
  passage_count: number
  created_at: string
}

export type DraftSentence = {
  text: string
  cites: string[]
  gap: boolean
  status: "supported" | "check"
  issues: string[]
}

export type DraftSource = { kind: string; label: string; text: string; document_id?: string | null }

export type EvidenceDraft = {
  id: string
  program_id: string
  curriculum_id: string
  criterion_title: string
  criterion_guidance: string | null
  sentences: DraftSentence[]
  missing: string[]
  sources: Record<string, DraftSource>
  status: "DRAFT" | "ACCEPTED" | "REJECTED"
  edited_text: string | null
  model: string
  prompt_version: string
  created_at: string
  decided_at: string | null
}

const API = `${PUBLIC_API_URL}/api/v1/evidence`

async function call<T>(path: string, init?: RequestInit & { timeoutMs?: number }): Promise<T> {
  const response = await apiFetch(`${API}${path}`, init)
  return (response.status === 204 ? undefined : response.json()) as Promise<T>
}

function json(method: string, body: unknown, timeoutMs = 240_000) {
  return { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body), timeoutMs }
}

export const evidenceApi = {
  documents: () => call<ReferenceDocument[]>("/documents"),
  addDocument: (file: File, title?: string) => {
    const form = new FormData()
    form.append("file", file)
    if (title) form.append("title", title)
    return call<ReferenceDocument>("/documents", { method: "POST", body: form, timeoutMs: 120_000 })
  },
  deleteDocument: (id: string) => call<void>(`/documents/${id}`, { method: "DELETE" }),
  draft: (programId: string, body: { curriculum_id: string; criterion_title: string; criterion_guidance?: string }) =>
    call<EvidenceDraft>(`/programs/${programId}/drafts`, json("POST", body)),
  drafts: (programId: string, curriculumId: string) =>
    call<EvidenceDraft[]>(`/programs/${programId}/drafts?curriculum_id=${curriculumId}`),
  decide: (id: string, decision: "ACCEPTED" | "REJECTED", editedText?: string) =>
    call<EvidenceDraft>(`/drafts/${id}/decision`, json("POST", { decision, edited_text: editedText ?? null }, 30_000)),
}
