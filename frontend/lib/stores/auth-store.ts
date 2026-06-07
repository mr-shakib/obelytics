"use client"

import { create } from "zustand"
import type { UserProfile, PermissionManifest } from "@/types"

interface AuthState {
  accessToken: string | null
  user: UserProfile | null
  manifest: PermissionManifest | null
  isInitialized: boolean
  isAuthenticated: boolean

  setAuth: (token: string, user: UserProfile, manifest: PermissionManifest) => void
  clearAuth: () => void
  setInitialized: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  accessToken: null,
  user: null,
  manifest: null,
  isInitialized: false,
  isAuthenticated: false,

  setAuth: (token, user, manifest) =>
    set({ accessToken: token, user, manifest, isAuthenticated: true }),

  clearAuth: () =>
    set({ accessToken: null, user: null, manifest: null, isAuthenticated: false }),

  setInitialized: () => set({ isInitialized: true }),
}))
