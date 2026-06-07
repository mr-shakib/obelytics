"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { useState, useEffect } from "react"
import { CircleDot, ChevronLeft, ChevronRight, Settings } from "lucide-react"
import { cn } from "@/lib/utils"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { useAppStore } from "@/lib/stores/app-store"
import { useAuthStore } from "@/lib/stores/auth-store"
import { usePermissions } from "@/hooks/use-permission"
import {
  NAV_ITEMS,
  NAV_GROUPS,
  NAV_GROUP_META,
  type NavItem,
  type NavGroup,
} from "@/lib/navigation"

function canView(item: NavItem, permissions: string[]) {
  return item.permission === null || permissions.includes(item.permission)
}

function isItemActive(item: NavItem, pathname: string) {
  return item.href === "/overview"
    ? pathname === "/overview" || pathname === "/"
    : pathname === item.href || pathname.startsWith(item.href + "/")
}

function getActiveGroup(pathname: string, items: NavItem[]): NavGroup {
  const active = items.find((item) => isItemActive(item, pathname))
  return (active?.group as NavGroup | undefined) ?? "Core"
}

export function Sidebar() {
  const pathname = usePathname()
  const collapsed = useAppStore((s) => s.sidebarCollapsed)
  const toggleSidebar = useAppStore((s) => s.toggleSidebar)
  const setSidebarCollapsed = useAppStore((s) => s.setSidebarCollapsed)
  const { user } = useAuthStore()
  const permissions = usePermissions()

  const visibleItems = NAV_ITEMS.filter((item) => canView(item, permissions))

  const [selectedGroup, setSelectedGroup] = useState<NavGroup>(
    () => getActiveGroup(pathname, visibleItems)
  )

  useEffect(() => {
    const group = getActiveGroup(pathname, visibleItems)
    setSelectedGroup(group)
  }, [pathname]) // eslint-disable-line react-hooks/exhaustive-deps

  const displayName =
    (user?.full_name ?? `${user?.first_name ?? ""} ${user?.last_name ?? ""}`.trim()) || "User"
  const initials =
    displayName
      .split(" ")
      .map((w: string) => w[0] ?? "")
      .slice(0, 2)
      .join("")
      .toUpperCase() || "U"
  const roleLabel = user?.email ?? "Account settings"

  function selectGroup(group: NavGroup) {
    setSelectedGroup(group)
    if (collapsed) setSidebarCollapsed(false)
  }

  const panelItems = visibleItems.filter((item) => item.group === selectedGroup)

  return (
    <aside
      className={cn(
        "relative m-3 flex h-[calc(100dvh-1.5rem)] shrink-0 flex-col overflow-hidden",
        "rounded-[22px] border border-sidebar-border bg-sidebar shadow-sm",
        "transition-[width] duration-200 ease-out",
        collapsed ? "w-[72px]" : "w-[252px]"
      )}
    >
      {/* ── Brand header ── */}
      <div
        className={cn(
          "flex h-[62px] shrink-0 items-center border-b border-sidebar-border/40",
          collapsed ? "justify-center px-2" : "gap-3 px-4"
        )}
      >
        <Link
          href="/overview"
          className="flex size-9 shrink-0 items-center justify-center rounded-xl border-2 border-sidebar-primary text-sidebar-primary transition-colors hover:bg-sidebar-primary/10"
        >
          <CircleDot className="size-4" />
        </Link>
        {!collapsed && (
          <span className="truncate text-[13px] font-bold tracking-tight text-sidebar-foreground">
            Obelytics
          </span>
        )}
      </div>

      {/* ── Main body: icon rail + item panel ── */}
      <div className="flex min-h-0 flex-1">

        {/* Left icon rail */}
        <div
          className={cn(
            "flex flex-col items-center py-3 gap-0.5",
            collapsed
              ? "w-full px-2"
              : "w-[72px] shrink-0 border-r border-sidebar-border/30 px-2"
          )}
        >
          {NAV_GROUPS.map((group) => {
            const meta = NAV_GROUP_META[group]
            const groupItems = visibleItems.filter((i) => i.group === group)
            if (groupItems.length === 0) return null

            const isSelected = selectedGroup === group && !collapsed
            const hasActive = groupItems.some((i) => isItemActive(i, pathname))
            const Icon = meta.icon

            const btn = (
              <button
                type="button"
                onClick={() => selectGroup(group)}
                className={cn(
                  "relative flex w-full flex-col items-center justify-center gap-[3px] rounded-xl px-1 py-2 transition-all duration-150",
                  isSelected
                    ? "bg-sidebar-primary text-sidebar-primary-foreground shadow-[0_2px_10px_rgba(0,0,0,0.18)]"
                    : hasActive && collapsed
                    ? "bg-sidebar-accent text-sidebar-primary"
                    : "text-sidebar-foreground/50 hover:bg-sidebar-accent hover:text-sidebar-foreground"
                )}
              >
                {/* Active dot — top-right corner, only in expanded mode for non-selected groups */}
                {hasActive && !isSelected && !collapsed && (
                  <span className="absolute right-2 top-2 size-1.5 rounded-full bg-sidebar-primary" />
                )}
                <Icon className="size-4 shrink-0" />
                <span className={cn(
                  "w-full truncate text-center text-[9px] font-semibold leading-none tracking-wide",
                  isSelected ? "opacity-90" : "opacity-70"
                )}>
                  {meta.short}
                </span>
              </button>
            )

            if (collapsed) {
              return (
                <Tooltip key={group}>
                  <TooltipTrigger render={<span className="flex" />}>
                    {btn}
                  </TooltipTrigger>
                  <TooltipContent side="right" sideOffset={8}>
                    {meta.label}
                  </TooltipContent>
                </Tooltip>
              )
            }

            return <span key={group}>{btn}</span>
          })}

          {/* Spacer pushes collapse toggle to bottom */}
          <div className="flex-1" />

          {/* Collapse / expand toggle */}
          <button
            type="button"
            onClick={toggleSidebar}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            className="flex size-8 items-center justify-center rounded-xl text-sidebar-foreground/35 transition-all hover:bg-sidebar-accent hover:text-sidebar-foreground"
          >
            {collapsed
              ? <ChevronRight className="size-3.5" />
              : <ChevronLeft className="size-3.5" />}
          </button>
        </div>

        {/* Right item panel */}
        {!collapsed && (
          <ScrollArea className="min-w-0 flex-1">
            <div className="px-2 pb-4 pt-5">
              {/* Group label */}
              <p className="mb-2.5 px-2 text-[10px] font-semibold uppercase tracking-[0.14em] text-sidebar-foreground/35">
                {NAV_GROUP_META[selectedGroup].label}
              </p>

              {/* Items — keyed on selectedGroup so animate-in fires on switch */}
              <div
                key={selectedGroup}
                className="animate-in fade-in slide-in-from-bottom-2 space-y-0.5 duration-150"
              >
                {panelItems.map((item) => {
                  const active = isItemActive(item, pathname)
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      aria-current={active ? "page" : undefined}
                      className={cn(
                        "group relative flex h-9 w-full items-center gap-2.5 rounded-lg px-2.5 text-[13px]",
                        "transition-all duration-150 [&>svg]:size-[15px] [&>svg]:shrink-0",
                        active
                          ? "bg-sidebar-accent font-semibold text-sidebar-foreground"
                          : "font-medium text-sidebar-foreground/58 hover:bg-sidebar-accent/65 hover:text-sidebar-foreground"
                      )}
                    >
                      {active && (
                        <span className="absolute left-0 top-1/2 h-5 w-[3px] -translate-y-1/2 rounded-r-full bg-sidebar-primary" />
                      )}
                      <item.icon
                        className={cn(
                          "transition-colors",
                          active
                            ? "text-sidebar-primary"
                            : "text-sidebar-foreground/38 group-hover:text-sidebar-primary/70"
                        )}
                      />
                      <span className="truncate">{item.label}</span>
                    </Link>
                  )
                })}
              </div>
            </div>
          </ScrollArea>
        )}
      </div>

      {/* ── User footer ── */}
      <div className="shrink-0 border-t border-sidebar-border/40 p-2">
        {collapsed ? (
          <Tooltip>
            <TooltipTrigger render={<span className="flex justify-center" />}>
              <Link
                href="/profile"
                className="flex size-10 items-center justify-center rounded-xl transition-colors hover:bg-sidebar-accent"
              >
                <Avatar size="sm" className="size-8 rounded-xl">
                  <AvatarFallback className="rounded-xl bg-sidebar-primary text-[11px] font-bold text-sidebar-primary-foreground">
                    {initials}
                  </AvatarFallback>
                </Avatar>
              </Link>
            </TooltipTrigger>
            <TooltipContent side="right" sideOffset={8}>
              {displayName}
            </TooltipContent>
          </Tooltip>
        ) : (
          <Link
            href="/profile"
            className="flex w-full items-center gap-2.5 rounded-xl p-2 transition-colors hover:bg-sidebar-accent"
          >
            <Avatar size="sm" className="size-8 shrink-0 rounded-xl">
              <AvatarFallback className="rounded-xl bg-sidebar-primary text-[11px] font-bold text-sidebar-primary-foreground">
                {initials}
              </AvatarFallback>
            </Avatar>
            <div className="min-w-0 flex-1">
              <p className="truncate text-[12px] font-semibold leading-tight text-sidebar-foreground">
                {displayName}
              </p>
              <p className="truncate text-[10px] leading-tight text-sidebar-foreground/38">
                {roleLabel}
              </p>
            </div>
            <Settings className="size-3.5 shrink-0 text-sidebar-foreground/28" />
          </Link>
        )}
      </div>
    </aside>
  )
}
