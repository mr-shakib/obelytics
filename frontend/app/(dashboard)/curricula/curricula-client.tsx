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

type Curriculum = {
  id: string
  program_id: string
  name: string
  code: string
  effective_year: number
  version_number: number
  status: string
}

type Program = { id: string; title?: string; name?: string; acronym?: string }

function programLabel(p: Program) {
  const title = p.title ?? p.name ?? ""
  return p.acronym ? `${p.acronym} — ${title}` : title || p.id
}

const schema = z.object({
  name: z.string().min(1, "Name is required").max(255),
  code: z.string().min(1, "Code is required").max(50),
  program_id: z.string().min(1, "Program is required"),
  effective_year: z.number().int().min(1900).max(2100),
  batch_name: z.string().min(1, "Batch name is required").max(100),
  semester_count: z.number().int().min(1, "At least 1 semester is required").max(20),
})
type FormValues = z.infer<typeof schema>

export function CurriculaClient() {
  const [open, setOpen] = useState(false)
  const [selProgramId, setSelProgramId] = useState("")
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

  const programById = Object.fromEntries(programs.map((p) => [p.id, p]))

  const columns: ColumnDef<Curriculum>[] = [
    { accessorKey: "name", header: "Name" },
    { accessorKey: "code", header: "Code" },
    {
      id: "program",
      header: "Program",
      cell: ({ row }) => {
        const p = programById[row.original.program_id]
        return p ? programLabel(p) : "—"
      },
    },
    { accessorKey: "effective_year", header: "Effective Year" },
    {
      accessorKey: "version_number",
      header: "Version",
      cell: ({ row }) => `v${row.original.version_number}`,
    },
    {
      accessorKey: "status",
      header: "Status",
      cell: ({ row }) => <StatusBadge status={row.original.status} />,
    },
  ]

  const {
    register,
    handleSubmit,
    setValue,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: { semester_count: 8 } })

  const mutation = useMutation({
    mutationFn: async (values: FormValues) => {
      const { data: curriculum } = await apiClient.POST("/curricula" as never, {
        body: {
          name: values.name,
          code: values.code,
          program_id: values.program_id,
          effective_year: values.effective_year,
        },
      } as never)
      const created = (curriculum as unknown) as { id: string }
      await apiClient.POST("/batches" as never, {
        body: {
          curriculum_id: created.id,
          name: values.batch_name,
          start_date: `${values.effective_year}-01-01`,
          term_system: "SEMESTER",
          num_semesters: values.semester_count,
        },
      } as never)
      await apiClient.POST(`/curricula/${created.id}/terms` as never, {
        body: Array.from({ length: values.semester_count }, (_, i) => ({
          term_number: i + 1,
          name: `Semester ${i + 1}`,
          total_credit_hours: null,
        })),
      } as never)
    },
    onSuccess: () => {
      toast.success("Curriculum created")
      qc.invalidateQueries({ queryKey: queryKeys.curricula.all })
      qc.invalidateQueries({ queryKey: queryKeys.batches.all })
      setOpen(false)
      setSelProgramId("")
      reset({ semester_count: 8 })
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
            <Dialog open={open} onOpenChange={(v) => { setOpen(v); if (!v) { setSelProgramId(""); reset() } }}>
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
                    <Input id="name" placeholder="e.g. BSc in CSE Curriculum" {...register("name")} />
                    {errors.name && (
                      <p className="text-sm text-destructive">{errors.name.message}</p>
                    )}
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="program_id">Program</Label>
                    <Select
                      value={selProgramId}
                      onValueChange={(v) => { if (v == null) return; setSelProgramId(v as string); setValue("program_id", v as string, { shouldValidate: true }) }}
                    >
                      <SelectTrigger className="w-full">
                        <SelectValue placeholder="Select program">
                          {selProgramId ? (programById[selProgramId] ? programLabel(programById[selProgramId]) : undefined) : undefined}
                        </SelectValue>
                      </SelectTrigger>
                      <SelectContent>
                        {programs.map((p) => (
                          <SelectItem key={p.id} value={p.id}>
                            {programLabel(p)}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {errors.program_id && (
                      <p className="text-sm text-destructive">{errors.program_id.message}</p>
                    )}
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="code">Code</Label>
                      <Input id="code" placeholder="e.g. CSE-2024" {...register("code")} />
                      {errors.code && (
                        <p className="text-sm text-destructive">{errors.code.message}</p>
                      )}
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="effective_year">Effective Year</Label>
                      <Input
                        id="effective_year"
                        type="number"
                        min={1900}
                        max={2100}
                        placeholder="e.g. 2024"
                        {...register("effective_year", { valueAsNumber: true })}
                      />
                      {errors.effective_year && (
                        <p className="text-sm text-destructive">{errors.effective_year.message}</p>
                      )}
                    </div>
                  </div>
                  <div className="space-y-2 rounded-xl border bg-muted/30 p-4">
                    <Label htmlFor="batch_name">Batch Name</Label>
                    <Input id="batch_name" placeholder="e.g. Fall 2024" {...register("batch_name")} />
                    {errors.batch_name && (
                      <p className="text-sm text-destructive">{errors.batch_name.message}</p>
                    )}
                    <p className="text-xs text-muted-foreground">
                      Creates the curriculum&apos;s first batch (cohort), with its intake year set to the
                      effective year above.
                    </p>
                  </div>
                  <div className="space-y-2 rounded-xl border bg-muted/30 p-4">
                    <Label htmlFor="semester_count">Number of Semesters</Label>
                    <Input
                      id="semester_count"
                      type="number"
                      min={1}
                      max={20}
                      placeholder="e.g. 8"
                      {...register("semester_count", { valueAsNumber: true })}
                    />
                    {errors.semester_count && (
                      <p className="text-sm text-destructive">{errors.semester_count.message}</p>
                    )}
                    <p className="text-xs text-muted-foreground">
                      Automatically creates this many semesters (Semester 1, Semester 2, …) for the
                      curriculum, ready for courses to be placed into.
                    </p>
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
