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
  program_id: z.string().min(1, "Program is required"),
  effective_year: z.number().int().min(1900).max(2100),
  version_number: z.number().int().min(1, "Version must be at least 1").max(99),
  batch_name: z.string().min(1, "Batch is required").max(100),
  term_structure: z.enum(["TRIMESTER", "BI_SEMESTER"]),
  threshold_co_score_pct: z.number().min(0, "0–100").max(100, "0–100"),
})
type FormValues = z.infer<typeof schema>

// The term structure fixes the semester count — trimester programs run 12
// semesters, bi-semester programs run 8. Not user-editable.
const TERM_STRUCTURES = {
  TRIMESTER: { label: "Trimester", semesters: 12 },
  BI_SEMESTER: { label: "Bi-Semester", semesters: 8 },
} as const

export function CurriculaClient() {
  const [open, setOpen] = useState(false)
  const [selProgramId, setSelProgramId] = useState("")
  const [selBatchName, setSelBatchName] = useState("")
  const [selTermStructure, setSelTermStructure] = useState<keyof typeof TERM_STRUCTURES>("TRIMESTER")
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
    defaultValues: { term_structure: "TRIMESTER", version_number: 1, threshold_co_score_pct: 50 },
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
  ]

  const mutation = useMutation({
    mutationFn: async (values: FormValues) => {
      const deptShort = selectedDept?.short_name ?? "DEPT"
      const autoName = `${deptShort}_Curriculum_${values.effective_year}_v${values.version_number}`
      const { data: curriculum } = await apiClient.POST("/curricula" as never, {
        body: {
          name: autoName,
          program_id: values.program_id,
          effective_year: values.effective_year,
          threshold_co_score_pct: values.threshold_co_score_pct,
        },
      } as never)
      const created = (curriculum as unknown) as { id: string }
      const semesterCount = TERM_STRUCTURES[values.term_structure].semesters
      await apiClient.POST("/batches" as never, {
        body: {
          curriculum_id: created.id,
          name: values.batch_name,
          start_date: `${values.effective_year}-01-01`,
          // Backend accepts TRIMESTER | SEMESTER; bi-semester maps to SEMESTER
          term_system: values.term_structure === "TRIMESTER" ? "TRIMESTER" : "SEMESTER",
          num_semesters: semesterCount,
        },
      } as never)
      await apiClient.POST(`/curricula/${created.id}/terms` as never, {
        body: Array.from({ length: semesterCount }, (_, i) => ({
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
      setSelTermStructure("TRIMESTER")
      reset({ term_structure: "TRIMESTER", version_number: 1, threshold_co_score_pct: 50 })
    },
    onError: () => toast.error("Failed to create curriculum"),
  })

  function handleClose() {
    setOpen(false)
    setSelProgramId("")
    setSelBatchName("")
    setSelTermStructure("TRIMESTER")
    reset({ term_structure: "TRIMESTER", version_number: 1, threshold_co_score_pct: 50 })
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
              <DialogContent className="sm:max-w-lg">
                <DialogHeader>
                  <DialogTitle>Create Curriculum</DialogTitle>
                </DialogHeader>
                <form
                  id="create-curriculum-form"
                  onSubmit={handleSubmit((v) => mutation.mutate(v))}
                  className="space-y-4 py-1"
                >
                  {/* Generated name — prominent preview at the top */}
                  <div className="rounded-lg border border-primary/20 bg-primary/5 px-4 py-3">
                    <p className="text-[10px] font-medium uppercase tracking-wider text-primary/60 mb-0.5">Curriculum Name</p>
                    <p className="font-mono text-sm font-semibold text-primary truncate">{generatedName}</p>
                  </div>

                  {/* Program */}
                  <div className="space-y-1.5">
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
                      <p className="text-xs text-destructive">{errors.program_id.message}</p>
                    )}
                  </div>

                  {/* Year / Version / Threshold */}
                  <div className="grid grid-cols-3 gap-3">
                    <div className="space-y-1.5">
                      <Label htmlFor="effective_year">Effective Year</Label>
                      <Input
                        id="effective_year"
                        type="number"
                        min={1900}
                        max={2100}
                        placeholder={String(new Date().getFullYear())}
                        {...register("effective_year", { valueAsNumber: true })}
                      />
                      {errors.effective_year && (
                        <p className="text-xs text-destructive">{errors.effective_year.message}</p>
                      )}
                    </div>
                    <div className="space-y-1.5">
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
                        <p className="text-xs text-destructive">{errors.version_number.message}</p>
                      )}
                    </div>
                    <div className="space-y-1.5">
                      <Label htmlFor="threshold_co_score_pct">Threshold (%)</Label>
                      <Input
                        id="threshold_co_score_pct"
                        type="number"
                        min={0}
                        max={100}
                        step="1"
                        placeholder="50"
                        {...register("threshold_co_score_pct", { valueAsNumber: true })}
                      />
                      {errors.threshold_co_score_pct && (
                        <p className="text-xs text-destructive">{errors.threshold_co_score_pct.message}</p>
                      )}
                    </div>
                  </div>

                  {/* Batch + Semesters side by side */}
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-1.5">
                      <Label>First Batch</Label>
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
                        <Input placeholder="e.g. Batch 61" {...register("batch_name")} />
                      )}
                      {errors.batch_name && (
                        <p className="text-xs text-destructive">{errors.batch_name.message}</p>
                      )}
                      <p className="text-xs text-muted-foreground">First student cohort for this curriculum.</p>
                    </div>
                    <div className="space-y-1.5">
                      <Label>Term Structure</Label>
                      <Select
                        value={selTermStructure}
                        onValueChange={(v) => {
                          if (v == null) return
                          const structure = v as keyof typeof TERM_STRUCTURES
                          setSelTermStructure(structure)
                          setValue("term_structure", structure, { shouldValidate: true })
                        }}
                      >
                        <SelectTrigger className="w-full">
                          <SelectValue>
                            {(value: string) => TERM_STRUCTURES[value as keyof typeof TERM_STRUCTURES]?.label ?? value}
                          </SelectValue>
                        </SelectTrigger>
                        <SelectContent>
                          {Object.entries(TERM_STRUCTURES).map(([value, s]) => (
                            <SelectItem key={value} value={value}>
                              {s.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <p className="text-xs text-muted-foreground">
                        Creates {TERM_STRUCTURES[selTermStructure].semesters} semesters automatically.
                      </p>
                    </div>
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
