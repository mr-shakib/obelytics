"use client"

import { useEffect, useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { Search } from "lucide-react"
import type { ColumnDef } from "@tanstack/react-table"
import { DataTable } from "@/components/shared/data-table"
import { PageHeader } from "@/components/shared/page-header"
import { StatusBadge } from "@/components/shared/status-badge"
import { Input } from "@/components/ui/input"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"

type Student = {
  id: string
  student_id_number: string
  full_name: string
  email: string | null
  status: string
}

const columns: ColumnDef<Student>[] = [
  { accessorKey: "student_id_number", header: "Student ID" },
  { accessorKey: "full_name", header: "Name" },
  {
    accessorKey: "email",
    header: "Email",
    cell: ({ row }) => row.original.email ?? <span className="text-muted-foreground">—</span>,
  },
  {
    accessorKey: "status",
    header: "Status",
    cell: ({ row }) => <StatusBadge status={row.original.status} />,
  },
]

export function StudentsClient() {
  const [search, setSearch] = useState("")
  const [debouncedSearch, setDebouncedSearch] = useState("")

  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search), 300)
    return () => clearTimeout(t)
  }, [search])

  const { data: students = [], isLoading } = useQuery({
    queryKey: queryKeys.students.list({ search: debouncedSearch }),
    queryFn: async () => {
      const { data } = await apiClient.GET("/students" as never, {
        params: { query: debouncedSearch ? { search: debouncedSearch } : {} },
      } as never)
      return ((data as unknown) as Student[]) ?? []
    },
  })

  return (
    <div className="space-y-4">
      <PageHeader
        title="Students"
        description="System-wide student registry. Add students from a batch's detail page."
      />

      <div className="relative max-w-sm">
        <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
        <Input
          className="pl-8"
          placeholder="Search by ID or name…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      <DataTable columns={columns} data={students} loading={isLoading} emptyMessage="No students found." />
    </div>
  )
}
