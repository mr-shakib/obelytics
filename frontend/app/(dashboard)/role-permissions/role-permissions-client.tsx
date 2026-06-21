"use client"

import { useMemo, useState } from "react"
import { useQuery, useMutation } from "@tanstack/react-query"
import { toast } from "sonner"
import { Loader2, Save, Shield, Check, Lock, Info } from "lucide-react"
import { cn } from "@/lib/utils"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"
import { PageHeader } from "@/components/shared/page-header"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"

// ── Types ─────────────────────────────────────────────────────────────────────

type Permission = {
  id: string
  code: string
  description: string | null
  module: string
  tier: string
}

type RoleWithPerms = {
  id: string
  name: string
  description: string | null
  is_system_role: boolean
  permission_codes: string[]
}

// ── Module display names (ordered) ────────────────────────────────────────────

const MODULE_ORDER: { key: string; label: string }[] = [
  { key: "org",           label: "Organization" },
  { key: "iam",           label: "IAM / Users" },
  { key: "ref_data",      label: "Reference Data" },
  { key: "audit",         label: "Audit" },
  { key: "curriculum",    label: "Curriculum" },
  { key: "obe",           label: "OBE" },
  { key: "assessment",    label: "Assessment" },
  { key: "attainment",    label: "Attainment" },
  { key: "reporting",     label: "Reporting" },
  { key: "accreditation", label: "Accreditation" },
  { key: "approval",      label: "Approvals" },
  { key: "notification",  label: "Notifications" },
]

const LOCKED_ROLES = ["Super Admin"]

// ── Checkbox cell ─────────────────────────────────────────────────────────────

