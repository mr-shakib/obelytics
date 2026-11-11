import { apiFetch, PUBLIC_API_URL } from "@/lib/api/client"

export type ProviderName = "local" | "hosted" | "off"
export type Feature = "integrity" | "copilot"

export type FeatureSetting = {
  feature: Feature
  /** null: the organization has not chosen, so the server default applies. */
  chosen: ProviderName | null
  default: ProviderName
  effective: ProviderName
}

export type ProviderStatus = {
  name: "local" | "hosted"
  configured: boolean
  /** External: data leaves your servers, so personal data is redacted first. */
  external: boolean
  models: Record<"text" | "vision" | "chat", string | null>
  reachable: boolean | null
  installed_models: string[] | null
}

export type AISettings = { features: FeatureSetting[]; providers: ProviderStatus[] }

export type UsageRow = {
  feature: string
  provider: string
  model: string
  calls: number
  errors: number
  input_tokens: number
  output_tokens: number
  images: number
  redactions: number
  cost_usd: number
  avg_latency_ms: number
}

export type AIUsage = {
  days: number
  calls: number
  errors: number
  input_tokens: number
  output_tokens: number
  redactions: number
  cost_usd: number
  rows: UsageRow[]
}

const API = `${PUBLIC_API_URL}/api/v1/ai`

async function readJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await apiFetch(`${API}${path}`, init)
  return response.json() as Promise<T>
}

export const aiApi = {
  settings: () => readJson<AISettings>("/settings"),
  updateSettings: (change: Partial<Record<`${Feature}_provider`, ProviderName | null>>) =>
    readJson<AISettings>("/settings", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(change),
    }),
  usage: (days: number) => readJson<AIUsage>(`/usage?days=${days}`),
}
