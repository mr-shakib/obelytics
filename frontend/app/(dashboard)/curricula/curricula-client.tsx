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

import { PageHeader } from "@/components/shared/page-header"
import { DataTable } from "@/components/shared/data-table"
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
  DialogTrigger,
  DialogFooter,
} from "@/components/ui/dialog"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"
import { formatDate } from "@/lib/utils"

type Curriculum = {
  id: string
  name: string
  program_name: string
  version: string
  status: string
  effective_from: string
  effective_to?: string
}

type Program = {
  id: string
  name: string
}

const schema = z.object({
  name: z.string().min(1, "Name is required"),
  program_id: z.string().min(1, "Program is required"),
  version: z.string().min(1, "Version is required"),
  effective_from: z.string().min(1, "Effective from date is required"),
})
type FormValues = z.infer<typeof schema>

const columns: ColumnDef<Curriculum>[] = [
  { accessorKey: "name", header: "Name" },
  { accessorKey: "program_name", header: "Program" },
  { accessorKey: "version", header: "Version" },
  {
    accessorKey: "status",
    header: "Status",
    cell: ({ row }) => <StatusBadge status={row.original.status} />,
  },
  {
    accessorKey: "effective_from",
    header: "Effective From",
    cell: ({ row }) => formatDate(row.original.effective_from),
  },
  {
    accessorKey: "effective_to",
    header: "Effective To",
    cell: ({ row }) => row.original.effective_to ? formatDate(row.original.effective_to) : "—",
  },
]

export function CurriculaClient() {
  const [open, setOpen] = useState(false)
  const qc = useQueryClient()
  const router = useRouter()

  const { data: curricula = [], isLoading } = useQuery({
    queryKey: queryKeys.curricula.all,
    queryFn: async () => {
      const { data } = await apiClient.GET("/curricula" as never)
      return ((data as unknown) as Curriculum[]) ?? []
    },
  })

  const { data: programs = [] } = useQuery({
    queryKey: queryKeys.programs.all,
    queryFn: async () => {
      const { data } = await apiClient.GET("/programs" as never)
      return ((data as unknown) as Program[]) ?? []
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
      await apiClient.POST("/curricula" as never, { body: values } as never)
    },
    onSuccess: () => {
      toast.success("Curriculum created")
      qc.invalidateQueries({ queryKey: queryKeys.curricula.all })
      setOpen(false)
      reset()
    },
    onError: () => toast.error("Failed to create curriculum"),
  })

  return (
    <div>
      <PageHeader
        title="Curricula"
        description="Manage academic curricula across programs."
        actions={
          <PermissionGate permission="curriculum.create">
            <Dialog open={open} onOpenChange={setOpen}>
              <DialogTrigger render={<Button />}>
                <Plus className="h-4 w-4" />
                New Curriculum
              </DialogTrigger>
              <DialogContent className="sm:max-w-md">
                <DialogHeader>
                  <DialogTitle>Create Curriculum</DialogTitle>
                </DialogHeader>
                <form
                  id="create-curriculum-form"
                  onSubmit={handleSubmit((v) => mutation.mutate(v))}
                  className="space-y-4 py-2"
                >
                  <div className="space-y-2">
                    <Label htmlFor="name">Name</Label>
                    <Input id="name" {...register("name")} />
                    {errors.name && (
                      <p className="text-sm text-destructive">{errors.name.message}</p>
                    )}
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="program_id">Program</Label>
                    <Select onValueChange={(v) => v != null && setValue("program_id", v as string)}>
                      <SelectTrigger className="w-full">
                        <SelectValue placeholder="Select program" />
                      </SelectTrigger>
                      <SelectContent>
                        {programs.map((p) => (
                          <SelectItem key={p.id} value={p.id}>
                            {p.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {errors.program_id && (
                      <p className="text-sm text-destructive">{errors.program_id.message}</p>
                    )}
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="version">Version</Label>
                    <Input id="version" {...register("version")} placeholder="e.g. 2024.1" />
                    {errors.version && (
                      <p className="text-sm text-destructive">{errors.version.message}</p>
                    )}
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="effective_from">Effective From</Label>
                    <Input id="effective_from" type="date" {...register("effective_from")} />
                    {errors.effective_from && (
                      <p className="text-sm text-destructive">{errors.effective_from.message}</p>
                    )}
                  </div>
                </form>
                <DialogFooter>
                  <Button
                    variant="outline"
                    onClick={() => setOpen(false)}
                    disabled={isSubmitting || mutation.isPending}
                  >
                    Cancel
                  </Button>
                  <Button
                    type="submit"
                    form="create-curriculum-form"
                    disabled={isSubmitting || mutation.isPending}
                  >
                    {(isSubmitting || mutation.isPending) && (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
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
        data={curricula}
        loading={isLoading}
        onRowClick={(row) => router.push(`/curricula/${row.id}`)}
        emptyMessage="No curricula found."
      />
    </div>
  )
}
