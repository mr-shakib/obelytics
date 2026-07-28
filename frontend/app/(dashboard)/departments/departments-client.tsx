"use client"

import { useRef, useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useForm, Controller } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { toast } from "sonner"
import { Plus, Loader2, Upload } from "lucide-react"
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
import { Combobox } from "@/components/ui/combobox"
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
import { useAuthStore } from "@/lib/stores/auth-store"

type Department = {
  id: string
  name: string
  short_name: string
  logo_url?: string | null
  status: string
  current_hod?: { user_id: string; full_name: string } | null
}

type User = { id: string; full_name: string; employee_id?: string | null }

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
  {
    accessorKey: "logo_url",
    header: "Logo",
    cell: ({ row }) =>
      row.original.logo_url ? (
        <div className="flex size-10 items-center justify-center rounded border bg-background p-1">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={row.original.logo_url}
            alt={`${row.original.name} logo`}
            className="max-h-full max-w-full object-contain"
          />
        </div>
      ) : (
        <span className="rounded border border-amber-300 bg-amber-50 px-2 py-1 text-xs font-medium text-amber-800">
          Upload required
        </span>
      ),
  },
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
  const [logoFile, setLogoFile] = useState<File | null>(null)
  const [logoPreview, setLogoPreview] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const router = useRouter()
  const qc = useQueryClient()
  const { accessToken } = useAuthStore()

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
      if (!logoFile) throw new Error("logo_required")
      const { head_of_department_id, ...rest } = values
      const { data } = await apiClient.POST("/departments" as never, { body: rest } as never)
      const created = (data as unknown) as { id: string } | undefined
      if (!created?.id) throw new Error("department_create_failed")

      const form = new FormData()
      form.append("file", logoFile)
      const logoRes = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/v1/departments/${created.id}/logo`,
        {
          method: "POST",
          headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
          body: form,
        }
      )
      if (!logoRes.ok) throw new Error("logo_upload_failed")

      if (head_of_department_id && created?.id) {
        await apiClient.POST(`/departments/${created.id}/head` as never, { body: { user_id: head_of_department_id } } as never)
      }
    },
    onSuccess: () => {
      toast.success("Department created")
      qc.invalidateQueries({ queryKey: queryKeys.departments.all })
      reset()
      setLogoFile(null)
      setLogoPreview(null)
      setOpen(false)
    },
    onError: (error) => {
      toast.error(error instanceof Error && error.message === "logo_required"
        ? "Department logo is required"
        : "Failed to create department")
    },
  })

  function handleLogoChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setLogoFile(file)
    setLogoPreview(URL.createObjectURL(file))
  }

  function handleDialogOpenChange(nextOpen: boolean) {
    setOpen(nextOpen)
    if (!nextOpen) {
      reset()
      setLogoFile(null)
      setLogoPreview(null)
    }
  }

  return (
    <div>
      <PageHeader
        title="Departments"
        description="Manage university departments."
        actions={
          <PermissionGate permission="department.create">
            <Dialog open={open} onOpenChange={handleDialogOpenChange}>
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
                  className="space-y-4 py-2 overflow-y-auto flex-1 min-h-0 pr-1"
                >
                  <div className="space-y-2">
                    <Label>Department Logo</Label>
                    <div className="flex items-center gap-3">
                      <div className="flex size-16 items-center justify-center rounded border bg-muted/20 p-2">
                        {logoPreview ? (
                          <>
                            {/* eslint-disable-next-line @next/next/no-img-element */}
                            <img src={logoPreview} alt="Department logo preview" className="max-h-full max-w-full object-contain" />
                          </>
                        ) : (
                          <Upload className="size-5 text-muted-foreground" />
                        )}
                      </div>
                      <div className="space-y-1">
                        <Input
                          ref={fileInputRef}
                          type="file"
                          accept="image/*,.svg"
                          className="hidden"
                          onChange={handleLogoChange}
                        />
                        <Button type="button" variant="outline" onClick={() => fileInputRef.current?.click()}>
                          <Upload />
                          Upload Logo
                        </Button>
                        <p className="text-xs text-muted-foreground">Required. PNG, JPG, or SVG up to 2MB.</p>
                      </div>
                    </div>
                  </div>
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
                        <Combobox
                          options={(users ?? []).map((u) => ({
                            value: u.id,
                            label: u.employee_id ? `${u.employee_id} — ${u.full_name}` : u.full_name,
                          }))}
                          value={field.value ?? ""}
                          onValueChange={field.onChange}
                          placeholder="Select a user (optional)"
                          searchPlaceholder="Search by employee ID or name…"
                          emptyText="No users found."
                          triggerClassName="w-full"
                        />
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
