"use client"

import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Plus, Search, Upload, Trash2, Download } from "lucide-react"
import { useRouter } from "next/navigation"
import { toast } from "sonner"
import type { ColumnDef, RowSelectionState } from "@tanstack/react-table"
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

const FACULTY_TYPES = ["Faculty", "Administrative", "Management"] as const

const EXPORT_HEADERS = [
  "Employee ID", "Faculty Type", "First Name", "Last Name",
  "Full Name", "Email", "Department", "Designation", "Status",
] as const

// Quote only when needed; double up embedded quotes (RFC 4180).
function csvCell(value: string | null | undefined) {
  const s = value ?? ""
  return /[",\r\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
}


// ── Main Page ─────────────────────────────────────────────────────────────────

export function UsersClient() {
  const router = useRouter()
  const qc = useQueryClient()
  const [search, setSearch] = useState("")
  const [deptFilter, setDeptFilter] = useState("__all__")
  const [deleteTarget, setDeleteTarget] = useState<User | null>(null)
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({})
  const [bulkFacultyType, setBulkFacultyType] = useState<string>("Faculty")

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

  const bulkFacultyTypeMutation = useMutation({
    mutationFn: async ({ userIds, facultyType }: { userIds: string[]; facultyType: string }) => {
      const { data } = await apiClient.POST("/users/bulk/faculty-type" as never, {
        body: { user_ids: userIds, faculty_type: facultyType },
      } as never)
      return (data as unknown) as { updated_count: number }
    },
    onSuccess: (data) => {
      toast.success(`Updated ${data.updated_count} user${data.updated_count === 1 ? "" : "s"}`)
      setRowSelection({})
      qc.invalidateQueries({ queryKey: queryKeys.users.all })
    },
    onError: () => toast.error("Failed to update faculty type"),
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

  const selectedIds = Object.entries(rowSelection)
    .filter(([, selected]) => selected)
    .map(([id]) => id)
  const selectedUsers = users.filter((u) => selectedIds.includes(u.id))
  const selectedCount = selectedUsers.length

  function handleExportCsv() {
    const rows = filtered.map((u) =>
      [
        u.employee_id,
        u.faculty_type,
        u.first_name,
        u.last_name,
        u.full_name,
        u.email,
        u.department_id ? (deptMap[u.department_id] ?? "") : "",
        u.designation,
        u.status,
      ].map(csvCell).join(",")
    )

    // Leading BOM so Excel reads the file as UTF-8 rather than mangling
    // non-ASCII names.
    const csv = "\uFEFF" + [EXPORT_HEADERS.join(","), ...rows].join("\r\n")
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" })
    const objectUrl = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = objectUrl
    a.download = `users_${new Date().toISOString().slice(0, 10)}.csv`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(objectUrl)
    toast.success(`Exported ${filtered.length} user${filtered.length === 1 ? "" : "s"}`)
  }

  const selectionColumn: ColumnDef<User> = {
    id: "select",
    header: ({ table }) => (
      <input
        type="checkbox"
        className="h-4 w-4"
        checked={table.getIsAllPageRowsSelected()}
        ref={(input) => {
          if (input) input.indeterminate = table.getIsSomePageRowsSelected()
        }}
        onChange={table.getToggleAllPageRowsSelectedHandler()}
        onClick={(e) => e.stopPropagation()}
        aria-label="Select visible users"
      />
    ),
    cell: ({ row }) => (
      <input
        type="checkbox"
        className="h-4 w-4"
        checked={row.getIsSelected()}
        onChange={row.getToggleSelectedHandler()}
        onClick={(e) => e.stopPropagation()}
        aria-label={`Select ${row.original.full_name}`}
      />
    ),
    enableSorting: false,
  }

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
          <div className="flex gap-2">
            <Button
              variant="outline"
              className="gap-2"
              onClick={handleExportCsv}
              disabled={isLoading || filtered.length === 0}
            >
              <Download className="h-4 w-4" />
              Export CSV{filtered.length > 0 ? ` (${filtered.length})` : ""}
            </Button>
            <PermissionGate permission="user.create">
              <Button variant="outline" className="gap-2" onClick={() => router.push("/users/new?tab=bulk")}>
                <Upload className="h-4 w-4" />
                Bulk Import
              </Button>
              <Button className="gap-2" onClick={() => router.push("/users/new")}>
                <Plus className="h-4 w-4" />
                Add User
              </Button>
            </PermissionGate>
          </div>
        }
      />

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-3">
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

      <PermissionGate permission="user.update">
        <div className="mb-5 flex flex-wrap items-center gap-3 rounded-md border bg-muted/30 px-3 py-2">
          <span className="text-sm font-medium">
            Bulk faculty type
          </span>
          <span className="text-xs text-muted-foreground">
            {selectedCount > 0 ? `${selectedCount} selected` : "Select users from the table"}
          </span>
          <Select value={bulkFacultyType} onValueChange={(v) => { if (v != null) setBulkFacultyType(v as string) }}>
            <SelectTrigger className="w-48">
              <SelectValue placeholder="Faculty type" />
            </SelectTrigger>
            <SelectContent>
              {FACULTY_TYPES.map((type) => (
                <SelectItem key={type} value={type}>{type}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button
            size="sm"
            onClick={() => bulkFacultyTypeMutation.mutate({ userIds: selectedIds, facultyType: bulkFacultyType })}
            disabled={selectedCount === 0 || bulkFacultyTypeMutation.isPending}
          >
            {bulkFacultyTypeMutation.isPending ? "Updating..." : "Apply to Selected"}
          </Button>
          <Button variant="ghost" size="sm" onClick={() => setRowSelection({})} disabled={selectedCount === 0}>
            Clear
          </Button>
        </div>
      </PermissionGate>

      <DataTable
        columns={[selectionColumn, ...columns, deleteColumn]}
        data={filtered}
        getRowId={(row) => row.id}
        rowSelection={rowSelection}
        onRowSelectionChange={setRowSelection}
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
