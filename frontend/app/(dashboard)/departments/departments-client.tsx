"use client"

import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useForm, Controller } from "react-hook-form"
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
import { Textarea } from "@/components/ui/textarea"
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
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"

type Department = {
  id: string
  name: string
  short_name: string
  status: string
  current_hod?: { user_id: string; full_name: string } | null
}

type User = { id: string; full_name: string }

const schema = z.object({
  name: z.string().min(2, "Name must be at least 2 characters"),
  short_name: z.string().min(1, "Short name is required").max(30, "Short name too long"),
  head_of_department_id: z.string().optional(),
  description: z.string().optional(),
  vision: z.string().optional(),
  mission: z.string().optional(),
})
type FormValues = z.infer<typeof schema>

const columns: ColumnDef<Department>[] = [
  { accessorKey: "name", header: "Name" },
  { accessorKey: "short_name", header: "Short Name" },
  {
    accessorKey: "status",
    header: "Status",
    cell: ({ row }) => <StatusBadge status={row.original.status} />,
  },
  {
    accessorKey: "current_hod",
    header: "Head of Department",
    cell: ({ row }) => row.original.current_hod?.full_name ?? <span className="text-muted-foreground">—</span>,
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

  const { data: users } = useQuery({
    queryKey: queryKeys.users.list(),
    queryFn: async () => {
      const { data } = await apiClient.GET("/users" as never)
      return ((data as unknown) as User[]) ?? []
    },
  })

  const {
    register,
    handleSubmit,
    control,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) })

  const mutation = useMutation({
    mutationFn: async (values: FormValues) => {
      const { head_of_department_id, ...rest } = values
      const { data } = await apiClient.POST("/departments" as never, { body: rest } as never)
      const created = (data as unknown) as { id: string } | undefined
      if (head_of_department_id && created?.id) {
        await apiClient.POST(`/departments/${created.id}/head` as never, { body: { user_id: head_of_department_id } } as never)
      }
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
              <DialogContent className="sm:max-w-lg">
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
                    <Label htmlFor="dept-short-name">Short Name</Label>
                    <Input id="dept-short-name" {...register("short_name")} placeholder="CSE" />
                    {errors.short_name && (
                      <p className="text-sm text-destructive">{errors.short_name.message}</p>
                    )}
                  </div>
                  <div className="space-y-2">
                    <Label>Head of Department</Label>
                    <Controller
                      name="head_of_department_id"
                      control={control}
                      render={({ field }) => (
                        <Select value={field.value ?? ""} onValueChange={field.onChange}>
                          <SelectTrigger className="w-full">
                            <SelectValue placeholder="Select a user (optional)" />
                          </SelectTrigger>
                          <SelectContent>
                            {(users ?? []).map((u) => (
                              <SelectItem key={u.id} value={u.id}>
                                {u.full_name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      )}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="dept-description">Description</Label>
                    <Textarea id="dept-description" rows={2} {...register("description")} placeholder="Optional" />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="dept-mission">Mission</Label>
                    <Textarea id="dept-mission" rows={2} {...register("mission")} />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="dept-vision">Vision</Label>
                    <Textarea id="dept-vision" rows={2} {...register("vision")} />
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
