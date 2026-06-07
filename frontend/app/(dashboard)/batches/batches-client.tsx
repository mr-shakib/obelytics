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

type Batch = {
  id: string
  name: string
  program_name: string
  intake_year: number
  status: string
}

type Program = {
  id: string
  name: string
}

const schema = z.object({
  name: z.string().min(1, "Name is required"),
  program_id: z.string().min(1, "Program is required"),
  intake_year: z.number().int().min(2000).max(2100),
})
type FormValues = z.infer<typeof schema>

const columns: ColumnDef<Batch>[] = [
  { accessorKey: "name", header: "Name" },
  { accessorKey: "program_name", header: "Program" },
  { accessorKey: "intake_year", header: "Intake Year" },
  {
    accessorKey: "status",
    header: "Status",
    cell: ({ row }) => <StatusBadge status={row.original.status} />,
  },
]

export function BatchesClient() {
  const [open, setOpen] = useState(false)
  const qc = useQueryClient()
  const router = useRouter()

  const { data: batches = [], isLoading } = useQuery({
    queryKey: queryKeys.batches.all,
    queryFn: async () => {
      const { data } = await apiClient.GET("/batches" as never)
      return ((data as unknown) as Batch[]) ?? []
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
      await apiClient.POST("/batches" as never, { body: values } as never)
    },
    onSuccess: () => {
      toast.success("Batch created")
      qc.invalidateQueries({ queryKey: queryKeys.batches.all })
      setOpen(false)
      reset()
    },
    onError: () => toast.error("Failed to create batch"),
  })

  return (
    <div>
      <PageHeader
        title="Batches"
        description="Manage student batches."
        actions={
          <PermissionGate permission="batch.create">
            <Dialog open={open} onOpenChange={setOpen}>
              <DialogTrigger render={<Button />}>
                <Plus className="h-4 w-4" />
                New Batch
              </DialogTrigger>
              <DialogContent className="sm:max-w-md">
                <DialogHeader>
                  <DialogTitle>Create Batch</DialogTitle>
                </DialogHeader>
                <form
                  id="create-batch-form"
                  onSubmit={handleSubmit((v) => mutation.mutate(v))}
                  className="space-y-4 py-2"
                >
                  <div className="space-y-2">
                    <Label htmlFor="name">Name</Label>
                    <Input id="name" {...register("name")} placeholder="e.g. CSE 2024" />
                    {errors.name && (
                      <p className="text-sm text-destructive">{errors.name.message}</p>
                    )}
                  </div>
                  <div className="space-y-2">
                    <Label>Program</Label>
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
                    <Label htmlFor="intake_year">Intake Year</Label>
                    <Input
                      id="intake_year"
                      type="number"
                      min={2000}
                      max={2100}
                      {...register("intake_year", { valueAsNumber: true })}
                    />
                    {errors.intake_year && (
                      <p className="text-sm text-destructive">{errors.intake_year.message}</p>
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
                    form="create-batch-form"
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
        data={batches}
        loading={isLoading}
        onRowClick={(row) => router.push(`/batches/${row.id}`)}
        emptyMessage="No batches found."
      />
    </div>
  )
}
