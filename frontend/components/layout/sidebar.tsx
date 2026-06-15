"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { CircleDot, ChevronLeft, ChevronRight, Settings } from "lucide-react"
import { cn } from "@/lib/utils"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { useAppStore } from "@/lib/stores/app-store"
import { useAuthStore } from "@/lib/stores/auth-store"
import { usePermissions } from "@/hooks/use-permission"
import {
  NAV_GROUP_META,
  isNavItemActive,
  isSectionTeacherView,
  getActiveNavGroup,
  getVisibleNavItems,
} from "@/lib/navigation"

export function Sidebar() {
  const pathname = usePathname()
  const collapsed = useAppStore((s) => s.sidebarCollapsed)
  const toggleSidebar = useAppStore((s) => s.toggleSidebar)
  const { user } = useAuthStore()
  const permissions = usePermissions()

  const visibleItems = getVisibleNavItems(permissions)
  const homeHref = isSectionTeacherView(permissions) ? "/my-sections" : "/overview"
  const activeGroup = getActiveNavGroup(pathname, visibleItems)
  const groupItems = visibleItems.filter((item) => item.group === activeGroup)
  const groupMeta = NAV_GROUP_META[activeGroup]

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
          href={homeHref}
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

      {/* ── Group items panel ── */}
      <ScrollArea className="min-h-0 flex-1">
        <div className={cn("py-4", collapsed ? "px-2" : "px-2.5")}>
          {!collapsed && (
            <p className="mb-2.5 px-2 text-[10px] font-semibold uppercase tracking-[0.14em] text-sidebar-foreground/35">
              {groupMeta.label}
            </p>
          )}

          {/* Items — keyed on activeGroup so animate-in fires on switch */}
          <div
            key={activeGroup}
            className="animate-in fade-in slide-in-from-bottom-2 space-y-0.5 duration-150"
          >
            {groupItems.map((item) => {
              const active = isNavItemActive(item, pathname)
              const link = (
                <Link
                  href={item.href}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "group relative flex h-9 items-center gap-2.5 rounded-lg px-2.5 text-[13px]",
                    "transition-all duration-150 [&>svg]:size-[15px] [&>svg]:shrink-0",
                    collapsed ? "w-10 justify-center" : "w-full",
                    active
                      ? "bg-sidebar-accent font-semibold text-sidebar-foreground"
                      : "font-medium text-sidebar-foreground/58 hover:bg-sidebar-accent/65 hover:text-sidebar-foreground"
                  )}
                >
                  {active && !collapsed && (
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
                  {!collapsed && <span className="truncate">{item.label}</span>}
                </Link>
              )

              if (collapsed) {
                return (
                  <Tooltip key={item.href}>
                    <TooltipTrigger render={<span className="flex justify-center" />}>
                      {link}
                    </TooltipTrigger>
                    <TooltipContent side="right" sideOffset={8}>
                      {item.label}
                    </TooltipContent>
                  </Tooltip>
                )
              }

              return <span key={item.href}>{link}</span>
            })}
          </div>
        </div>
      </ScrollArea>

      {/* ── Collapse / expand toggle ── */}
      <div
        className={cn(
          "shrink-0 border-t border-sidebar-border/30 px-2 py-1.5",
          collapsed ? "flex justify-center" : "flex justify-end"
        )}
      >
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
