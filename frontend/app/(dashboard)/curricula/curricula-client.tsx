"use client"

import { useState, useMemo } from "react"
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

type Program = { id: string; title?: string; name?: string; acronym?: string; department_id?: string }
type Department = { id: string; name: string; short_name: string }
type Batch = { id: string; name: string }

function programLabel(p: Program) {
  const title = p.title ?? p.name ?? ""
  return p.acronym ? `${p.acronym} — ${title}` : title || p.id
}

const schema = z.object({
  code: z.string().min(1, "Code is required").max(50),
  program_id: z.string().min(1, "Program is required"),
  effective_year: z.number().int().min(1900).max(2100),
  version_number: z.number().int().min(1, "Version must be at least 1").max(99),
  batch_name: z.string().min(1, "Batch is required").max(100),
  semester_count: z.number().int().min(1, "At least 1 semester is required").max(20),
  threshold_co_score_pct: z.number().min(0, "0–100").max(100, "0–100"),
  threshold_student_pct: z.number().min(0, "0–100").max(100, "0–100"),
})
type FormValues = z.infer<typeof schema>

export function CurriculaClient() {
  const [open, setOpen] = useState(false)
  const [selProgramId, setSelProgramId] = useState("")
  const [selBatchName, setSelBatchName] = useState("")
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

  const { data: departments = [] } = useQuery({
    queryKey: queryKeys.departments.all,
    queryFn: async () => {
      const { data } = await apiClient.GET("/departments" as never)
      return ((data as unknown) as Department[]) ?? []
    },
  })

  const { data: batches = [] } = useQuery({
    queryKey: queryKeys.batches.all,
    queryFn: async () => {
      const { data } = await apiClient.GET("/batches" as never)
      return ((data as unknown) as Batch[]) ?? []
    },
  })

  const programById = Object.fromEntries(programs.map((p) => [p.id, p]))
  const deptById = Object.fromEntries(departments.map((d) => [d.id, d]))

  // Deduplicate batch names for the dropdown
  const uniqueBatchNames = useMemo(() => {
    const seen = new Set<string>()
    return batches.filter((b) => {
      if (seen.has(b.name)) return false
      seen.add(b.name)
      return true
    })
  }, [batches])

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { semester_count: 12, version_number: 1, threshold_co_score_pct: 50, threshold_student_pct: 50 },
  })

  const watchedYear = watch("effective_year")
  const watchedVersion = watch("version_number")

  const selectedProgram = selProgramId ? programById[selProgramId] : undefined
  const selectedDept = selectedProgram?.department_id ? deptById[selectedProgram.department_id] : undefined

  const generatedName = useMemo(() => {
    const deptShort = selectedDept?.short_name ?? "DEPT"
    const year = watchedYear > 1900 ? watchedYear : new Date().getFullYear()
    const version = watchedVersion >= 1 ? watchedVersion : 1
    return `${deptShort}_Curriculum_${year}_v${version}`
  }, [selectedDept, watchedYear, watchedVersion])

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

  const mutation = useMutation({
    mutationFn: async (values: FormValues) => {
      const deptShort = selectedDept?.short_name ?? "DEPT"
      const autoName = `${deptShort}_Curriculum_${values.effective_year}_v${values.version_number}`
      const { data: curriculum } = await apiClient.POST("/curricula" as never, {
        body: {
          name: autoName,
          code: values.code,
          program_id: values.program_id,
          effective_year: values.effective_year,
          threshold_co_score_pct: values.threshold_co_score_pct,
          threshold_student_pct: values.threshold_student_pct,
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
      setSelBatchName("")
      reset({ semester_count: 12, version_number: 1, threshold_co_score_pct: 50, threshold_student_pct: 50 })
    },
    onError: () => toast.error("Failed to create curriculum"),
  })

  function handleClose() {
    setOpen(false)
    setSelProgramId("")
    setSelBatchName("")
    reset({ semester_count: 12, version_number: 1, threshold_co_score_pct: 50, threshold_student_pct: 50 })
  }

  return (
    <div>
      <PageHeader
        title="Curricula"
        description="Manage academic curricula across programs."
        actions={
          <PermissionGate permission="curriculum.create">
            <Dialog open={open} onOpenChange={(v) => { if (v) setOpen(true); else handleClose() }}>
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
                  {/* Program */}
                  <div className="space-y-2">
                    <Label>Program</Label>
                    <Select
                      value={selProgramId}
                      onValueChange={(v) => {
                        if (v == null) return
                        setSelProgramId(v as string)
                        setValue("program_id", v as string, { shouldValidate: true })
                      }}
                    >
                      <SelectTrigger className="w-full">
                        <SelectValue placeholder="Select program">
                          {(value: string) =>
                            value ? (programById[value] ? programLabel(programById[value]) : value) : null
                          }
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

                  {/* Code / Year / Version */}
                  <div className="grid grid-cols-3 gap-3">
                    <div className="space-y-2">
                      <Label htmlFor="code">Code</Label>
                      <Input id="code" placeholder="CSE-2024" {...register("code")} />
                      {errors.code && (
                        <p className="text-sm text-destructive">{errors.code.message}</p>
                      )}
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="effective_year">Year</Label>
                      <Input
                        id="effective_year"
                        type="number"
                        min={1900}
                        max={2100}
                        placeholder="2024"
                        {...register("effective_year", { valueAsNumber: true })}
                      />
                      {errors.effective_year && (
                        <p className="text-sm text-destructive">{errors.effective_year.message}</p>
                      )}
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="version_number">Version</Label>
                      <Input
                        id="version_number"
                        type="number"
                        min={1}
                        max={99}
                        placeholder="1"
                        {...register("version_number", { valueAsNumber: true })}
                      />
                      {errors.version_number && (
                        <p className="text-sm text-destructive">{errors.version_number.message}</p>
                      )}
                    </div>
                  </div>

                  {/* Auto-generated name preview */}
                  <div className="rounded-xl border bg-muted/30 px-4 py-3">
                    <p className="text-xs text-muted-foreground mb-1">Generated curriculum name</p>
                    <p className="font-mono text-sm font-medium">{generatedName}</p>
                  </div>

                  {/* Batch */}
                  <div className="space-y-2 rounded-xl border bg-muted/30 p-4">
                    <Label>Batch</Label>
                    {uniqueBatchNames.length > 0 ? (
                      <Select
                        value={selBatchName}
                        onValueChange={(v) => {
                          if (v == null) return
                          setSelBatchName(v as string)
                          setValue("batch_name", v as string, { shouldValidate: true })
                        }}
                      >
                        <SelectTrigger className="w-full">
                          <SelectValue placeholder="Select batch">
                            {(value: string) => value || null}
                          </SelectValue>
                        </SelectTrigger>
                        <SelectContent>
                          {uniqueBatchNames.map((b) => (
                            <SelectItem key={b.id} value={b.name}>
                              {b.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    ) : (
                      <Input
                        placeholder="e.g. Batch 61"
                        {...register("batch_name")}
                      />
                    )}
                    {errors.batch_name && (
                      <p className="text-sm text-destructive">{errors.batch_name.message}</p>
                    )}
                    <p className="text-xs text-muted-foreground">
                      Creates the curriculum&apos;s first batch (cohort), with its intake year set to the
                      effective year above.
                    </p>
                  </div>

                  {/* Semester count */}
                  <div className="space-y-2 rounded-xl border bg-muted/30 p-4">
                    <Label htmlFor="semester_count">Number of Semesters</Label>
                    <Input
                      id="semester_count"
                      type="number"
                      min={1}
                      max={20}
                      placeholder="8"
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

                  {/* Attainment thresholds */}
                  <div className="space-y-3 rounded-xl border bg-muted/30 p-4">
                    <Label>Attainment Thresholds</Label>
                    <div className="grid grid-cols-2 gap-3">
                      <div className="space-y-2">
                        <Label htmlFor="threshold_co_score_pct" className="text-xs font-normal text-muted-foreground">
                          CO/PO pass mark (%)
                        </Label>
                        <Input
                          id="threshold_co_score_pct"
                          type="number"
                          min={0}
                          max={100}
                          step="0.01"
                          {...register("threshold_co_score_pct", { valueAsNumber: true })}
                        />
                        {errors.threshold_co_score_pct && (
                          <p className="text-sm text-destructive">{errors.threshold_co_score_pct.message}</p>
                        )}
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="threshold_student_pct" className="text-xs font-normal text-muted-foreground">
                          Students attaining (%)
                        </Label>
                        <Input
                          id="threshold_student_pct"
                          type="number"
                          min={0}
                          max={100}
                          step="0.01"
                          {...register("threshold_student_pct", { valueAsNumber: true })}
                        />
                        {errors.threshold_student_pct && (
                          <p className="text-sm text-destructive">{errors.threshold_student_pct.message}</p>
                        )}
                      </div>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      A student attains a CO/PO when their score reaches the pass mark. A CO is
                      considered attained when at least this share of students attain it. Defaults to 50% each.
                    </p>
                  </div>
                </form>
                <DialogFooter>
                  <Button
                    variant="outline"
                    onClick={handleClose}
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
