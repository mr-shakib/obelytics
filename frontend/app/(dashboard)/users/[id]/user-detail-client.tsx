"use client"

import { useEffect, useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useRouter } from "next/navigation"
import { toast } from "sonner"
import { Loader2, Plus, ShieldCheck, KeyRound, Trash2 } from "lucide-react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
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
import { CredentialsDialog, genPassword, type Credentials } from "@/components/shared/credentials-dialog"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"
import { useAuthStore } from "@/lib/stores/auth-store"

type UserDetail = {
  id: string
  email: string
  full_name: string
  title: string | null
  first_name: string | null
  middle_name: string | null
  last_name: string | null
  faculty_type: string | null
  nid: string | null
  department_id: string | null
  designation: string | null
  contact_number: string | null
  qualification: string | null
  experience_years: number | null
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
type Program = { id: string; title: string; acronym: string | null }

const SCOPE_TYPES = ["GLOBAL", "DEPARTMENT", "PROGRAM"] as const

const roleSchema = z.object({
  role_id: z.string().min(1, "Role required"),
  scope_type: z.enum(SCOPE_TYPES),
  scope_id: z.string().optional(),
})
type RoleFormValues = z.infer<typeof roleSchema>

const FACULTY_TYPES = ["Faculty", "Administrative", "Management"] as const
const TITLES = ["Dr.", "Mr.", "Ms.", "Prof.", "Assoc. Prof."] as const
const DESIGNATIONS = [
  "Professor", "Associate Professor", "Assistant Professor",
  "Senior Lecturer", "Lecturer", "Head of Department",
  "Director", "Administrative Officer",
] as const

const editSchema = z.object({
  faculty_type: z.string().min(1, "Required"),
  title: z.string().optional(),
  first_name: z.string().min(1, "Required"),
  last_name: z.string().optional(),
  nid: z.string().optional(),
  department_id: z.string().optional(),
  designation: z.string().optional(),
  contact_number: z.string().optional(),
  qualification: z.string().optional(),
  experience_years: z.string().optional(),
})
type EditFormValues = z.infer<typeof editSchema>

function EditField({
  label, required, error, children,
}: { label: string; required?: boolean; error?: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <Label className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
        {label}{required && <span className="ml-0.5 text-destructive">*</span>}
      </Label>
      {children}
      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  )
}

interface Props {
  id: string
}

export function UserDetailClient({ id }: Props) {
  const [roleDialogOpen, setRoleDialogOpen] = useState(false)
  const [scopeType, setScopeType] = useState<typeof SCOPE_TYPES[number]>("GLOBAL")
  const [selectedRoleId, setSelectedRoleId] = useState("")
  const [selectedScopeId, setSelectedScopeId] = useState("")
  const qc = useQueryClient()
  const router = useRouter()
  const isGlobal = useAuthStore((s) => s.manifest?.scope.is_global ?? false)

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

  const deleteUser = useMutation({
    mutationFn: async () => {
      await apiClient.DELETE(`/users/${id}` as never, {} as never)
    },
    onSuccess: () => {
      toast.success("User deleted")
      qc.invalidateQueries({ queryKey: queryKeys.users.all })
      router.push("/users")
    },
    onError: () => toast.error("Failed to delete user"),
  })

  const [resetCreds, setResetCreds] = useState<Credentials | null>(null)
  const resetPassword = useMutation({
    mutationFn: async () => {
      if (!user) return
      const password = genPassword()
      await apiClient.POST(`/users/${id}/reset-password` as never, { body: { password } } as never)
      return { email: user.email, full_name: `${user.first_name} ${user.last_name}`.trim(), password }
    },
    onSuccess: (creds) => {
      if (creds) setResetCreds(creds)
    },
    onError: () => toast.error("Failed to reset password"),
  })

  const [selFacultyType, setSelFacultyType] = useState("")
  const [selTitle, setSelTitle] = useState("")
  const [selDeptId, setSelDeptId] = useState("")
  const [selDesignation, setSelDesignation] = useState("")

  useEffect(() => {
    if (!user) return
    setSelFacultyType(user.faculty_type ?? "")
    setSelTitle(user.title ?? "")
    setSelDeptId(user.department_id ?? "")
    setSelDesignation(user.designation ?? "")
  }, [user])

  const {
    register: registerEdit,
    handleSubmit: handleEditSubmit,
    setValue: setEditValue,
    formState: { errors: editErrors, isSubmitting: isEditSubmitting },
  } = useForm<EditFormValues>({
    resolver: zodResolver(editSchema),
    values: user ? {
      faculty_type: user.faculty_type ?? "",
      title: user.title ?? "",
      first_name: user.first_name ?? "",
      last_name: user.last_name ?? "",
      nid: user.nid ?? "",
      department_id: user.department_id ?? "",
      designation: user.designation ?? "",
      contact_number: user.contact_number ?? "",
      qualification: user.qualification ?? "",
      experience_years: user.experience_years != null ? String(user.experience_years) : "",
    } : undefined,
  })

  const updateUser = useMutation({
    mutationFn: async (values: EditFormValues) => {
      await apiClient.PATCH(`/users/${id}` as never, {
        body: {
          first_name: values.first_name,
          last_name: values.last_name || null,
          title: values.title || null,
          faculty_type: values.faculty_type || null,
          nid: values.nid || null,
          department_id: values.department_id || null,
          designation: values.designation || null,
          contact_number: values.contact_number || null,
          qualification: values.qualification || null,
          experience_years: values.experience_years ? parseInt(values.experience_years) : null,
        },
      } as never)
    },
    onSuccess: () => {
      toast.success("User updated")
      qc.invalidateQueries({ queryKey: queryKeys.users.detail(id) })
      qc.invalidateQueries({ queryKey: queryKeys.users.all })
    },
    onError: () => toast.error("Failed to update user"),
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

  const [removingRoleId, setRemovingRoleId] = useState<string | null>(null)

  const removeRole = useMutation({
    mutationFn: async (assignmentId: string) => {
      setRemovingRoleId(assignmentId)
      await apiClient.DELETE(`/users/${id}/roles/${assignmentId}` as never)
    },
    onSuccess: () => {
      toast.success("Role removed")
      qc.invalidateQueries({ queryKey: queryKeys.users.roles(id) })
    },
    onError: () => toast.error("Failed to remove role"),
    onSettled: () => setRemovingRoleId(null),
  })

  if (isLoading) return <div className="animate-pulse h-40 bg-muted rounded-md" />
  if (!user) return <p className="text-muted-foreground">User not found.</p>

  return (
    <div className="max-w-3xl space-y-6">
      <PageHeader
        title={`${user.first_name} ${user.last_name}`}
        description={user.email}
        actions={
          <div className="flex items-center gap-2">
            {isGlobal && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => resetPassword.mutate()}
                disabled={resetPassword.isPending}
              >
                {resetPassword.isPending
                  ? <Loader2 className="animate-spin" />
                  : <KeyRound className="h-4 w-4" />}
                Reset Password
              </Button>
            )}
            {isGlobal && (
              <Button
                variant={user.status === "ACTIVE" ? "outline" : "default"}
                size="sm"
                onClick={() => toggleStatus.mutate()}
                disabled={toggleStatus.isPending}
              >
                {toggleStatus.isPending && <Loader2 className="animate-spin" />}
                {user.status === "ACTIVE" ? "Deactivate" : "Activate"}
              </Button>
            )}
            {isGlobal && (
              <Button
                variant="destructive"
                size="sm"
                disabled={deleteUser.isPending}
                onClick={() => {
                  if (window.confirm(`Permanently delete ${user.full_name}? This cannot be undone.`))
                    deleteUser.mutate()
                }}
              >
                {deleteUser.isPending ? <Loader2 className="animate-spin" /> : <Trash2 className="h-4 w-4" />}
                Delete
              </Button>
            )}
          </div>
        }
      />

      <CredentialsDialog
        creds={resetCreds}
        onClose={() => setResetCreds(null)}
        title="Password Reset — Share New Credentials"
        description="The user's password has been reset. Copy or send the new password now — it cannot be retrieved later."
      />

      <Card>
        <CardHeader>
          <CardTitle>Profile</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleEditSubmit((v) => updateUser.mutate(v))} className="flex flex-col gap-5">
            <div className="grid grid-cols-2 gap-4">
              <EditField label="Faculty Type" required error={editErrors.faculty_type?.message}>
                <Select
                  value={selFacultyType}
                  onValueChange={(v) => { if (v == null) return; setSelFacultyType(v as string); setEditValue("faculty_type", v as string, { shouldValidate: true }) }}
                >
                  <SelectTrigger className="w-full"><SelectValue placeholder="Select type" /></SelectTrigger>
                  <SelectContent>{FACULTY_TYPES.map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}</SelectContent>
                </Select>
              </EditField>
              <EditField label="NID" error={editErrors.nid?.message}>
                <Input placeholder="National ID number" {...registerEdit("nid")} />
              </EditField>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <EditField label="Title">
                <Select
                  value={selTitle}
                  onValueChange={(v) => { if (v == null) return; setSelTitle(v as string); setEditValue("title", v as string) }}
                >
                  <SelectTrigger className="w-full"><SelectValue placeholder="Select title" /></SelectTrigger>
                  <SelectContent>{TITLES.map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}</SelectContent>
                </Select>
              </EditField>
              <EditField label="Department" error={editErrors.department_id?.message}>
                <Select
                  value={selDeptId}
                  onValueChange={(v) => { if (v == null) return; setSelDeptId(v as string); setEditValue("department_id", v as string) }}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Select department">
                      {selDeptId ? departments?.find((d) => d.id === selDeptId)?.name : undefined}
                    </SelectValue>
                  </SelectTrigger>
                  <SelectContent>{(departments ?? []).map((d) => <SelectItem key={d.id} value={d.id}>{d.name}</SelectItem>)}</SelectContent>
                </Select>
              </EditField>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <EditField label="First Name" required error={editErrors.first_name?.message}>
                <Input placeholder="First name" {...registerEdit("first_name")} />
              </EditField>
              <EditField label="Designation" error={editErrors.designation?.message}>
                <Select
                  value={selDesignation}
                  onValueChange={(v) => { if (v == null) return; setSelDesignation(v as string); setEditValue("designation", v as string) }}
                >
                  <SelectTrigger className="w-full"><SelectValue placeholder="Select designation" /></SelectTrigger>
                  <SelectContent>{DESIGNATIONS.map((d) => <SelectItem key={d} value={d}>{d}</SelectItem>)}</SelectContent>
                </Select>
              </EditField>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <EditField label="Highest Qualification" error={editErrors.qualification?.message}>
                <Input placeholder="e.g. PhD, MSc, MBA" {...registerEdit("qualification")} />
              </EditField>
              <EditField label="Experience (Years)" error={editErrors.experience_years?.message}>
                <Input type="number" min={0} max={99} placeholder="0" {...registerEdit("experience_years")} />
              </EditField>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <EditField label="Contact Number" error={editErrors.contact_number?.message}>
                <Input placeholder="+880 ..." {...registerEdit("contact_number")} />
              </EditField>
              <EditField label="Status">
                <div className="flex h-9 items-center"><StatusBadge status={user.status} /></div>
              </EditField>
            </div>

            <div className="flex justify-end gap-2 pt-1">
              <PermissionGate permission="user.update">
                <Button type="submit" disabled={isEditSubmitting || updateUser.isPending} className="px-8">
                  {(isEditSubmitting || updateUser.isPending) && <Loader2 className="h-4 w-4 animate-spin mr-1" />}
                  Save Changes
                </Button>
              </PermissionGate>
            </div>
          </form>
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
                        <SelectValue placeholder="Select role">
                          {selectedRoleId ? roles?.find((r) => r.id === selectedRoleId)?.name : undefined}
                        </SelectValue>
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
                          <SelectValue placeholder="Select department">
                            {selectedScopeId ? departments?.find((d) => d.id === selectedScopeId)?.name : undefined}
                          </SelectValue>
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
                          <SelectValue placeholder="Select program">
                            {selectedScopeId
                              ? (() => {
                                  const p = programs?.find((p) => p.id === selectedScopeId)
                                  return p ? (p.acronym ? `${p.acronym} — ${p.title}` : p.title) : undefined
                                })()
                              : undefined}
                          </SelectValue>
                        </SelectTrigger>
                        <SelectContent>
                          {(programs ?? []).map((p) => (
                            <SelectItem key={p.id} value={p.id}>
                              {p.acronym ? `${p.acronym} — ${p.title}` : p.title}
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
                <li key={r.id} className="flex items-center gap-2 text-sm group">
                  <ShieldCheck className="h-4 w-4 text-muted-foreground shrink-0" />
                  <span className="font-medium">{r.role_name}</span>
                  <Badge variant="secondary" className="text-xs">
                    {r.scope_type}
                  </Badge>
                  {r.scope_name && (
                    <span className="text-muted-foreground">{r.scope_name}</span>
                  )}
                  <PermissionGate permission="user.update">
                    <button
                      type="button"
                      className="ml-auto h-6 w-6 flex items-center justify-center rounded hover:bg-destructive/10 text-muted-foreground hover:text-destructive transition-colors opacity-0 group-hover:opacity-100 disabled:opacity-50"
                      disabled={removeRole.isPending && removingRoleId === r.id}
                      onClick={() => removeRole.mutate(r.id)}
                      aria-label={`Remove ${r.role_name} role`}
                    >
                      {removeRole.isPending && removingRoleId === r.id ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <Trash2 className="h-3.5 w-3.5" />
                      )}
                    </button>
                  </PermissionGate>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
