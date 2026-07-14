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
  curriculum_id: string
  intake_year: number | null
  start_date: string | null
  term_system: string | null
  num_semesters: number | null
  status: string
}

type Curriculum = {
  id: string
  name: string
  code: string
}

const TERM_SYSTEMS = [
  { value: "TRIMESTER", label: "Trimester (3 per year — Spring, Summer, Fall)" },
  { value: "SEMESTER",  label: "Semester (2 per year — Spring, Fall)" },
] as const

const schema = z.object({
  name: z.string().min(1, "Name is required"),
  curriculum_id: z.string().min(1, "Curriculum is required"),
  start_date: z.string().min(1, "Start date is required"),
  term_system: z.enum(["TRIMESTER", "SEMESTER"]),
  num_semesters: z.number().int().min(1).max(30),
})
type FormValues = z.infer<typeof schema>

const columns: ColumnDef<Batch>[] = [
  { accessorKey: "name", header: "Batch Name" },
  {
    accessorKey: "term_system",
    header: "Term System",
    cell: ({ row }) => row.original.term_system ?? "—",
  },
  {
    accessorKey: "start_date",
    header: "Start",
    cell: ({ row }) => row.original.start_date?.slice(0, 7) ?? "—",
  },
  {
    accessorKey: "num_semesters",
    header: "Semesters",
    cell: ({ row }) => row.original.num_semesters ?? "—",
  },
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

  const { data: curricula = [] } = useQuery({
    queryKey: queryKeys.curricula.all,
    queryFn: async () => {
      const { data } = await apiClient.GET("/curricula" as never)
      return ((data as unknown) as Curriculum[]) ?? []
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
      await apiClient.POST("/batches" as never, { body: values } as never)
    },
    onSuccess: () => {
      toast.success("Batch created — semesters auto-generated")
      qc.invalidateQueries({ queryKey: queryKeys.batches.all })
      setOpen(false)
      reset()
    },
    onError: () => toast.error("Failed to create batch"),
  })

  return (
    <div>
      <PageHeader
        title="Academic Batches"
        description="Create batches and auto-generate their semester calendar."
        actions={
          <PermissionGate permission="batch.create">
            <Dialog open={open} onOpenChange={setOpen}>
              <DialogTrigger render={<Button />}>
                <Plus className="h-4 w-4" />
                New Batch
              </DialogTrigger>
              <DialogContent className="sm:max-w-lg">
                <DialogHeader>
                  <DialogTitle>Create Academic Batch</DialogTitle>
                </DialogHeader>
                <form
                  id="create-batch-form"
                  onSubmit={handleSubmit((v) => mutation.mutate(v))}
                  className="space-y-4 py-2"
                >
                  <div className="space-y-2">
                    <Label htmlFor="name">Batch Name</Label>
                    <Input id="name" {...register("name")} placeholder="e.g. Batch CSE 61" />
                    {errors.name && <p className="text-sm text-destructive">{errors.name.message}</p>}
                  </div>

                  <div className="space-y-2">
                    <Label>Curriculum</Label>
                    <Controller
                      name="curriculum_id"
                      control={control}
                      render={({ field }) => (
                        <Select value={field.value ?? ""} onValueChange={field.onChange}>
                          <SelectTrigger className="w-full">
                            <SelectValue placeholder="Select curriculum">
                              {(value: string) => {
                                const c = curricula.find((c) => c.id === value)
                                return c ? c.name : value
                              }}
                            </SelectValue>
                          </SelectTrigger>
                          <SelectContent>
                            {curricula.map((c) => (
                              <SelectItem key={c.id} value={c.id}>
                                {c.name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      )}
                    />
                    {errors.curriculum_id && <p className="text-sm text-destructive">{errors.curriculum_id.message}</p>}
                  </div>

                  <div className="space-y-2">
                    <Label>Term System</Label>
                    <Controller
                      name="term_system"
                      control={control}
                      render={({ field }) => (
                        <Select value={field.value ?? ""} onValueChange={field.onChange}>
                          <SelectTrigger className="w-full">
                            <SelectValue placeholder="Select term system" />
                          </SelectTrigger>
                          <SelectContent>
                            {TERM_SYSTEMS.map((t) => (
                              <SelectItem key={t.value} value={t.value}>
                                {t.label}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      )}
                    />
                    {errors.term_system && <p className="text-sm text-destructive">{errors.term_system.message}</p>}
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="start_date">Start Date</Label>
                      <Input id="start_date" type="date" {...register("start_date")} />
                      {errors.start_date && <p className="text-sm text-destructive">{errors.start_date.message}</p>}
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="num_semesters">Number of Semesters</Label>
                      <Input
                        id="num_semesters"
                        type="number"
                        min={1}
                        max={30}
                        {...register("num_semesters", { valueAsNumber: true })}
                        placeholder="e.g. 12"
                      />
                      {errors.num_semesters && <p className="text-sm text-destructive">{errors.num_semesters.message}</p>}
                    </div>
                  </div>
                </form>
                <DialogFooter showCloseButton>
                  <Button
                    type="submit"
                    form="create-batch-form"
                    disabled={isSubmitting || mutation.isPending}
                  >
                    {(isSubmitting || mutation.isPending) && <Loader2 className="animate-spin" />}
                    Create &amp; Generate Semesters
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
