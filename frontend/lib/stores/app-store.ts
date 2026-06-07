"use client"

import { create } from "zustand"
import { persist } from "zustand/middleware"

interface AppState {
  activeProgramId: string | null
  sidebarCollapsed: boolean
  theme: "light" | "dark"

  setActiveProgram: (id: string | null) => void
  toggleSidebar: () => void
  setTheme: (theme: "light" | "dark") => void
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      activeProgramId: null,
      sidebarCollapsed: false,
      theme: "light",

      setActiveProgram: (id) => set({ activeProgramId: id }),
      toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
      setTheme: (theme) => set({ theme }),
    }),
    { name: "obelytics-app-prefs", partialize: (s) => ({ sidebarCollapsed: s.sidebarCollapsed, theme: s.theme }) }
  )
)
