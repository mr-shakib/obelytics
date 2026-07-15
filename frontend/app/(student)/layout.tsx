"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { Bell, LogOut } from "lucide-react"
import { useAuthStore } from "@/lib/stores/auth-store"
import { useNotificationStore } from "@/lib/stores/notification-store"
import { logoutApi } from "@/lib/api/auth"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { Skeleton } from "@/components/ui/skeleton"

const STUDENT_NAV = [
  { label: "My Curriculum", href: "/my-curriculum" },
  { label: "My Courses", href: "/my-courses" },
  { label: "My Results", href: "/my-results" },
  { label: "My Profile", href: "/my-profile" },
]

export default function StudentLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const pathname = usePathname()
  const { user, accessToken, isInitialized, isAuthenticated, clearAuth } = useAuthStore()
  const { unreadCount } = useNotificationStore()

  useEffect(() => {
    if (!isInitialized) return
    if (!isAuthenticated) router.replace("/login")
  }, [isInitialized, isAuthenticated, router])

  if (!isInitialized) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="space-y-3 w-72">
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-4 w-3/4" />
        </div>
      </div>
    )
  }

  if (!isAuthenticated) return null

  const initials = user
    ? `${user.first_name?.[0] ?? ""}${user.last_name?.[0] ?? ""}`.toUpperCase()
    : "?"

  async function handleLogout() {
    if (accessToken) await logoutApi(accessToken).catch(() => {})
    clearAuth()
    document.cookie = "auth-status=; Max-Age=0; path=/"
    router.push("/login")
  }

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="border-b bg-background sticky top-0 z-40">
        <div className="max-w-5xl mx-auto px-4 h-14 flex items-center gap-3">
          <span className="font-bold tracking-tight">Obelytics</span>
          <div className="flex-1" />
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Avatar className="h-7 w-7">
              <AvatarFallback className="text-xs">{initials}</AvatarFallback>
            </Avatar>
            <span className="hidden sm:block">{user?.first_name} {user?.last_name}</span>
          </div>
          <div className="relative">
            <Button variant="ghost" size="icon" nativeButton={false} render={<Link href="/notifications" />}>
              <Bell className="h-4 w-4" />
            </Button>
            {unreadCount > 0 && (
              <Badge
                variant="destructive"
                className="absolute -top-1 -right-1 h-4 w-4 p-0 flex items-center justify-center text-[10px] pointer-events-none"
              >
                {unreadCount > 99 ? "99+" : unreadCount}
              </Badge>
            )}
          </div>
          <Button variant="ghost" size="icon" onClick={handleLogout}>
            <LogOut className="h-4 w-4" />
          </Button>
        </div>

        {/* Tab navigation */}
        <div className="max-w-5xl mx-auto px-4 flex gap-1 border-t">
          {STUDENT_NAV.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "px-4 py-2 text-sm font-medium border-b-2 transition-colors",
                pathname === item.href
                  ? "border-primary text-foreground"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              )}
            >
              {item.label}
            </Link>
          ))}
        </div>
      </header>

      {/* Content */}
      <main className="flex-1 max-w-5xl mx-auto w-full px-4 py-6">
        {children}
      </main>
    </div>
  )
}
