import createClient from "openapi-fetch"
import type { paths } from "@/types/api"
import { useAuthStore } from "@/lib/stores/auth-store"
import { useAppStore } from "@/lib/stores/app-store"
import { toast } from "sonner"

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

// Raw client used by BFF route handlers (server-side, no interceptors)
export const rawApiClient = createClient<paths>({ baseUrl: `${BASE_URL}/api/v1` })

// ─── Intercepted fetch for client-side calls ──────────────────────────────────

let isRefreshing = false
let refreshQueue: Array<(token: string) => void> = []

async function refreshToken(): Promise<string> {
  const res = await fetch("/api/auth/refresh", { method: "POST" })
  if (!res.ok) throw new Error("refresh_failed")
  const data = await res.json()
  return data.access_token as string
}

async function interceptedFetch(
  input: RequestInfo | URL,
  init?: RequestInit
): Promise<Response> {
  const { accessToken, setAuth, user, manifest, clearAuth } = useAuthStore.getState()
  const { activeProgramId } = useAppStore.getState()

  const headers = new Headers(init?.headers)
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`)
  if (activeProgramId) headers.set("X-Program-Id", activeProgramId)

  let res = await fetch(input, { ...init, headers })

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
        res = await fetch(input, { ...init, headers })
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
      res = await fetch(input, { ...init, headers })
    }
  }

  if (res.status === 403) {
    toast.error("You don't have permission for this action")
  }

  if (res.status === 400 || res.status === 404 || res.status === 409 || res.status === 422) {
    toast.error("Please check the information and try again.")
  }

  if (res.status >= 500) {
    toast.error("Something went wrong. Please try again.")
  }

  if (!res.ok) {
    throw new Error(`api_error_${res.status}`)
  }

  return res
}

export const apiClient = createClient<paths>({
  baseUrl: `${BASE_URL}/api/v1`,
  fetch: interceptedFetch,
})
