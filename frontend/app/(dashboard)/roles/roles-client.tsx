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
import { PermissionGate } from "@/components/shared/permission-gate"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
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

type Role = {
  id: string
  name: string
  description?: string
  permissions_count: number
}

const schema = z.object({
  name: z.string().min(2, "Name required"),
  description: z.string().optional(),
})
type FormValues = z.infer<typeof schema>

const columns: ColumnDef<Role>[] = [
  { accessorKey: "name", header: "Name" },
  {
    accessorKey: "description",
    header: "Description",
    cell: ({ row }) =>
      row.original.description ?? <span className="text-muted-foreground">—</span>,
  },
  {
    accessorKey: "permissions_count",
    header: "Permissions",
    cell: ({ row }) => row.original.permissions_count ?? 0,
  },
]

export function RolesClient() {
  const [open, setOpen] = useState(false)
  const router = useRouter()
  const qc = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.roles.list(),
    queryFn: async () => {
      const { data } = await apiClient.GET("/roles" as never)
      return ((data as unknown) as { items?: Role[] })?.items ?? ((data as unknown) as Role[]) ?? []
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
      await apiClient.POST("/roles" as never, { body: values } as never)
    },
    onSuccess: () => {
      toast.success("Role created")
      qc.invalidateQueries({ queryKey: queryKeys.roles.all })
      reset()
      setOpen(false)
    },
    onError: () => toast.error("Failed to create role"),
  })

  return (
    <div>
      <PageHeader
        title="Roles"
        description="Manage system roles and permissions."
        actions={
          <PermissionGate permission="system.roles.create">
            <Dialog open={open} onOpenChange={setOpen}>
              <DialogTrigger
                render={
                  <Button>
                    <Plus />
                    New Role
                  </Button>
                }
              />
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Create Role</DialogTitle>
                </DialogHeader>
                <form
                  id="create-role-form"
                  onSubmit={handleSubmit((v) => mutation.mutate(v))}
                  className="space-y-4 py-2"
                >
                  <div className="space-y-2">
                    <Label htmlFor="role-name">Name</Label>
                    <Input id="role-name" {...register("name")} placeholder="Department Admin" />
                    {errors.name && (
                      <p className="text-sm text-destructive">{errors.name.message}</p>
                    )}
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="role-desc">Description</Label>
                    <Textarea
                      id="role-desc"
                      {...register("description")}
                      placeholder="Manages department-level resources..."
                      rows={3}
                    />
                  </div>
                </form>
                <DialogFooter showCloseButton>
                  <Button
                    type="submit"
                    form="create-role-form"
                    disabled={isSubmitting || mutation.isPending}
                  >
                    {(isSubmitting || mutation.isPending) && <Loader2 className="animate-spin" />}
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
        onRowClick={(row) => router.push(`/roles/${row.id}`)}
        emptyMessage="No roles found."
      />
    </div>
  )
}
