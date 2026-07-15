"use client"

import Link from "next/link"
import { useEffect } from "react"
import { useRouter, usePathname } from "next/navigation"
import { Bell, ChevronDown, LogOut, User } from "lucide-react"
import { useQuery } from "@tanstack/react-query"
import { Button } from "@/components/ui/button"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { useAuthStore } from "@/lib/stores/auth-store"
import { useAppStore } from "@/lib/stores/app-store"
import { useNotificationStore } from "@/lib/stores/notification-store"
import { usePermissions } from "@/hooks/use-permission"
import { logoutApi } from "@/lib/api/auth"
import { queryKeys } from "@/lib/query-keys"
import { fetchWithTimeout } from "@/lib/api/client"
import {
  NAV_GROUP_META,
  getActiveNavGroup,
  getVisibleNavItems,
  isNavItemActive,
} from "@/lib/navigation"

// The full navigation lives in the sidebar; the header shows a breadcrumb of
// the current location for orientation.
function LocationBreadcrumb() {
  const pathname = usePathname()
  const permissions = usePermissions()
  const visibleItems = getVisibleNavItems(permissions)
  const activeGroup = getActiveNavGroup(pathname, visibleItems)
  const activeItem = visibleItems.find((item) => isNavItemActive(item, pathname))

  if (!activeItem) return null
  const meta = NAV_GROUP_META[activeGroup]
  const Icon = meta.icon

  return (
    <div className="flex min-w-0 items-center gap-1.5 text-[13px]">
      <Icon className="size-[14px] shrink-0 text-muted-foreground" />
      <span className="shrink-0 text-muted-foreground">{meta.label}</span>
      <span className="shrink-0 text-muted-foreground/50">/</span>
      <span className="truncate font-medium text-foreground">{activeItem.label}</span>
    </div>
  )
}

export function Header() {
  const router = useRouter()
  const { user, manifest, accessToken, clearAuth } = useAuthStore()
  const { activeProgramId, setActiveProgram } = useAppStore()
  const { unreadCount, setUnreadCount } = useNotificationStore()

  const programs = manifest?.scope.programs ?? []
  const isGlobal = manifest?.scope.is_global ?? false

  const { data: fetchedUnreadCount = 0 } = useQuery({
    queryKey: queryKeys.notifications.unreadCount,
    queryFn: async () => {
      const res = await fetchWithTimeout(`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/v1/notifications/me/count`, {
        headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
      })
      if (!res.ok) return 0
      const data = await res.json() as { unread_count?: number }
      return data.unread_count ?? 0
    },
    refetchInterval: 60_000,
    enabled: !!accessToken,
  })

  useEffect(() => {
    setUnreadCount(fetchedUnreadCount)
  }, [fetchedUnreadCount, setUnreadCount])

  async function handleLogout() {
    if (accessToken) await logoutApi(accessToken).catch(() => {})
    clearAuth()
    document.cookie = "auth-status=; Max-Age=0; path=/"
    router.push("/login")
  }

  const displayName = user?.full_name ?? `${user?.first_name ?? ""} ${user?.last_name ?? ""}`.trim()
  const initials = (displayName || "?")
    .split(" ")
    .map((w) => w[0] ?? "")
    .slice(0, 2)
    .join("")
    .toUpperCase()

  return (
    <header className="flex h-14 items-center border-b bg-background px-4 gap-3">
      <LocationBreadcrumb />

      {!isGlobal && programs.length > 0 && (
        <Select
          value={activeProgramId ?? ""}
          onValueChange={(v) => setActiveProgram((v as string | null) || null)}
        >
          <SelectTrigger className="w-48 h-8 text-sm">
            <SelectValue placeholder="Select program…">
              {(value: string) => {
                const p = programs.find((p) => p.id === value)
                return p ? `${p.acronym} — ${p.name}` : value
              }}
            </SelectValue>
          </SelectTrigger>
          <SelectContent>
            {programs.map((p) => (
              <SelectItem key={p.id} value={p.id}>
                {p.acronym} — {p.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      )}

      <div className="flex-1" />

      {/* Notification bell — nativeButton={false} because Link renders <a>, not <button> */}
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

      <DropdownMenu>
        <DropdownMenuTrigger className="flex items-center gap-2 rounded-md px-2 py-1 text-sm hover:bg-muted transition-colors">
          <Avatar className="h-7 w-7">
            <AvatarFallback className="text-xs">{initials}</AvatarFallback>
          </Avatar>
          <span className="hidden md:block">{displayName}</span>
          <ChevronDown className="h-3 w-3 text-muted-foreground" />
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-52">
          <DropdownMenuLabel>
            <p className="text-sm font-medium">{displayName}</p>
            {user?.employee_id && (
              <p className="text-xs font-mono text-muted-foreground font-normal">{user.employee_id}</p>
            )}
            <p className="text-xs text-muted-foreground font-normal truncate">{user?.email}</p>
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuItem render={<Link href="/profile" />}>
            <User className="mr-2 h-4 w-4" />
            Profile
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={handleLogout} variant="destructive">
            <LogOut className="mr-2 h-4 w-4" />
            Sign out
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </header>
  )
}
