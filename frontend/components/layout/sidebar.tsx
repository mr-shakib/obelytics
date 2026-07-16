"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { usePathname, useRouter } from "next/navigation"
import { Bot, CircleDot, ChevronLeft, ChevronRight, ChevronDown, Settings } from "lucide-react"
import { useQueryClient } from "@tanstack/react-query"
import type { QueryClient } from "@tanstack/react-query"
import { cn } from "@/lib/utils"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { useAppStore } from "@/lib/stores/app-store"
import { useAuthStore } from "@/lib/stores/auth-store"
import { usePermissions } from "@/hooks/use-permission"
import { prefetchRoute } from "@/lib/prefetch"
import {
  NAV_GROUPS,
  NAV_GROUP_META,
  isNavItemActive,
  isSectionTeacherView,
  getActiveNavGroup,
  getVisibleNavItems,
  type NavGroup,
  type NavItem,
} from "@/lib/navigation"

function NavItemLink({
  item,
  active,
  qc,
  onNavigate,
  className,
}: {
  item: NavItem
  active: boolean
  qc: QueryClient
  onNavigate?: () => void
  className?: string
}) {
  return (
    <Link
      href={item.href}
      onMouseEnter={() => prefetchRoute(qc, item.href)}
      onClick={onNavigate}
      aria-current={active ? "page" : undefined}
      className={cn(
        "group relative flex h-8 items-center gap-2.5 rounded-lg px-2.5 text-[12.5px]",
        "transition-all duration-150 [&>svg]:size-[14px] [&>svg]:shrink-0",
        active
          ? "bg-sidebar-accent font-semibold text-sidebar-foreground"
          : "font-medium text-sidebar-foreground/58 hover:bg-sidebar-accent/65 hover:text-sidebar-foreground",
        className
      )}
    >
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
}

function GroupSection({
  group,
  items,
  collapsed,
  expanded,
  onToggle,
  pathname,
  qc,
}: {
  group: NavGroup
  items: NavItem[]
  collapsed: boolean
  expanded: boolean
  onToggle: () => void
  pathname: string
  qc: QueryClient
}) {
  const [flyoutOpen, setFlyoutOpen] = useState(false)
  const meta = NAV_GROUP_META[group]
  const Icon = meta.icon
  const containsActive = items.some((item) => isNavItemActive(item, pathname))

  // The flyout is for quick hover navigation — suppress it when the group's
  // items are already visible inline right below the header.
  const showFlyout = flyoutOpen && (collapsed || !expanded)

  return (
    <div>
      <Popover
        open={showFlyout}
        onOpenChange={(open, eventDetails) => {
          if (!open) {
            setFlyoutOpen(false)
            return
          }
          // Open on hover always; on click only in collapsed mode (in expanded
          // mode a click means "toggle the inline accordion", handled below).
          if (eventDetails.reason === "trigger-hover" || collapsed) {
            setFlyoutOpen(true)
          }
        }}
      >
        <PopoverTrigger
          openOnHover
          delay={150}
          closeDelay={120}
          onClick={() => {
            if (!collapsed) {
              setFlyoutOpen(false)
              onToggle()
            }
          }}
          className={cn(
            "group relative flex h-9 items-center rounded-lg text-[13px] outline-none",
            "transition-all duration-150",
            collapsed ? "w-10 justify-center" : "w-full gap-2.5 px-2.5",
            containsActive && !expanded
              ? "font-semibold text-sidebar-foreground"
              : "font-medium text-sidebar-foreground/58",
            "hover:bg-sidebar-accent/65 hover:text-sidebar-foreground",
            collapsed && "mx-auto"
          )}
        >
          {containsActive && !expanded && !collapsed && (
            <span className="absolute left-0 top-1/2 h-5 w-[3px] -translate-y-1/2 rounded-r-full bg-sidebar-primary" />
          )}
          <Icon
            className={cn(
              "size-[15px] shrink-0 transition-colors",
              containsActive
                ? "text-sidebar-primary"
                : "text-sidebar-foreground/38 group-hover:text-sidebar-primary/70"
            )}
          />
          {!collapsed && (
            <>
              <span className="flex-1 truncate text-left">{meta.label}</span>
              <ChevronDown
                className={cn(
                  "size-3.5 shrink-0 text-sidebar-foreground/30 transition-transform duration-200",
                  expanded && "rotate-180"
                )}
              />
            </>
          )}
        </PopoverTrigger>

        <PopoverContent
          side="right"
          align="start"
          sideOffset={10}
          className="w-56 gap-0 p-1.5"
        >
          <p className="mb-1 px-2 pt-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-muted-foreground/70">
            {meta.label}
          </p>
          <div className="space-y-0.5">
            {items.map((item) => (
              <NavItemLink
                key={item.href}
                item={item}
                active={isNavItemActive(item, pathname)}
                qc={qc}
                onNavigate={() => setFlyoutOpen(false)}
              />
            ))}
          </div>
        </PopoverContent>
      </Popover>

      {/* Inline accordion items */}
      {!collapsed && expanded && (
        <div className="animate-in fade-in slide-in-from-top-1 mt-0.5 space-y-0.5 duration-150">
          <div className="ml-[19px] space-y-0.5 border-l border-sidebar-border/60 pl-2">
            {items.map((item) => (
              <NavItemLink
                key={item.href}
                item={item}
                active={isNavItemActive(item, pathname)}
                qc={qc}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export function Sidebar() {
  const pathname = usePathname()
  const router = useRouter()
  const qc = useQueryClient()
  const collapsed = useAppStore((s) => s.sidebarCollapsed)
  const toggleSidebar = useAppStore((s) => s.toggleSidebar)
  const { user } = useAuthStore()
  const permissions = usePermissions()

  const visibleItems = getVisibleNavItems(permissions)
  const visibleHrefs = visibleItems.map((item) => item.href).join("|")
  const homeHref = isSectionTeacherView(permissions) ? "/my-sections" : "/overview"
  const activeGroup = getActiveNavGroup(pathname, visibleItems)

  // Single-open accordion; the group containing the current page opens
  // automatically on navigation, and clicking a header toggles it manually.
  const [expandedGroup, setExpandedGroup] = useState<NavGroup | null>(activeGroup)
  const [prevActiveGroup, setPrevActiveGroup] = useState(activeGroup)
  if (prevActiveGroup !== activeGroup) {
    setPrevActiveGroup(activeGroup)
    setExpandedGroup(activeGroup)
  }

  const groups = NAV_GROUPS
    .map((group) => ({
      group,
      items: visibleItems.filter((item) => item.group === group),
    }))
    .filter(({ items }) => items.length > 0)

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

  useEffect(() => {
    for (const href of visibleHrefs.split("|")) {
      if (href) router.prefetch(href)
    }
  }, [router, visibleHrefs])

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

      {/* ── Grouped navigation ── */}
      <ScrollArea className="min-h-0 flex-1">
        <div className={cn("space-y-0.5 py-3", collapsed ? "px-2" : "px-2.5")}>
          {groups.map(({ group, items }) => (
            group === "Copilot" ? (
              collapsed ? (
                <Tooltip key={group}>
                  <TooltipTrigger render={<span className="flex justify-center" />}>
                    <Link
                      href={items[0].href}
                      aria-current={isNavItemActive(items[0], pathname) ? "page" : undefined}
                      className={cn(
                        "flex size-10 items-center justify-center rounded-lg transition-colors",
                        isNavItemActive(items[0], pathname)
                          ? "bg-sidebar-accent text-sidebar-primary"
                          : "text-sidebar-foreground/38 hover:bg-sidebar-accent/65 hover:text-sidebar-primary/70"
                      )}
                    >
                      <Bot className="size-[15px]" />
                    </Link>
                  </TooltipTrigger>
                  <TooltipContent side="right" sideOffset={8}>OBE Copilot</TooltipContent>
                </Tooltip>
              ) : (
                <NavItemLink
                  key={group}
                  item={items[0]}
                  active={isNavItemActive(items[0], pathname)}
                  qc={qc}
                  className="h-9 text-[13px]"
                />
              )
            ) : (
              <GroupSection
                key={group}
                group={group}
                items={items}
                collapsed={collapsed}
                expanded={expandedGroup === group}
                onToggle={() =>
                  setExpandedGroup((current) => (current === group ? null : group))
                }
                pathname={pathname}
                qc={qc}
              />
            )
          ))}
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
