"use client"

import { create } from "zustand"
import type { UserProfile, PermissionManifest } from "@/types"

const STORAGE_KEY = "obelytics_auth"

interface PersistedAuth {
  user: UserProfile
  manifest: PermissionManifest
}

function loadPersisted(): PersistedAuth | null {
  if (typeof window === "undefined") return null
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    return JSON.parse(raw) as PersistedAuth
  } catch {
    return null
  }
}

function persistAuth(user: UserProfile, manifest: PermissionManifest) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ user, manifest }))
  } catch {
    // storage full or unavailable — degrade gracefully
  }
}

function clearPersisted() {
  try {
    localStorage.removeItem(STORAGE_KEY)
  } catch {
    // ignore
  }
}

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

  setAuth: (token, user, manifest) => {
    persistAuth(user, manifest)
    set({ accessToken: token, user, manifest, isAuthenticated: true })
  },

  clearAuth: () => {
    clearPersisted()
    set({ accessToken: null, user: null, manifest: null, isAuthenticated: false })
  },

  setInitialized: () => set({ isInitialized: true }),
}))

export { loadPersisted }
