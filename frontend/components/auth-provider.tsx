"use client"

import { useEffect, useRef } from "react"
import { useRouter } from "next/navigation"
import { useAuthStore, loadPersisted } from "@/lib/stores/auth-store"
import { getMeApi } from "@/lib/api/auth"
import type { MeResponse } from "@/types"

function getCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`))
  return match ? decodeURIComponent(match[1]) : null
}

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
        // Check if we have a cached access_token cookie from a prior login/refresh
        const cachedToken = getCookie("access_token")
        const cachedData = loadPersisted()

        let token: string
        if (cachedToken && cachedData) {
          // Fast path: token + user data all cached — skip getMeApi entirely
          token = cachedToken
          setAuth(token, cachedData.user, cachedData.manifest)
          scheduleRefresh(14 * 60 * 1000, token)
          document.cookie = "auth-status=authenticated; path=/; SameSite=Lax"
          setInitialized()
          return
        }

        if (cachedToken) {
          token = cachedToken
        } else {
          // No cached token — ask the BFF to exchange the HttpOnly refresh cookie
          const refreshRes = await fetch("/api/auth/refresh", { method: "POST" })
          if (!refreshRes.ok) throw new Error("no_session")
          const data = await refreshRes.json()
          token = data.access_token
        }

        const me: MeResponse = await getMeApi(token)

        const { permissions, scope, offering_ids, ...user } = me
        setAuth(token, user, { permissions, scope, offering_ids })

        // Mark the lightweight cookie so middleware knows we're logged in
        document.cookie = "auth-status=authenticated; path=/; SameSite=Lax"

        // Start silent refresh 30 seconds before the 15-min expiry
        scheduleRefresh(14 * 60 * 1000, token)
      } catch {
        clearAuth()
        document.cookie = "auth-status=; Max-Age=0; path=/"
        document.cookie = "access_token=; Max-Age=0; path=/"
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

      // Token refreshed — update the token in zustand. User/permissions
      // are already in localStorage and zustand, no need to re-fetch.
      useAuthStore.setState({ accessToken: access_token })
      scheduleRefresh(14 * 60 * 1000, access_token)
    } catch {
      useAuthStore.getState().clearAuth()
      document.cookie = "auth-status=; Max-Age=0; path=/"
      window.location.href = "/login"
    }
  }, delayMs)
}