function Cell({
  checked,
  indeterminate = false,
  locked = false,
  onChange,
}: {
  checked: boolean
  indeterminate?: boolean
  locked?: boolean
  onChange?: () => void
}) {
  if (locked) {
    return (
      <span className="flex items-center justify-center">
        <span className="flex size-5 items-center justify-center rounded bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
          <Check className="h-3 w-3" />
        </span>
      </span>
    )
  }

  return (
    <button
      type="button"
      role="checkbox"
      aria-checked={indeterminate ? "mixed" : checked}
      onClick={onChange}
      className={cn(
        "mx-auto flex size-5 items-center justify-center rounded border transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        checked || indeterminate
          ? "bg-primary border-primary text-primary-foreground"
          : "border-input bg-background hover:border-primary/50"
      )}
    >
      {indeterminate ? (
        <span className="block h-0.5 w-2.5 bg-current rounded-full" />
      ) : checked ? (
        <Check className="h-3 w-3" />
      ) : null}
    </button>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export function RolePermissionsClient() {
  // ── Remote data ─────────────────────────────────────────────────────────────

  const { data: roles = [], isLoading: rolesLoading } = useQuery({
    queryKey: queryKeys.roles.withPermissions,
    queryFn: async () => {
      const { data } = await apiClient.GET("/roles/with-permissions" as never)
      return ((data as unknown) as RoleWithPerms[]) ?? []
    },
  })

  const { data: allPerms = [], isLoading: permsLoading } = useQuery({
    queryKey: queryKeys.roles.allPermissions,
    queryFn: async () => {
      const { data } = await apiClient.GET("/roles/permissions/all" as never)
      return ((data as unknown) as Permission[]) ?? []
    },
  })

  // ── Local state: role_id → Set<permission_code> ──────────────────────────────

  const [draft, setDraft] = useState<Record<string, Set<string>>>({})
  const [dirty, setDirty] = useState<Set<string>>(new Set())
  const [initialized, setInitialized] = useState(false)

  // Seed draft from remote once roles are loaded
  const rolesKey = roles.map((r) => r.id).join(",")
  useMemo(() => {
    if (roles.length === 0) return
    const init: Record<string, Set<string>> = {}
    for (const role of roles) init[role.id] = new Set(role.permission_codes)
    setDraft(init)
    setDirty(new Set())
    setInitialized(true)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rolesKey])

  function isGranted(roleId: string, code: string) {
    return draft[roleId]?.has(code) ?? false
  }

  function toggle(roleId: string, code: string) {
    setDraft((prev) => {
      const next = new Set(prev[roleId] ?? [])
      if (next.has(code)) next.delete(code)
      else next.add(code)
      return { ...prev, [roleId]: next }
    })
    setDirty((prev) => new Set([...prev, roleId]))
  }

  function toggleModule(roleId: string, codes: string[], on: boolean) {
    setDraft((prev) => {
      const next = new Set(prev[roleId] ?? [])
      for (const c of codes) on ? next.add(c) : next.delete(c)
      return { ...prev, [roleId]: next }
    })
    setDirty((prev) => new Set([...prev, roleId]))
  }

  // ── Save ─────────────────────────────────────────────────────────────────────

  const saveMutation = useMutation({
    mutationFn: async () => {
      const permByCode: Record<string, string> = {}
      for (const p of allPerms) permByCode[p.code] = p.id

      await Promise.all(
        [...dirty].map((roleId) => {
          const ids = [...(draft[roleId] ?? [])].map((c) => permByCode[c]).filter(Boolean)
          return apiClient.PUT(`/roles/${roleId}/permissions` as never, {
            body: { permission_ids: ids },
          } as never)
        })
      )
    },
    onSuccess: () => {
      toast.success("Permissions saved")
      setDirty(new Set())
    },
    onError: () => toast.error("Failed to save permissions"),
  })

  // ── Grouped permissions ───────────────────────────────────────────────────

  const grouped = useMemo(() => {
    const map: Record<string, Permission[]> = {}
    for (const p of allPerms) {
      if (!map[p.module]) map[p.module] = []
      map[p.module].push(p)
    }
    return MODULE_ORDER.filter(({ key }) => map[key]?.length).map(({ key, label }) => ({
      key,
      label,
      perms: map[key],
    }))
  }, [allPerms])

  const lockedRoles   = roles.filter((r) => LOCKED_ROLES.includes(r.name))
  const editableRoles = roles.filter((r) => !LOCKED_ROLES.includes(r.name))
  const displayRoles  = [...lockedRoles, ...editableRoles]

  // ── Loading ───────────────────────────────────────────────────────────────

  if (rolesLoading || permsLoading || !initialized) {
    return (
      <div className="flex items-center gap-2 text-muted-foreground p-8">
        <Loader2 className="animate-spin h-4 w-4" />
        Loading permissions…
      </div>
    )
  }

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="space-y-4">
      <PageHeader
        title="Permission Management"
        description="Control which permissions each role has. Super Admin always retains all permissions."
        actions={
          dirty.size > 0 ? (
            <Button onClick={() => saveMutation.mutate()} disabled={saveMutation.isPending}>
              {saveMutation.isPending ? <Loader2 className="animate-spin" /> : <Save />}
              Save Changes
            </Button>
          ) : undefined
        }
      />

      {/* Legend */}
      <div className="flex flex-wrap items-center gap-4 text-xs text-muted-foreground border rounded-lg px-4 py-3 bg-muted/30">
        <span className="flex items-center gap-1.5 font-medium text-foreground">Legend:</span>
        <span className="flex items-center gap-1.5">
          <span className="flex size-4 items-center justify-center rounded border bg-primary text-primary-foreground">
            <Check className="h-2.5 w-2.5" />
          </span>
          Granted
        </span>
        <span className="flex items-center gap-1.5">
          <span className="flex size-4 items-center justify-center rounded border border-input" />
          Not granted
        </span>
        <span className="flex items-center gap-1.5">
          <span className="flex size-4 items-center justify-center rounded bg-amber-100 text-amber-700">
            <Check className="h-2.5 w-2.5" />
          </span>
          <Lock className="h-3 w-3 text-amber-500" />
          Always granted (locked)
        </span>
        {dirty.size > 0 && (
          <Badge variant="secondary" className="ml-auto">
            {dirty.size} role{dirty.size > 1 ? "s" : ""} with unsaved changes
          </Badge>
        )}
      </div>

      {/* Matrix table */}
      <div className="rounded-xl border overflow-x-auto">
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="bg-muted/50 border-b">
              <th className="sticky left-0 z-20 bg-muted/50 px-4 py-3 text-left font-medium min-w-[260px] border-r">
                Permission
              </th>
              {displayRoles.map((role) => {
                const locked = LOCKED_ROLES.includes(role.name)
                return (
                  <th key={role.id} className="px-3 py-3 text-center font-medium min-w-[120px] border-r last:border-r-0">
                    <div className="flex flex-col items-center gap-1">
                      <Shield className={cn("h-4 w-4", locked ? "text-amber-500" : "text-muted-foreground")} />
                      <span className="text-xs leading-snug">{role.name}</span>
                      {locked && (
                        <Tooltip>
                          <TooltipTrigger>
                            <Lock className="h-3 w-3 text-amber-500 cursor-help" />
                          </TooltipTrigger>
                          <TooltipContent>
                            Super Admin always has all permissions — cannot be restricted
                          </TooltipContent>
                        </Tooltip>
                      )}
                      {dirty.has(role.id) && (
                        <Badge variant="secondary" className="text-[10px] px-1 py-0">unsaved</Badge>
                      )}
                    </div>
                  </th>
                )
              })}
            </tr>
          </thead>

          <tbody>
            {grouped.map(({ key, label, perms }) => {
              const moduleCodes = perms.map((p) => p.code)

              return (
                <>
                  {/* Module header */}
                  <tr key={`hdr-${key}`} className="bg-muted/25 border-y">
                    <td
                      colSpan={displayRoles.length + 1}
                      className="sticky left-0 z-10 bg-muted/25 px-4 py-2 font-semibold text-xs uppercase tracking-widest text-muted-foreground"
                    >
                      {label}
                    </td>
                  </tr>

                  {/* Module bulk-toggle row */}
                  <tr key={`bulk-${key}`} className="border-b bg-muted/5">
                    <td className="sticky left-0 z-10 bg-muted/5 px-4 py-2 text-xs text-muted-foreground italic border-r">
                      Toggle all in {label}
                    </td>
                    {displayRoles.map((role) => {
                      const locked = LOCKED_ROLES.includes(role.name)
                      const allOn  = moduleCodes.every((c) => draft[role.id]?.has(c))
                      const someOn = moduleCodes.some((c) => draft[role.id]?.has(c))
                      return (
                        <td key={role.id} className="border-r last:border-r-0 text-center py-2">
                          <Cell
                            checked={allOn}
                            indeterminate={someOn && !allOn}
                            locked={locked}
                            onChange={() => toggleModule(role.id, moduleCodes, !allOn)}
                          />
                        </td>
                      )
                    })}
                  </tr>

                  {/* Permission rows */}
                  {perms.map((perm, i) => (
                    <tr
                      key={perm.id}
                      className={cn(
                        "border-b last:border-b-0 hover:bg-muted/10 transition-colors",
                        i % 2 !== 0 && "bg-muted/5"
                      )}
                    >
                      <td className="sticky left-0 z-10 bg-background px-4 py-2.5 border-r">
                        <div className="flex items-start gap-2">
                          <div className="flex-1 min-w-0">
                            <p className="font-mono text-xs font-medium truncate">{perm.code}</p>
                            {perm.description && (
                              <p className="text-xs text-muted-foreground truncate max-w-[200px]">
                                {perm.description}
                              </p>
                            )}
                          </div>
                          {perm.description && (
                            <Tooltip>
                              <TooltipTrigger>
                                <Info className="h-3.5 w-3.5 text-muted-foreground/50 shrink-0 mt-0.5 cursor-help" />
                              </TooltipTrigger>
                              <TooltipContent side="right">
                                {perm.description}
                              </TooltipContent>
                            </Tooltip>
                          )}
                        </div>
                      </td>

                      {displayRoles.map((role) => {
                        const locked  = LOCKED_ROLES.includes(role.name)
                        const granted = locked || isGranted(role.id, perm.code)
                        return (
                          <td key={role.id} className="border-r last:border-r-0 text-center py-2">
                            <Cell
                              checked={granted}
                              locked={locked}
                              onChange={() => toggle(role.id, perm.code)}
                            />
                          </td>
                        )
                      })}
                    </tr>
                  ))}
                </>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* Sticky save bar */}
      {dirty.size > 0 && (
        <div className="sticky bottom-4 flex justify-end pointer-events-none">
          <div className="flex items-center gap-3 rounded-xl border bg-background/95 backdrop-blur px-4 py-2.5 shadow-lg pointer-events-auto">
            <span className="text-sm text-muted-foreground">
              {dirty.size} role{dirty.size > 1 ? "s" : ""} modified
            </span>
            <Button size="sm" onClick={() => saveMutation.mutate()} disabled={saveMutation.isPending}>
              {saveMutation.isPending ? <Loader2 className="animate-spin" /> : <Save />}
              Save Changes
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
