"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import {
  ChevronLeft,
  ChevronRight,
  CircleDot,
  PanelLeftOpen,
  Settings,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { useAppStore } from "@/lib/stores/app-store"
import { useAuthStore } from "@/lib/stores/auth-store"
import { usePermissions } from "@/hooks/use-permission"
import { NAV_ITEMS, NAV_GROUPS, type NavItem } from "@/lib/navigation"

function canView(item: NavItem, permissions: string[]) {
  return item.permission === null || permissions.includes(item.permission)
}

function isItemActive(item: NavItem, pathname: string) {
  return item.href === "/overview"
    ? pathname === "/overview" || pathname === "/"
    : pathname === item.href || pathname.startsWith(item.href + "/")
}

function SidebarTooltip({
  collapsed,
  label,
  children,
}: {
  collapsed: boolean
  label: string
  children: React.ReactNode
}) {
  if (!collapsed) return children

  return (
    <Tooltip>
      <TooltipTrigger render={<span />} className="flex w-full">
        {children}
      </TooltipTrigger>
      <TooltipContent side="right" sideOffset={10}>
        {label}
      </TooltipContent>
    </Tooltip>
  )
}

function NavigationItem({
  item,
  collapsed,
  active,
}: {
  item: NavItem
  collapsed: boolean
  active: boolean
}) {
  const btn = (
    <Link
      href={item.href}
      aria-current={active ? "page" : undefined}
      className={cn(
        "group/nav relative flex h-10 w-full items-center gap-2.5 overflow-hidden rounded-md px-2.5 text-[14px]",
        "transition-[background,color,box-shadow,transform] duration-150 ease-out",
        "[&>svg]:size-[17px] [&>svg]:shrink-0 [&>span]:truncate",
        collapsed && "mx-auto size-10 justify-center px-0",
        active
          ? "bg-sidebar-accent text-sidebar-foreground"
          : "text-sidebar-foreground/72 hover:bg-sidebar-accent/75 hover:text-sidebar-foreground"
      )}
    >
      <span
        className={cn(
          "-left-2 absolute top-1/2 h-7 w-1.5 -translate-y-1/2 rounded-full bg-sidebar-primary opacity-0 transition-opacity",
          active && !collapsed && "opacity-100"
        )}
      />
      <item.icon
        className={cn(
          "transition-colors",
          active ? "text-sidebar-primary" : "text-sidebar-foreground/58 group-hover/nav:text-sidebar-primary"
        )}
      />
      {!collapsed && <span className={cn("min-w-0", active ? "font-semibold" : "font-medium")}>{item.label}</span>}
    </Link>
  )

  return (
    <SidebarTooltip collapsed={collapsed} label={item.label}>
      {btn}
    </SidebarTooltip>
  )
}

function SidebarToggle({
  collapsed,
  onToggle,
}: {
  collapsed: boolean
  onToggle: () => void
}) {
  return (
    <button
      type="button"
      onClick={onToggle}
      aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
      className={cn(
        "flex size-8 shrink-0 items-center justify-center rounded-md text-sidebar-foreground/62",
        "transition-colors hover:bg-sidebar-accent hover:text-sidebar-foreground focus-visible:ring-2 focus-visible:ring-sidebar-ring",
        collapsed && "group-hover/sidebar:bg-sidebar-accent"
      )}
    >
      {collapsed ? <ChevronRight className="size-4" /> : <ChevronLeft className="size-4" />}
    </button>
  )
}

