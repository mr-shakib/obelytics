"use client"

import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { Loader2, Plus, ShieldCheck } from "lucide-react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogTrigger,
} from "@/components/ui/dialog"
import { PageHeader } from "@/components/shared/page-header"
import { StatusBadge } from "@/components/shared/status-badge"
import { PermissionGate } from "@/components/shared/permission-gate"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"

type UserDetail = {
  id: string
  first_name: string
  last_name: string
  email: string
  faculty_type: string
  department_name?: string
  status: string
}

type UserRole = {
  id: string
  role_id: string
  role_name: string
  scope_type: string
  scope_id?: string
  scope_name?: string
}

type Role = { id: string; name: string }
type Department = { id: string; name: string }
type Program = { id: string; name: string }

const SCOPE_TYPES = ["GLOBAL", "DEPARTMENT", "PROGRAM"] as const

const roleSchema = z.object({
  role_id: z.string().min(1, "Role required"),
  scope_type: z.enum(SCOPE_TYPES),
  scope_id: z.string().optional(),
})
type RoleFormValues = z.infer<typeof roleSchema>

interface Props {
  id: string
}

export function UserDetailClient({ id }: Props) {
  const [roleDialogOpen, setRoleDialogOpen] = useState(false)
  const [scopeType, setScopeType] = useState<typeof SCOPE_TYPES[number]>("GLOBAL")
  const [selectedRoleId, setSelectedRoleId] = useState("")
  const [selectedScopeId, setSelectedScopeId] = useState("")
  const qc = useQueryClient()

  const { data: user, isLoading } = useQuery({
    queryKey: queryKeys.users.detail(id),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/users/${id}` as never)
      return (data as unknown) as UserDetail
    },
  })

  const { data: userRoles, isLoading: rolesLoading } = useQuery({
    queryKey: queryKeys.users.roles(id),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/users/${id}/roles` as never)
      return ((data as unknown) as UserRole[]) ?? []
    },
  })

  const { data: roles } = useQuery({
    queryKey: queryKeys.roles.list(),
    queryFn: async () => {
      const { data } = await apiClient.GET("/roles" as never)
      return ((data as unknown) as { items?: Role[] })?.items ?? ((data as unknown) as Role[]) ?? []
    },
    enabled: roleDialogOpen,
  })

  const { data: departments } = useQuery({
    queryKey: queryKeys.departments.list(),
    queryFn: async () => {
      const { data } = await apiClient.GET("/departments" as never)
      return ((data as unknown) as { items?: Department[] })?.items ?? ((data as unknown) as Department[]) ?? []
    },
    enabled: roleDialogOpen && scopeType === "DEPARTMENT",
  })

  const { data: programs } = useQuery({
    queryKey: queryKeys.programs.list(),
    queryFn: async () => {
      const { data } = await apiClient.GET("/programs" as never)
      return ((data as unknown) as { items?: Program[] })?.items ?? ((data as unknown) as Program[]) ?? []
    },
    enabled: roleDialogOpen && scopeType === "PROGRAM",
  })

  const toggleStatus = useMutation({
    mutationFn: async () => {
      const action = user?.status === "ACTIVE" ? "deactivate" : "activate"
      await apiClient.POST(`/users/${id}/${action}` as never, {} as never)
    },
    onSuccess: () => {
      toast.success("User status updated")
      qc.invalidateQueries({ queryKey: queryKeys.users.detail(id) })
      qc.invalidateQueries({ queryKey: queryKeys.users.all })
    },
    onError: () => toast.error("Failed to update user status"),
  })

  const {
    handleSubmit,
    setValue,
    reset: resetRoleForm,
    formState: { errors, isSubmitting },
  } = useForm<RoleFormValues>({
    resolver: zodResolver(roleSchema),
    defaultValues: { scope_type: "GLOBAL" },
  })

  const addRole = useMutation({
    mutationFn: async (values: RoleFormValues) => {
      await apiClient.POST(`/users/${id}/roles` as never, { body: values } as never)
    },
    onSuccess: () => {
      toast.success("Role assigned")
      qc.invalidateQueries({ queryKey: queryKeys.users.roles(id) })
      resetRoleForm()
      setSelectedRoleId("")
      setScopeType("GLOBAL")
      setSelectedScopeId("")
      setRoleDialogOpen(false)
    },
    onError: () => toast.error("Failed to assign role"),
  })

  if (isLoading) return <div className="animate-pulse h-40 bg-muted rounded-md" />
  if (!user) return <p className="text-muted-foreground">User not found.</p>

  return (
    <div className="max-w-3xl space-y-6">
      <PageHeader
        title={`${user.first_name} ${user.last_name}`}
        description={user.email}
        actions={
          <PermissionGate permission="user.deactivate">
            <Button
              variant={user.status === "ACTIVE" ? "destructive" : "outline"}
              size="sm"
              onClick={() => toggleStatus.mutate()}
              disabled={toggleStatus.isPending}
            >
              {toggleStatus.isPending && <Loader2 className="animate-spin" />}
              {user.status === "ACTIVE" ? "Deactivate" : "Activate"}
            </Button>
          </PermissionGate>
        }
      />

      <Card>
        <CardHeader>
          <CardTitle>Profile</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <div className="flex gap-2">
            <span className="text-muted-foreground w-32">Faculty Type</span>
            <span>{user.faculty_type}</span>
          </div>
          <div className="flex gap-2">
            <span className="text-muted-foreground w-32">Department</span>
            <span>{user.department_name ?? "—"}</span>
          </div>
          <div className="flex gap-2">
            <span className="text-muted-foreground w-32">Status</span>
            <StatusBadge status={user.status} />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Roles</CardTitle>
          <PermissionGate permission="user.update">
            <Dialog open={roleDialogOpen} onOpenChange={setRoleDialogOpen}>
              <DialogTrigger
                render={
                  <Button size="sm" variant="outline">
                    <Plus />
                    Assign Role
                  </Button>
                }
              />
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Assign Role</DialogTitle>
                </DialogHeader>
                <form
                  id="assign-role-form"
                  onSubmit={handleSubmit((v) => addRole.mutate(v))}
                  className="space-y-4 py-2"
                >
                  <div className="space-y-2">
                    <Label>Role</Label>
                    <Select
                      value={selectedRoleId}
                      onValueChange={(v) => {
                        if (v == null) return
                        setSelectedRoleId(v as string)
                        setValue("role_id", v as string, { shouldValidate: true })
                      }}
                    >
                      <SelectTrigger className="w-full">
                        <SelectValue placeholder="Select role" />
                      </SelectTrigger>
                      <SelectContent>
                        {(roles ?? []).map((r) => (
                          <SelectItem key={r.id} value={r.id}>
                            {r.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {errors.role_id && (
                      <p className="text-sm text-destructive">{errors.role_id.message}</p>
                    )}
                  </div>
                  <div className="space-y-2">
                    <Label>Scope Type</Label>
                    <Select
                      value={scopeType}
                      onValueChange={(v) => {
                        if (v == null) return
                        const val = v as typeof SCOPE_TYPES[number]
                        setScopeType(val)
                        setValue("scope_type", val, { shouldValidate: true })
                        setSelectedScopeId("")
                        setValue("scope_id", undefined)
                      }}
                    >
                      <SelectTrigger className="w-full">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {SCOPE_TYPES.map((s) => (
                          <SelectItem key={s} value={s}>
                            {s}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  {scopeType === "DEPARTMENT" && (
                    <div className="space-y-2">
                      <Label>Department</Label>
                      <Select
                        value={selectedScopeId}
                        onValueChange={(v) => {
                          setSelectedScopeId((v as string | null) ?? "")
                          setValue("scope_id", (v as string | null) ?? undefined)
                        }}
                      >
                        <SelectTrigger className="w-full">
                          <SelectValue placeholder="Select department" />
                        </SelectTrigger>
                        <SelectContent>
                          {(departments ?? []).map((d) => (
                            <SelectItem key={d.id} value={d.id}>
                              {d.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  )}
                  {scopeType === "PROGRAM" && (
                    <div className="space-y-2">
                      <Label>Program</Label>
                      <Select
                        value={selectedScopeId}
                        onValueChange={(v) => {
                          setSelectedScopeId((v as string | null) ?? "")
                          setValue("scope_id", (v as string | null) ?? undefined)
                        }}
                      >
                        <SelectTrigger className="w-full">
                          <SelectValue placeholder="Select program" />
                        </SelectTrigger>
                        <SelectContent>
                          {(programs ?? []).map((p) => (
                            <SelectItem key={p.id} value={p.id}>
                              {p.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  )}
                </form>
                <DialogFooter showCloseButton>
                  <Button
                    type="submit"
                    form="assign-role-form"
                    disabled={isSubmitting || addRole.isPending}
                  >
                    {(isSubmitting || addRole.isPending) && <Loader2 className="animate-spin" />}
                    Assign
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </PermissionGate>
        </CardHeader>
        <CardContent>
          {rolesLoading ? (
            <div className="animate-pulse h-10 bg-muted rounded-md" />
          ) : (userRoles ?? []).length === 0 ? (
            <p className="text-sm text-muted-foreground">No roles assigned.</p>
          ) : (
            <ul className="space-y-2">
              {(userRoles ?? []).map((r) => (
                <li key={r.id} className="flex items-center gap-2 text-sm">
                  <ShieldCheck className="h-4 w-4 text-muted-foreground shrink-0" />
                  <span className="font-medium">{r.role_name}</span>
                  <Badge variant="secondary" className="text-xs">
                    {r.scope_type}
                  </Badge>
                  {r.scope_name && (
                    <span className="text-muted-foreground">{r.scope_name}</span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
