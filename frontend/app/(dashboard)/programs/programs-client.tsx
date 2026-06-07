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

type Program = {
  id: string
  name: string
  acronym: string
  department_name: string
  duration_years: number
  status: string
}

type Department = {
  id: string
  name: string
}

const schema = z.object({
  name: z.string().min(2, "Name required"),
  acronym: z.string().min(1, "Acronym required").max(10),
  department_id: z.string().min(1, "Department required"),
  duration_years: z.number().int().min(1).max(10),
})
type FormValues = z.infer<typeof schema>

const columns: ColumnDef<Program>[] = [
  { accessorKey: "name", header: "Name" },
  { accessorKey: "acronym", header: "Acronym" },
  { accessorKey: "department_name", header: "Department" },
  {
    accessorKey: "duration_years",
    header: "Duration",
    cell: ({ row }) => `${row.original.duration_years} yr`,
  },
  {
    accessorKey: "status",
    header: "Status",
    cell: ({ row }) => <StatusBadge status={row.original.status} />,
  },
]

export function ProgramsClient() {
  const [open, setOpen] = useState(false)
  const [deptId, setDeptId] = useState("")
  const router = useRouter()
  const qc = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.programs.list(),
    queryFn: async () => {
      const { data } = await apiClient.GET("/programs" as never)
      return ((data as unknown) as { items?: Program[] })?.items ?? ((data as unknown) as Program[]) ?? []
    },
  })

  const { data: departments } = useQuery({
    queryKey: queryKeys.departments.list(),
    queryFn: async () => {
      const { data } = await apiClient.GET("/departments" as never)
      return ((data as unknown) as { items?: Department[] })?.items ?? ((data as unknown) as Department[]) ?? []
    },
  })

  const {
    register,
    handleSubmit,
    setValue,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) })

  const mutation = useMutation({
    mutationFn: async (values: FormValues) => {
      await apiClient.POST("/programs" as never, { body: values } as never)
    },
    onSuccess: () => {
      toast.success("Program created")
      qc.invalidateQueries({ queryKey: queryKeys.programs.all })
      reset()
      setDeptId("")
      setOpen(false)
    },
    onError: () => toast.error("Failed to create program"),
  })

  return (
    <div>
      <PageHeader
        title="Programs"
        description="Manage academic programs."
        actions={
          <PermissionGate permission="program.create">
            <Dialog open={open} onOpenChange={setOpen}>
              <DialogTrigger
                render={
                  <Button>
                    <Plus />
                    New Program
                  </Button>
                }
              />
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Create Program</DialogTitle>
                </DialogHeader>
                <form
                  id="create-prog-form"
                  onSubmit={handleSubmit((v) => mutation.mutate(v))}
                  className="space-y-4 py-2"
                >
                  <div className="space-y-2">
                    <Label htmlFor="prog-name">Name</Label>
                    <Input id="prog-name" {...register("name")} placeholder="Bachelor of Science in CS" />
                    {errors.name && <p className="text-sm text-destructive">{errors.name.message}</p>}
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="prog-acronym">Acronym</Label>
                    <Input id="prog-acronym" {...register("acronym")} placeholder="BSCS" />
                    {errors.acronym && <p className="text-sm text-destructive">{errors.acronym.message}</p>}
                  </div>
                  <div className="space-y-2">
                    <Label>Department</Label>
                    <Select
                      value={deptId}
                      onValueChange={(v) => {
                        if (v == null) return
                        setDeptId(v as string)
                        setValue("department_id", v as string, { shouldValidate: true })
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
                    {errors.department_id && (
                      <p className="text-sm text-destructive">{errors.department_id.message}</p>
                    )}
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="prog-years">Duration (years)</Label>
                    <Input
                      id="prog-years"
                      type="number"
                      min={1}
                      max={10}
                      {...register("duration_years", { valueAsNumber: true })}
                      placeholder="4"
                    />
                    {errors.duration_years && (
                      <p className="text-sm text-destructive">{errors.duration_years.message}</p>
                    )}
                  </div>
                </form>
                <DialogFooter showCloseButton>
                  <Button
                    type="submit"
                    form="create-prog-form"
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
        onRowClick={(row) => router.push(`/programs/${row.id}`)}
        emptyMessage="No programs found."
      />
    </div>
  )
}
