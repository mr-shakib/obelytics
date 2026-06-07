"use client"

import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { toast } from "sonner"
import { Plus, Loader2 } from "lucide-react"
import { useRouter } from "next/navigation"
import type { ColumnDef } from "@tanstack/react-table"
import { DataTable } from "@/components/shared/data-table"
import { PageHeader } from "@/components/shared/page-header"
import { StatusBadge } from "@/components/shared/status-badge"
import { PermissionGate } from "@/components/shared/permission-gate"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogTrigger,
} from "@/components/ui/dialog"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"

type Department = {
  id: string
  name: string
  code: string
  status: string
  hod_name?: string
}

const schema = z.object({
  name: z.string().min(2, "Name must be at least 2 characters"),
  code: z.string().min(1, "Code is required").max(20, "Code too long"),
})
type FormValues = z.infer<typeof schema>

const columns: ColumnDef<Department>[] = [
  { accessorKey: "name", header: "Name" },
  { accessorKey: "code", header: "Code" },
  {
    accessorKey: "status",
    header: "Status",
    cell: ({ row }) => <StatusBadge status={row.original.status} />,
  },
  {
    accessorKey: "hod_name",
    header: "HOD",
    cell: ({ row }) => row.original.hod_name ?? <span className="text-muted-foreground">—</span>,
  },
]

export function DepartmentsClient() {
  const [open, setOpen] = useState(false)
  const router = useRouter()
  const qc = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.departments.list(),
    queryFn: async () => {
      const { data } = await apiClient.GET("/departments" as never)
      return ((data as unknown) as { items?: Department[] })?.items ?? ((data as unknown) as Department[]) ?? []
    },
  })

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) })

  const mutation = useMutation({
    mutationFn: async (values: FormValues) => {
      await apiClient.POST("/departments" as never, { body: values } as never)
    },
    onSuccess: () => {
      toast.success("Department created")
      qc.invalidateQueries({ queryKey: queryKeys.departments.all })
      reset()
      setOpen(false)
    },
    onError: () => toast.error("Failed to create department"),
  })

  return (
    <div>
      <PageHeader
        title="Departments"
        description="Manage university departments."
        actions={
          <PermissionGate permission="department.create">
            <Dialog open={open} onOpenChange={setOpen}>
              <DialogTrigger
                render={
                  <Button>
                    <Plus />
                    New Department
                  </Button>
                }
              />
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Create Department</DialogTitle>
                </DialogHeader>
                <form
                  id="create-dept-form"
                  onSubmit={handleSubmit((v) => mutation.mutate(v))}
                  className="space-y-4 py-2"
                >
                  <div className="space-y-2">
                    <Label htmlFor="dept-name">Name</Label>
                    <Input id="dept-name" {...register("name")} placeholder="Computer Science" />
                    {errors.name && (
                      <p className="text-sm text-destructive">{errors.name.message}</p>
                    )}
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="dept-code">Code</Label>
                    <Input id="dept-code" {...register("code")} placeholder="CS" />
                    {errors.code && (
                      <p className="text-sm text-destructive">{errors.code.message}</p>
                    )}
                  </div>
                </form>
                <DialogFooter showCloseButton>
                  <Button
                    type="submit"
                    form="create-dept-form"
                    disabled={isSubmitting || mutation.isPending}
                  >
                    {(isSubmitting || mutation.isPending) && (
                      <Loader2 className="animate-spin" />
                    )}
                    Create
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </PermissionGate>
        }
      />
      <DataTable
        columns={columns}
        data={data ?? []}
        loading={isLoading}
        onRowClick={(row) => router.push(`/departments/${row.id}`)}
        emptyMessage="No departments found."
      />
    </div>
  )
}
