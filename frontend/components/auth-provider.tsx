"use client"

import { useEffect, useRef } from "react"
import { useRouter } from "next/navigation"
import { useAuthStore } from "@/lib/stores/auth-store"
import { getMeApi } from "@/lib/api/auth"
import type { MeResponse } from "@/types"

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const { accessToken, setAuth, clearAuth, setInitialized, isInitialized } = useAuthStore()
  const router = useRouter()
  const initialized = useRef(false)

  useEffect(() => {
    if (initialized.current) return
    initialized.current = true

    async function init() {
      // Already have a token in memory (shouldn't happen on first mount, but guard anyway)
      if (accessToken) {
        setInitialized()
        return
      }

      try {
        // Ask the BFF to exchange the HttpOnly cookie for a fresh access token
        const refreshRes = await fetch("/api/auth/refresh", { method: "POST" })
        if (!refreshRes.ok) throw new Error("no_session")

        const { access_token } = await refreshRes.json()
        const me: MeResponse = await getMeApi(access_token)

        const { permissions, scope, offering_ids, ...user } = me
        setAuth(access_token, user, { permissions, scope, offering_ids })

        // Mark the lightweight cookie so middleware knows we're logged in
        document.cookie = "auth-status=authenticated; path=/; SameSite=Lax"

        // Start silent refresh 30 seconds before the 15-min expiry
        scheduleRefresh(14 * 60 * 1000, access_token)
      } catch {
        clearAuth()
        document.cookie = "auth-status=; Max-Age=0; path=/"
      } finally {
        setInitialized()
      }
    }

    init()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return <>{children}</>
}

let refreshTimer: ReturnType<typeof setTimeout> | null = null

function scheduleRefresh(delayMs: number, _currentToken: string) {
  if (refreshTimer) clearTimeout(refreshTimer)
  refreshTimer = setTimeout(async () => {
    try {
      const res = await fetch("/api/auth/refresh", { method: "POST" })
      if (!res.ok) throw new Error("refresh_failed")
      const { access_token } = await res.json()
      const me: MeResponse = await getMeApi(access_token)
      const { permissions, scope, offering_ids, ...user } = me
      useAuthStore.getState().setAuth(access_token, user, { permissions, scope, offering_ids })
      scheduleRefresh(14 * 60 * 1000, access_token)
    } catch {
      useAuthStore.getState().clearAuth()
      document.cookie = "auth-status=; Max-Age=0; path=/"
      window.location.href = "/login"
    }
  }, delayMs)
}
