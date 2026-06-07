"use client"

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { Loader2, ArrowLeft, Check } from "lucide-react"
import Link from "next/link"
import { useState } from "react"
import { PageHeader } from "@/components/shared/page-header"
import { PermissionGate } from "@/components/shared/permission-gate"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { cn } from "@/lib/utils"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"

type Permission = { code: string; description?: string; module: string }
type RoleDetail = {
  id: string
  name: string
  description?: string
  is_system: boolean
  permissions: string[]
}

interface Props {
  id: string
}

function groupByModule(permissions: Permission[]) {
  const groups: Record<string, Permission[]> = {}
  for (const p of permissions) {
    if (!groups[p.module]) groups[p.module] = []
    groups[p.module].push(p)
  }
  return groups
}

export function RoleDetailClient({ id }: Props) {
  const qc = useQueryClient()
  const [search, setSearch] = useState("")
  const [saving, setSaving] = useState(false)
  const [localPerms, setLocalPerms] = useState<Set<string> | null>(null)

  const { data: role, isLoading: roleLoading } = useQuery({
    queryKey: queryKeys.roles.detail(id),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/roles/${id}` as never)
      return (data as unknown) as RoleDetail
    },
  })

  const { data: allPermissions, isLoading: permsLoading } = useQuery({
    queryKey: ["all-permissions"],
    queryFn: async () => {
      const { data } = await apiClient.GET("/permissions" as never)
      return ((data as unknown) as { items?: Permission[] })?.items ?? ((data as unknown) as Permission[]) ?? []
    },
  })

  const saveMutation = useMutation({
    mutationFn: async (permCodes: string[]) => {
      await apiClient.PUT(`/roles/${id}/permissions` as never, {
        body: { permissions: permCodes },
      } as never)
    },
    onSuccess: () => {
      toast.success("Permissions updated")
      qc.invalidateQueries({ queryKey: queryKeys.roles.detail(id) })
      setLocalPerms(null)
    },
    onError: () => toast.error("Failed to update permissions"),
    onSettled: () => setSaving(false),
  })

  const effectivePerms = localPerms ?? new Set(role?.permissions ?? [])

  function togglePerm(code: string) {
    const next = new Set(effectivePerms)
    if (next.has(code)) {
      next.delete(code)
    } else {
      next.add(code)
    }
    setLocalPerms(next)
  }

  const isDirty = localPerms !== null

  const filtered = (allPermissions ?? []).filter(
    (p) => !search || p.code.includes(search) || (p.description ?? "").toLowerCase().includes(search.toLowerCase())
  )
  const groups = groupByModule(filtered)

  if (roleLoading) return <div className="animate-pulse h-40 bg-muted rounded-md" />
  if (!role) return <p className="text-muted-foreground">Role not found.</p>

  return (
    <div className="space-y-6">
      <PageHeader
        title={role.name}
        description={role.description ?? (role.is_system ? "System role — permissions can be viewed but not modified." : "")}
        actions={
          <div className="flex items-center gap-2">
            {role.is_system && <Badge variant="secondary">System</Badge>}
            <Button variant="outline" size="sm" render={<Link href="/roles" />}>
              <ArrowLeft /> Roles
            </Button>
            {isDirty && !role.is_system && (
              <PermissionGate permission="roles.manage">
                <Button
                  size="sm"
                  onClick={() => {
                    setSaving(true)
                    saveMutation.mutate(Array.from(effectivePerms))
                  }}
                  disabled={saveMutation.isPending}
                >
                  {saveMutation.isPending ? <Loader2 className="animate-spin" /> : <Check />}
                  Save Permissions
                </Button>
              </PermissionGate>
            )}
          </div>
        }
      />

      <Input
        placeholder="Filter permissions..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="max-w-xs"
      />

      {permsLoading && (
        <div className="space-y-2">
          {[...Array(5)].map((_, i) => <div key={i} className="h-10 bg-muted animate-pulse rounded-md" />)}
        </div>
      )}

      <div className="space-y-6">
        {Object.entries(groups).map(([module, perms]) => (
          <Card key={module}>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm capitalize">{module.replace(/_/g, " ")}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-1">
                {perms.map((perm) => {
                  const checked = effectivePerms.has(perm.code)
                  return (
                    <div
                      key={perm.code}
                      className={cn(
                        "flex items-center gap-3 p-2 rounded-md text-sm",
                        !role.is_system && "cursor-pointer hover:bg-muted/50",
                        checked && "bg-primary/5"
                      )}
                      onClick={() => !role.is_system && togglePerm(perm.code)}
                    >
                      <div className={cn(
                        "w-4 h-4 rounded border flex items-center justify-center shrink-0",
                        checked ? "bg-primary border-primary" : "border-input"
                      )}>
                        {checked && <Check className="h-3 w-3 text-primary-foreground" />}
                      </div>
                      <span className="font-mono text-xs text-muted-foreground">{perm.code}</span>
                      {perm.description && (
                        <span className="text-muted-foreground text-xs">{perm.description}</span>
                      )}
                    </div>
                  )
                })}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
