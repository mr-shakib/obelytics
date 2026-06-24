"use client"

import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Plus, Search, Upload, Trash2 } from "lucide-react"
import { useRouter } from "next/navigation"
import { toast } from "sonner"
import type { ColumnDef } from "@tanstack/react-table"
import { DataTable } from "@/components/shared/data-table"
import { PageHeader } from "@/components/shared/page-header"
import { StatusBadge } from "@/components/shared/status-badge"
import { PermissionGate } from "@/components/shared/permission-gate"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"

import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"

// ── Types ──────────────────────────────────────────────────────────────────────

type User = {
  id: string
  full_name: string
  first_name: string | null
  last_name: string | null
  email: string
  employee_id: string | null
  faculty_type: string | null
  department_id: string | null
  designation: string | null
  status: string
}

type Department = { id: string; name: string; short_name: string }


// ── Main Page ─────────────────────────────────────────────────────────────────

export function UsersClient() {
  const router = useRouter()
  const qc = useQueryClient()
  const [search, setSearch] = useState("")
  const [deptFilter, setDeptFilter] = useState("__all__")
  const [deleteTarget, setDeleteTarget] = useState<User | null>(null)

  const { data: users = [], isLoading } = useQuery({
    queryKey: queryKeys.users.list(),
    queryFn: async () => {
      const { data } = await apiClient.GET("/users" as never)
      return ((data as unknown) as User[]) ?? []
    },
  })

  const { data: departments = [] } = useQuery({
    queryKey: queryKeys.departments.list(),
    queryFn: async () => {
      const { data } = await apiClient.GET("/departments" as never)
      return ((data as unknown) as Department[]) ?? []
    },
  })

  const deptMap = Object.fromEntries(departments.map((d) => [d.id, d.name]))

  const deleteMutation = useMutation({
    mutationFn: async (userId: string) => {
      await apiClient.DELETE(`/users/${userId}` as never)
    },
    onSuccess: () => {
      toast.success("User deleted")
      qc.invalidateQueries({ queryKey: queryKeys.users.all })
      setDeleteTarget(null)
    },
    onError: () => toast.error("Failed to delete user"),
  })

  const filtered = users.filter((u) => {
    const term = search.toLowerCase()
    const matchSearch = !term ||
      u.full_name.toLowerCase().includes(term) ||
      u.email.toLowerCase().includes(term) ||
      (u.employee_id ?? "").toLowerCase().includes(term) ||
      (u.designation ?? "").toLowerCase().includes(term)
    const matchDept = deptFilter === "__all__" || u.department_id === deptFilter
    return matchSearch && matchDept
  })

  const columns: ColumnDef<User>[] = [
    {
      accessorKey: "employee_id",
      header: "Employee ID",
      cell: ({ row }) => (
        <span className="font-mono text-xs">{row.original.employee_id ?? "—"}</span>
      ),
    },
    {
      accessorKey: "faculty_type",
      header: "Faculty Type",
      cell: ({ row }) => (
        <Badge variant="outline" className="font-normal text-xs">
          {row.original.faculty_type ?? "—"}
        </Badge>
      ),
    },
    {
      accessorKey: "first_name",
      header: "First Name",
      cell: ({ row }) => (
        <span className="font-medium">{row.original.first_name ?? row.original.full_name}</span>
      ),
    },
    {
      accessorKey: "last_name",
      header: "Last Name",
      cell: ({ row }) => <span>{row.original.last_name ?? "—"}</span>,
    },
    {
      accessorKey: "department_id",
      header: "Department",
      cell: ({ row }) => (
        <span className="text-muted-foreground text-xs">
          {row.original.department_id ? (deptMap[row.original.department_id] ?? row.original.department_id.slice(0, 8)) : "—"}
        </span>
      ),
    },
    {
      accessorKey: "designation",
      header: "Designation",
      cell: ({ row }) => <span className="text-xs">{row.original.designation ?? "—"}</span>,
    },
    {
      accessorKey: "email",
      header: "Email",
      cell: ({ row }) => <span className="text-muted-foreground text-xs">{row.original.email}</span>,
    },
    {
      accessorKey: "status",
      header: "Status",
      cell: ({ row }) => <StatusBadge status={row.original.status} />,
    },
  ]

  const deleteColumn: ColumnDef<User> = {
    id: "actions",
    header: "",
    cell: ({ row }) => (
      <PermissionGate permission="user.delete">
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7 text-muted-foreground hover:text-destructive"
          onClick={(e) => { e.stopPropagation(); setDeleteTarget(row.original) }}
          title="Delete user"
        >
          <Trash2 className="h-3.5 w-3.5" />
        </Button>
      </PermissionGate>
    ),
  }

  return (
    <div>
      <PageHeader
        title="Users"
        description="Manage faculty and staff accounts."
        actions={
          <PermissionGate permission="user.create">
            <div className="flex gap-2">
              <Button variant="outline" className="gap-2" onClick={() => router.push("/users/new?tab=bulk")}>
                <Upload className="h-4 w-4" />
                Bulk Import
              </Button>
              <Button className="gap-2" onClick={() => router.push("/users/new")}>
                <Plus className="h-4 w-4" />
                Add User
              </Button>
            </div>
          </PermissionGate>
        }
      />

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-5">
        <div className="relative w-72">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
          <Input
            className="pl-8"
            placeholder="Search by name, email, or designation…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <Select value={deptFilter} onValueChange={(v) => { if (v != null) setDeptFilter(v as string) }}>
          <SelectTrigger className="w-56">
            <SelectValue placeholder="All Departments">
              {deptFilter === "__all__" ? "All Departments" : (departments.find((d) => d.id === deptFilter)?.name ?? "All Departments")}
            </SelectValue>
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="__all__">All Departments</SelectItem>
            {departments.map((d) => (
              <SelectItem key={d.id} value={d.id}>{d.name}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <DataTable
        columns={[...columns, deleteColumn]}
        data={filtered}
        loading={isLoading}
        onRowClick={(row) => router.push(`/users/${row.id}`)}
        emptyMessage="No users found."
      />

      <Dialog open={!!deleteTarget} onOpenChange={(open) => { if (!open) setDeleteTarget(null) }}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Delete User</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            Are you sure you want to delete <strong>{deleteTarget?.full_name}</strong> ({deleteTarget?.email})?
            This action cannot be undone.
          </p>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteTarget(null)}>Cancel</Button>
            <Button
              variant="destructive"
              onClick={() => { if (deleteTarget) deleteMutation.mutate(deleteTarget.id) }}
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending ? "Deleting..." : "Delete"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

    </div>
  )
}
