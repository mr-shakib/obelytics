"use client"

import { useState, useEffect, useRef } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useForm, Controller } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { toast } from "sonner"
import { Plus, Loader2, ListChecks } from "lucide-react"
import type { ColumnDef } from "@tanstack/react-table"
import { useResolveCourseLocation } from "@/hooks/use-course-location"
import { usePermission } from "@/hooks/use-permission"
import { PageHeader } from "@/components/shared/page-header"
import { DataTable } from "@/components/shared/data-table"
import { PermissionGate } from "@/components/shared/permission-gate"
import { BloomLevelCheckboxGroup, sortBloomLevelIds } from "@/components/shared/bloom-level-checkbox-group"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
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

// ── Types ─────────────────────────────────────────────────────────────────────

type Curriculum = { id: string; name: string; code: string; program_id: string }
type TermDef    = { id: string; term_number: number; name: string }
type CourseSlot = { id: string; curriculum_term_definition_id: string; course_id: string; is_elective: boolean }
type Course     = { id: string; code: string; title: string }
type BloomLevel = { id: string; code: string; name: string; bloom_domain_id: string; order_index: number }
type BloomDomain = { id: string; name: string }
type CourseOutcome = {
  id: string
  code: string
  statement: string
  bloom_level_ids: string[]
}
type ModuleLeaderAssignment = { course_id: string }

// ── Form schema ───────────────────────────────────────────────────────────────

const coSchema = z.object({
  code:            z.string().min(1, "Code is required").max(20),
  statement:       z.string().min(10, "At least 10 characters"),
  bloom_level_ids: z.array(z.string()),
})
type COFormValues = z.infer<typeof coSchema>

// ── Add dialog ────────────────────────────────────────────────────────────────

