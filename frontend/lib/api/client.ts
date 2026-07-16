import createClient from "openapi-fetch"
import type { paths } from "@/types/api"
import { useAuthStore } from "@/lib/stores/auth-store"
import { useAppStore } from "@/lib/stores/app-store"
import { toast } from "sonner"

// Server-side (BFF): use BACKEND_URL directly.
// Client-side: use NEXT_PUBLIC_API_URL to call the backend without a proxy hop.
const BACKEND_URL = process.env.BACKEND_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

// Raw client used by BFF route handlers (server-side, no interceptors)
export const rawApiClient = createClient<paths>({ baseUrl: `${BACKEND_URL}/api/v1` })

// Public backend URL baked into the client bundle at build time
export const PUBLIC_API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

// ─── Fetch with timeout ──────────────────────────────────────────────────────

const FETCH_TIMEOUT_MS = 15_000

export function fetchWithTimeout(
  input: RequestInfo | URL,
  init?: RequestInit & { timeoutMs?: number }
): Promise<Response> {
  const timeoutMs = init?.timeoutMs ?? FETCH_TIMEOUT_MS
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)
  return fetch(input, { ...init, signal: controller.signal }).finally(() => clearTimeout(timer))
}

// ─── Intercepted fetch for client-side calls ──────────────────────────────────

let isRefreshing = false
let refreshQueue: Array<(token: string) => void> = []

async function refreshToken(): Promise<string> {
  const res = await fetchWithTimeout("/api/auth/refresh", { method: "POST" })
  if (!res.ok) throw new Error("refresh_failed")
  const data = await res.json()
  return data.access_token as string
}

export async function apiFetch(
  input: RequestInfo | URL,
  init?: RequestInit
): Promise<Response> {
  const { accessToken, setAuth, user, manifest, clearAuth } = useAuthStore.getState()
  const { activeProgramId } = useAppStore.getState()

  // openapi-fetch passes a pre-built Request as `input` (with `init` undefined) so its
  // Content-Type/body are already baked in — seed from `input.headers` first, otherwise
  // building a fresh Headers() here would silently drop Content-Type and break JSON bodies.
  const seedHeaders = input instanceof Request ? input.headers : init?.headers
  const headers = new Headers(seedHeaders)
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`)
  if (activeProgramId) headers.set("X-Program-Id", activeProgramId)

  let res = await fetchWithTimeout(input, { ...init, headers })

  if (res.status === 401) {
    if (!isRefreshing) {
      isRefreshing = true
      try {
        const newToken = await refreshToken()
        useAuthStore.setState({ accessToken: newToken, isAuthenticated: true })
        refreshQueue.forEach((cb) => cb(newToken))
        refreshQueue = []
        isRefreshing = false

        headers.set("Authorization", `Bearer ${newToken}`)
        res = await fetchWithTimeout(input, { ...init, headers })
      } catch {
        isRefreshing = false
        refreshQueue = []
        clearAuth()
        // set a flag cookie so middleware redirects to /login
        document.cookie = "auth-status=; Max-Age=0; path=/"
        window.location.href = "/login"
        throw new Error("session_expired")
      }
    } else {
      // queue while refresh is in flight
      const newToken = await new Promise<string>((resolve) => refreshQueue.push(resolve))
      headers.set("Authorization", `Bearer ${newToken}`)
      res = await fetchWithTimeout(input, { ...init, headers })
    }
  }

  if (!res.ok) {
    // Try to surface the backend's specific error message (FastAPI's `detail` field)
    // instead of a generic one, e.g. "A curriculum with this code already exists for this program".
    let detail: string | undefined
    try {
      const body = await res.clone().json()
      if (typeof body?.detail === "string") detail = body.detail
    } catch {
      // response body isn't JSON — fall back to generic messaging below
    }

    if (res.status === 403) {
      toast.error("You don't have permission for this action")
    } else if (res.status === 400 || res.status === 409 || res.status === 422) {
      toast.error(detail ?? "Please check the information and try again.")
    } else if (res.status >= 500) {
      toast.error("Something went wrong. Please try again.")
    }

    throw new Error(detail ?? `api_error_${res.status}`)
  }

  return res
}

export const apiClient = createClient<paths>({
  baseUrl: `${PUBLIC_API_URL}/api/v1`,
  fetch: apiFetch,
})