export function Sidebar() {
  const pathname = usePathname()
  const collapsed = useAppStore((s) => s.sidebarCollapsed)
  const toggleSidebar = useAppStore((s) => s.toggleSidebar)
  const { user } = useAuthStore()
  const permissions = usePermissions()

  const displayName =
    user?.full_name ?? `${user?.first_name ?? ""} ${user?.last_name ?? ""}`.trim() ?? "User"
  const initials =
    displayName
      .split(" ")
      .map((w) => w[0] ?? "")
      .slice(0, 2)
      .join("")
      .toUpperCase() || "U"
  const roleLabel = user?.email ?? "Account settings"
  const visibleItems = NAV_ITEMS.filter((item) => canView(item, permissions))

  return (
    <aside
      className={cn(
        "group/sidebar relative m-3 flex h-[calc(100dvh-1.5rem)] shrink-0 flex-col overflow-hidden rounded-[22px] border border-sidebar-border bg-sidebar shadow-sm",
        "transition-[width] duration-200 ease-out",
        collapsed ? "w-[68px]" : "w-[232px]"
      )}
    >
      <div className={cn("relative flex h-[76px] shrink-0 items-center px-4", collapsed ? "justify-center" : "gap-3")}>
        {!collapsed && (
          <Link
            href="/overview"
            className="flex min-w-0 flex-1 items-center gap-3 rounded-md p-1 transition-colors hover:bg-sidebar-accent"
          >
            <div className="flex size-8 shrink-0 items-center justify-center rounded-full border-2 border-sidebar-primary text-sidebar-primary">
              <CircleDot className="size-4" />
            </div>
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold leading-tight text-sidebar-foreground">
                Obelytics
              </p>
            </div>
          </Link>
        )}

        {collapsed && (
          <SidebarTooltip collapsed label="Obelytics">
            <Link
              href="/overview"
              className="flex size-9 items-center justify-center rounded-full border-2 border-sidebar-primary text-sidebar-primary"
            >
              <CircleDot className="size-4" />
            </Link>
          </SidebarTooltip>
        )}

        {!collapsed && <SidebarToggle collapsed={collapsed} onToggle={toggleSidebar} />}
      </div>

      {collapsed && (
        <div className="relative flex justify-center px-3 pb-3">
          <SidebarToggle collapsed={collapsed} onToggle={toggleSidebar} />
        </div>
      )}

      <ScrollArea className="relative flex-1">
        <nav className={cn("pb-4", collapsed ? "space-y-2 px-2" : "space-y-5 px-5")}>
          {NAV_GROUPS.map((group) => {
            const items = visibleItems.filter((item) => item.group === group)
            if (items.length === 0) return null

            return (
              <section key={group} className={cn(collapsed ? "space-y-1.5" : "space-y-1.5")}>
                {!collapsed && (
                  <div className="px-2 pb-1">
                    <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-sidebar-foreground/52">
                      {group}
                    </p>
                  </div>
                )}

                <div className="space-y-1">
                  {items.map((item) => (
                    <NavigationItem
                      key={item.href}
                      item={item}
                      collapsed={collapsed}
                      active={isItemActive(item, pathname)}
                    />
                  ))}
                </div>
              </section>
            )
          })}
        </nav>
      </ScrollArea>

      <div className="relative shrink-0 p-4">
        <SidebarTooltip collapsed={collapsed} label={displayName}>
          <Link
            href="/profile"
            className={cn(
              "flex w-full items-center gap-2 rounded-md transition-colors hover:bg-sidebar-accent",
              collapsed ? "size-9 justify-center p-0" : "p-2"
            )}
          >
            <Avatar size="sm" className="size-8 rounded-full">
              <AvatarFallback className="rounded-full bg-sidebar-primary text-[11px] font-bold text-sidebar-primary-foreground">
                {initials}
              </AvatarFallback>
            </Avatar>
            {!collapsed && (
              <>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-[13px] font-semibold leading-tight text-sidebar-foreground">
                    {displayName}
                  </p>
                  <p className="truncate text-[11px] leading-tight text-sidebar-foreground/40">
                    {roleLabel}
                  </p>
                </div>
                <Settings className="size-4 shrink-0 text-sidebar-foreground/34" />
              </>
            )}
          </Link>
        </SidebarTooltip>
      </div>

      <button
        type="button"
        aria-label="Toggle sidebar"
        onClick={toggleSidebar}
        className="absolute inset-y-0 right-0 w-1 cursor-col-resize opacity-0 transition-opacity hover:bg-sidebar-foreground/20 hover:opacity-100"
      >
        <PanelLeftOpen className="sr-only" />
      </button>
    </aside>
  )
}
