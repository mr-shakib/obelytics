"use client"

import { useQuery } from "@tanstack/react-query"
import type { ColumnDef } from "@tanstack/react-table"

import { PageHeader } from "@/components/shared/page-header"
import { DataTable } from "@/components/shared/data-table"
import { StatusBadge } from "@/components/shared/status-badge"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"
import { formatDate } from "@/lib/utils"

type AcademicTerm = {
  id: string
  name: string
  season: string
  year: number
  start_date: string
  end_date: string
  status: string
}

const columns: ColumnDef<AcademicTerm>[] = [
  { accessorKey: "name", header: "Name" },
  { accessorKey: "season", header: "Season" },
  { accessorKey: "year", header: "Year" },
  {
    accessorKey: "start_date",
    header: "Start Date",
    cell: ({ row }) => formatDate(row.original.start_date),
  },
  {
    accessorKey: "end_date",
    header: "End Date",
    cell: ({ row }) => formatDate(row.original.end_date),
  },
  {
    accessorKey: "status",
    header: "Status",
    cell: ({ row }) => <StatusBadge status={row.original.status} />,
  },
]

export function AcademicTermsClient() {
  const { data: terms = [], isLoading } = useQuery({
    queryKey: queryKeys.academicTerms.all,
    queryFn: async () => {
      const { data } = await apiClient.GET("/academic-terms" as never)
      return ((data as unknown) as AcademicTerm[]) ?? []
    },
  })

  return (
    <div>
      <PageHeader
        title="Academic Terms"
        description="Terms are auto-generated when academic batches are created."
      />
      <DataTable
        columns={columns}
        data={terms}
        loading={isLoading}
        emptyMessage="No academic terms yet. Create a batch to generate terms automatically."
      />
    </div>
  )
}
