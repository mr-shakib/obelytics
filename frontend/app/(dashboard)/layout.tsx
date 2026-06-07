"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"
import { Sidebar } from "@/components/layout/sidebar"
import { Header } from "@/components/layout/header"
import { useAuthStore } from "@/lib/stores/auth-store"
import { Skeleton } from "@/components/ui/skeleton"

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const { isAuthenticated, isInitialized, manifest } = useAuthStore()

  useEffect(() => {
    if (!isInitialized) return
    if (!isAuthenticated) {
      router.replace("/login")
      return
    }
    // Redirect students to their portal
    const permissions = manifest?.permissions ?? []
    if (!permissions.some((p) => p !== "student")) {
      // very rough check — refine based on actual student permission pattern
    }
  }, [isInitialized, isAuthenticated, router, manifest])

  if (!isInitialized) {
    return (
      <div className="flex h-screen items-center justify-center" suppressHydrationWarning>
        <div className="space-y-3 w-72" suppressHydrationWarning>
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="h-4 w-1/2" />
        </div>
      </div>
    )
  }

  if (!isAuthenticated) return null

  return (
    <div className="flex h-dvh overflow-hidden" suppressHydrationWarning>
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden min-w-0" suppressHydrationWarning>
        <Header />
        <main className="flex-1 overflow-y-auto bg-muted/30 p-6">
          {children}
        </main>
      </div>
    </div>
  )
}