function CODialog({
  open,
  onOpenChange,
  bloomDomains,
  bloomLevels,
  suggestedCode,
  onSubmit,
  isPending,
}: {
  open: boolean
  onOpenChange: (v: boolean) => void
  bloomDomains: BloomDomain[]
  bloomLevels: BloomLevel[]
  suggestedCode: string
  onSubmit: (values: COFormValues) => void
  isPending: boolean
}) {
  const {
    register,
    handleSubmit,
    control,
    reset,
    formState: { errors },
  } = useForm<COFormValues>({ resolver: zodResolver(coSchema) })

  useEffect(() => {
    if (open) {
      reset({ code: suggestedCode, statement: "", bloom_level_ids: [] })
    }
  }, [open, suggestedCode, reset])

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Add Course Outcome</DialogTitle>
        </DialogHeader>
        <form id="co-form" onSubmit={handleSubmit(onSubmit)} className="space-y-4 py-2">
          <div className="space-y-2">
            <Label htmlFor="co-code">Code</Label>
            <Input id="co-code" {...register("code")} placeholder={suggestedCode} />
            {errors.code && <p className="text-sm text-destructive">{errors.code.message}</p>}
          </div>

          <div className="space-y-2">
            <Label htmlFor="co-stmt">Statement</Label>
            <Textarea
              id="co-stmt"
              {...register("statement")}
              placeholder="Describe what students will be able to do..."
              rows={4}
            />
            {errors.statement && <p className="text-sm text-destructive">{errors.statement.message}</p>}
          </div>

          <div className="space-y-2">
            <Label>Bloom Level <span className="text-muted-foreground font-normal">(optional, multiple allowed)</span></Label>
            <Controller
              name="bloom_level_ids"
              control={control}
              render={({ field }) => (
                <BloomLevelCheckboxGroup
                  bloomDomains={bloomDomains}
                  bloomLevels={bloomLevels}
                  value={field.value ?? []}
                  onChange={field.onChange}
                />
              )}
            />
          </div>
        </form>
        <DialogFooter showCloseButton>
          <Button type="submit" form="co-form" disabled={isPending}>
            {isPending && <Loader2 className="animate-spin" />}
            Add CO
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export function CourseOutcomesClient() {
  const qc = useQueryClient()
  const searchParams = useSearchParams()
  const initialCourseId = searchParams.get("course_id") ?? ""

  const router = useRouter()

  const [curriculumId, setCurriculumId] = useState("")
  const [termDefId,    setTermDefId]    = useState("")
  const [courseId,     setCourseId]     = useState("")
  const [dialogOpen,   setDialogOpen]   = useState(false)

  // ── Deep-link from a course's "Design this course" link ──────────────────

  const resolvedLocation = useResolveCourseLocation(initialCourseId)
  const appliedInitialRef = useRef(false)

  useEffect(() => {
    if (appliedInitialRef.current || !resolvedLocation) return
    appliedInitialRef.current = true
    setCurriculumId(resolvedLocation.curriculumId)
    setTermDefId(resolvedLocation.termDefId)
    setCourseId(initialCourseId)
  }, [resolvedLocation, initialCourseId])

  // ── Remote data ──────────────────────────────────────────────────────────

  const { data: curricula = [] } = useQuery({
    queryKey: queryKeys.curricula.all,
    queryFn: async () => {
      const { data } = await apiClient.GET("/curricula" as never)
      return ((data as unknown) as Curriculum[]) ?? []
    },
  })

  const { data: termDefs = [] } = useQuery({
    queryKey: queryKeys.curricula.terms(curriculumId),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/curricula/${curriculumId}/terms` as never)
      return ((data as unknown) as TermDef[]) ?? []
    },
    enabled: !!curriculumId,
  })

  const { data: courseSlots = [] } = useQuery({
    queryKey: queryKeys.curricula.courseSlots(curriculumId),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/curricula/${curriculumId}/course-slots` as never)
      return ((data as unknown) as CourseSlot[]) ?? []
    },
    enabled: !!curriculumId,
  })

  const { data: allCourses = [] } = useQuery({
    queryKey: queryKeys.courses.all,
    queryFn: async () => {
      const { data } = await apiClient.GET("/courses" as never)
      return ((data as unknown) as Course[]) ?? []
    },
  })

  const { data: bloomLevels = [] } = useQuery({
    queryKey: queryKeys.refData.bloomLevels,
    queryFn: async () => {
      const { data } = await apiClient.GET("/ref-data/bloom-levels" as never)
      return ((data as unknown) as BloomLevel[]) ?? []
    },
  })

  const { data: bloomDomains = [] } = useQuery({
    queryKey: queryKeys.refData.bloomDomains,
    queryFn: async () => {
      const { data } = await apiClient.GET("/ref-data/bloom-domains" as never)
      return ((data as unknown) as { items?: BloomDomain[] })?.items ?? ((data as unknown) as BloomDomain[]) ?? []
    },
  })

  const canManageCourses = usePermission("course.create")

  const { data: myAssignments = [] } = useQuery({
    queryKey: queryKeys.moduleLeaderAssignments.mine,
    queryFn: async () => {
      const { data } = await apiClient.GET("/module-leader-assignments/mine" as never)
      return ((data as unknown) as ModuleLeaderAssignment[]) ?? []
    },
  })

  const { data: cos = [], isLoading: cosLoading } = useQuery({
    queryKey: queryKeys.courseOutcomes.list(curriculumId, courseId),
    queryFn: async () => {
      const { data } = await apiClient.GET(
        `/course-outcomes?curriculum_id=${curriculumId}&course_id=${courseId}` as never
      )
      return ((data as unknown) as CourseOutcome[]) ?? []
    },
    enabled: !!curriculumId && !!courseId,
  })

  // ── Derived ──────────────────────────────────────────────────────────────

  const courseIdsInTerm = termDefId
    ? courseSlots
        .filter((s) => s.curriculum_term_definition_id === termDefId)
        .map((s) => s.course_id)
    : []

  const myModuleLeaderCourseIds = new Set(myAssignments.map((a) => a.course_id))

  const coursesInTerm = allCourses.filter((c) => {
    if (!courseIdsInTerm.includes(c.id)) return false
    if (!canManageCourses && myModuleLeaderCourseIds.size > 0) {
      return myModuleLeaderCourseIds.has(c.id)
    }
    return true
  })

  const bloomMap = new Map(bloomLevels.map((b) => [b.id, `${b.code} — ${b.name}`]))
  const suggestedCode = `CO${cos.length + 1}`

  const columns: ColumnDef<CourseOutcome>[] = [
    {
      accessorKey: "code",
      header: "Code",
      cell: ({ row }) => <span className="font-mono font-semibold">{row.original.code}</span>,
    },
    {
      accessorKey: "statement",
      header: "Statement",
      cell: ({ row }) => (
        <span className="whitespace-normal break-words max-w-[420px] block">
          {row.original.statement}
        </span>
      ),
    },
    {
      id: "bloom_level",
      header: "Bloom Level",
      cell: ({ row }) => {
        const ids = sortBloomLevelIds(row.original.bloom_level_ids ?? [], bloomLevels, bloomDomains)
        if (ids.length === 0) return <span className="text-muted-foreground">—</span>
        return (
          <div className="flex flex-wrap gap-1">
            {ids.map((id) => (
              <Badge key={id} variant="secondary" className="font-normal">
                {bloomMap.get(id) ?? id}
              </Badge>
            ))}
          </div>
        )
      },
    },
  ]

  // ── Mutations ────────────────────────────────────────────────────────────

  const addMutation = useMutation({
    mutationFn: async (values: COFormValues) => {
      await apiClient.POST("/course-outcomes" as never, {
        body: {
          curriculum_id: curriculumId,
          course_id: courseId,
          ...values,
        },
      } as never)
    },
    onSuccess: () => {
      toast.success("Course Outcome added")
      qc.invalidateQueries({ queryKey: queryKeys.courseOutcomes.list(curriculumId, courseId) })
      setDialogOpen(false)
    },
    onError: () => toast.error("Failed to add CO"),
  })

  // ── Handlers ─────────────────────────────────────────────────────────────

  function openAdd() {
    setDialogOpen(true)
  }

  function handleChangeCurriculum(val: string | null) {
    setCurriculumId(val ?? "")
    setTermDefId("")
    setCourseId("")
  }

  function handleChangeTerm(val: string | null) {
    setTermDefId(val ?? "")
    setCourseId("")
  }

  const selectedCourse = allCourses.find((c) => c.id === courseId)

  return (
    <div>
      <PageHeader
        title="Course Outcomes"
        description="Select a curriculum, semester and course to manage its learning outcomes."
        actions={
          courseId && (
            <PermissionGate permission="co.create">
              <Button onClick={openAdd}>
                <Plus className="h-4 w-4" />
                Add CO
              </Button>
            </PermissionGate>
          )
        }
      />

      {/* Cascading selectors */}
      <div className="rounded-xl border border-border bg-muted/30 p-4 mb-6">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div className="space-y-1.5">
            <Label className="text-xs font-medium text-muted-foreground">Curriculum</Label>
            <Select value={curriculumId} onValueChange={handleChangeCurriculum}>
              <SelectTrigger className="h-11 w-full text-sm">
                <SelectValue placeholder="Choose a curriculum">
                  {(v: string | null) => v ? (curricula.find((c) => c.id === v)?.name ?? v) : null}
                </SelectValue>
              </SelectTrigger>
              <SelectContent>
                {curricula.map((c) => (
                  <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5">
            <Label className="text-xs font-medium text-muted-foreground">Semester</Label>
            <Select value={termDefId} onValueChange={handleChangeTerm} disabled={!curriculumId}>
              <SelectTrigger className="h-11 w-full text-sm">
                <SelectValue placeholder={curriculumId ? "Choose a semester" : "Select a curriculum first"}>
                  {(v: string | null) => {
                    const t = termDefs.find((td) => td.id === v)
                    return t ? `Sem ${t.term_number} — ${t.name}` : null
                  }}
                </SelectValue>
              </SelectTrigger>
              <SelectContent>
                {termDefs.map((t) => (
                  <SelectItem key={t.id} value={t.id}>Sem {t.term_number} — {t.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5">
            <Label className="text-xs font-medium text-muted-foreground">Course</Label>
            <Select value={courseId} onValueChange={(v) => setCourseId(v ?? "")} disabled={!termDefId}>
              <SelectTrigger className="h-11 w-full text-sm">
                <SelectValue placeholder={termDefId ? "Choose a course" : "Select a semester first"}>
                  {(v: string | null) => {
                    const c = coursesInTerm.find((co) => co.id === v)
                    return c ? `${c.code} — ${c.title}` : null
                  }}
                </SelectValue>
              </SelectTrigger>
              <SelectContent>
                {coursesInTerm.length === 0 && (
                  <SelectItem value="__none__" disabled>No courses in this semester</SelectItem>
                )}
                {coursesInTerm.map((c) => (
                  <SelectItem key={c.id} value={c.id}>{c.code} — {c.title}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      </div>

      {/* CO list */}
      {!courseId && (
        <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed border-border p-12 text-center">
          <ListChecks className="h-8 w-8 text-muted-foreground/50" />
          <p className="text-sm text-muted-foreground">
            Select a curriculum, semester, and course above to see its outcomes.
          </p>
        </div>
      )}

      {courseId && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">
              {selectedCourse ? `${selectedCourse.code} — ${selectedCourse.title}` : ""}
            </span>
            <span className="text-xs text-muted-foreground">{cos.length} outcome{cos.length !== 1 ? "s" : ""}</span>
          </div>

          <DataTable
            columns={columns}
            data={cos}
            loading={cosLoading}
            onRowClick={(row) => router.push(`/course-outcomes/${row.id}`)}
            emptyMessage="No outcomes yet."
          />
        </div>
      )}

      <CODialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        bloomDomains={bloomDomains}
        bloomLevels={bloomLevels}
        suggestedCode={suggestedCode}
        onSubmit={(v) => addMutation.mutate(v)}
        isPending={addMutation.isPending}
      />
    </div>
  )
}
