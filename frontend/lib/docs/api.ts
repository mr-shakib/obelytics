import { apiFetch, PUBLIC_API_URL } from "@/lib/api/client"

import type {
  AdminDocs,
  ApiReference,
  DocsGroup,
  LiveData,
  PublicDocs,
  SectionData,
  SectionVersion,
  ScheduleMode,
  Visibility,
} from "./types"

export const DOCS_API = `${PUBLIC_API_URL}/api/v1/docs`

/** The page is switched off or outside its schedule. */
export class DocsUnavailableError extends Error {
  constructor(public visibility: Visibility) {
    super(visibility.message)
  }
}

async function publicJson<T>(path: string): Promise<T> {
  const res = await fetch(`${DOCS_API}${path}`, { cache: "no-store" })
  if (res.status === 403) {
    const body = await res.json().catch(() => null)
    if (body?.detail?.state) throw new DocsUnavailableError(body.detail as Visibility)
  }
  if (!res.ok) throw new Error(`docs_${res.status}`)
  return res.json() as Promise<T>
}

export const docsPublicApi = {
  docs: () => publicJson<PublicDocs>("/public"),
  live: () => publicJson<LiveData>("/live"),
  apiReference: () => publicJson<ApiReference>("/api-reference"),
  exportUrl: `${DOCS_API}/export.md`,
}

/** photo_url from the API is a path under the backend; make it absolute. */
export function photoSrc(url: string): string {
  return url.startsWith("http") ? url : `${PUBLIC_API_URL}${url}`
}

async function adminJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await apiFetch(`${DOCS_API}/admin${path}`, init)
  return res.json() as Promise<T>
}

function json(method: string, body?: unknown): RequestInit {
  return {
    method,
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  }
}

export type SettingsInput = {
  is_enabled: boolean
  schedule_mode: ScheduleMode
  starts_at: string | null
  ends_at: string | null
  duration_minutes: number | null
  team_name: string | null
}

export const docsAdminApi = {
  get: () => adminJson<AdminDocs>(""),
  live: () => adminJson<LiveData>("/live"),
  apiReference: () => adminJson<ApiReference>("/api-reference"),
  updateSettings: (body: SettingsInput) => adminJson<AdminDocs>("/settings", json("PUT", body)),
  resetWindow: () => adminJson<AdminDocs>("/settings/reset-window", json("POST")),
  createSection: (title: string, group: DocsGroup) =>
    adminJson<AdminDocs>("/sections", json("POST", { title, group })),
  saveDraft: (id: string, body: { title: string; body: string; data?: SectionData }) =>
    adminJson<AdminDocs>(`/sections/${id}`, json("PUT", body)),
  setVisible: (id: string, is_visible: boolean) =>
    adminJson<AdminDocs>(`/sections/${id}/visibility`, json("PUT", { is_visible })),
  publish: (id: string) => adminJson<AdminDocs>(`/sections/${id}/publish`, json("POST")),
  publishAll: () => adminJson<AdminDocs>("/publish-all", json("POST")),
  discard: (id: string) => adminJson<AdminDocs>(`/sections/${id}/discard`, json("POST")),
  versions: (id: string) => adminJson<SectionVersion[]>(`/sections/${id}/versions`),
  restore: (id: string, version: number) =>
    adminJson<AdminDocs>(`/sections/${id}/versions/${version}/restore`, json("POST")),
  deleteSection: (id: string) => adminJson<AdminDocs>(`/sections/${id}`, json("DELETE")),
  reorderSections: (ids: string[]) => adminJson<AdminDocs>("/sections-order", json("PUT", { ids })),
  addMember: (form: FormData) => adminJson<AdminDocs>("/team", { method: "POST", body: form }),
  updateMember: (id: string, body: { full_name: string; role: string; email: string }) =>
    adminJson<AdminDocs>(`/team/${id}`, json("PUT", body)),
  setPhoto: (id: string, form: FormData) =>
    adminJson<AdminDocs>(`/team/${id}/photo`, { method: "PUT", body: form }),
  deletePhoto: (id: string) => adminJson<AdminDocs>(`/team/${id}/photo`, json("DELETE")),
  deleteMember: (id: string) => adminJson<AdminDocs>(`/team/${id}`, json("DELETE")),
  reorderTeam: (ids: string[]) => adminJson<AdminDocs>("/team-order", json("PUT", { ids })),
}
