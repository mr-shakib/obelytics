"use client"

import { useState, useEffect, useRef } from "react"
import { useSearchParams } from "next/navigation"
import { useQuery, useQueries, useMutation, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { Grid3x3 } from "lucide-react"
import { useResolveCourseLocation } from "@/hooks/use-course-location"
import { usePermission } from "@/hooks/use-permission"
import { PageHeader } from "@/components/shared/page-header"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { cn } from "@/lib/utils"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"

// ── Types ──────────────────────────────────────────────────────────────────────

type Curriculum  = { id: string; name: string; program_id: string }
type TermDef     = { id: string; term_number: number; name: string }
type CourseSlot  = { id: string; curriculum_term_definition_id: string; course_id: string }
type Course      = { id: string; code: string; title: string }
type CourseOutcome = { id: string; code: string; statement: string }

type ComplexOption = { id: string; code: string; name: string | null; description: string; is_active: boolean }

type ComplexMapping = {
  id: string
  course_outcome_id: string
  status: string
  complex_problem_id?: string
  complex_activity_id?: string
}

const EMPTY_COS: CourseOutcome[] = []
const EMPTY_OPTIONS: ComplexOption[] = []
const EMPTY_MAPPINGS: ComplexMapping[] = []

// ── Per-kind configuration ───────────────────────────────────────────────────

export type ComplexMappingKind = "cp" | "ca"

const KIND_CONFIG: Record<
  ComplexMappingKind,
  {
    title: string
    description: string
    optionsPath: "/complex-problems" | "/complex-activities"
    optionsQueryKey: readonly unknown[]
    mappingsPath: "/mappings/co-cp" | "/mappings/co-ca"
    optionField: "complex_problem_id" | "complex_activity_id"
    managePermission: string
    approvePermission: string
    columnLabel: string
  }
> = {
  cp: {
    title: "CO-CP Mapping",
    description:
      "Map course outcomes to Complex Engineering Problems (CEP). Required for any CO mapped to PO1–PO7. Click a cell to add, then approve, then remove.",
    optionsPath: "/complex-problems",
    optionsQueryKey: queryKeys.refData.complexProblems,
    mappingsPath: "/mappings/co-cp",
    optionField: "complex_problem_id",
    managePermission: "mapping.co_cp.manage",
    approvePermission: "mapping.co_cp.approve",
    columnLabel: "CEP",
  },
  ca: {
    title: "CO-CA Mapping",
    description:
      "Map course outcomes to Complex Engineering Activities (CEA). Required for any CO mapped to PO10. Click a cell to add, then approve, then remove.",
    optionsPath: "/complex-activities",
    optionsQueryKey: queryKeys.refData.complexActivities,
    mappingsPath: "/mappings/co-ca",
    optionField: "complex_activity_id",
    managePermission: "mapping.co_ca.manage",
    approvePermission: "mapping.co_ca.approve",
    columnLabel: "CEA",
  },
}

function getOptionId(mapping: ComplexMapping, kind: ComplexMappingKind): string | undefined {
  return kind === "cp" ? mapping.complex_problem_id : mapping.complex_activity_id
}

// ── Component ─────────────────────────────────────────────────────────────────

export function ComplexMappingClient({ kind }: { kind: ComplexMappingKind }) {
  const config = KIND_CONFIG[kind]
  const qc = useQueryClient()
  const searchParams = useSearchParams()
  const initialCourseId = searchParams.get("course_id") ?? ""

  const canManage = usePermission(config.managePermission)
  const canApprove = usePermission(config.approvePermission)

  const [curriculumId, setCurriculumId] = useState("")
  const [termDefId,    setTermDefId]    = useState("")
  const [courseId,     setCourseId]     = useState("")

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

  // ── Data fetching ────────────────────────────────────────────────────────

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

  const { data: cos = EMPTY_COS } = useQuery({
    queryKey: queryKeys.courseOutcomes.list(curriculumId, courseId),
    queryFn: async () => {
      const { data } = await apiClient.GET(
        `/course-outcomes?curriculum_id=${curriculumId}&course_id=${courseId}` as never
      )
      return ((data as unknown) as CourseOutcome[]) ?? []
    },
    enabled: !!curriculumId && !!courseId,
  })

  const { data: options = EMPTY_OPTIONS } = useQuery({
    queryKey: config.optionsQueryKey,
    queryFn: async () => {
      const { data } = await apiClient.GET(config.optionsPath as never)
      return ((data as unknown) as ComplexOption[]) ?? []
    },
  })

  const activeOptions = options.filter((o) => o.is_active)

  const mappingQueries = useQueries({
    queries: cos.map((co) => ({
      queryKey: queryKeys.complexMappings.byCo(kind, co.id),
      queryFn: async () => {
        const { data } = await apiClient.GET(
          `${config.mappingsPath}?course_outcome_id=${co.id}` as never
        )
        return ((data as unknown) as ComplexMapping[]) ?? []
      },
    })),
  })

  const mappingsByCo = new Map<string, ComplexMapping[]>()
  cos.forEach((co, i) => {
    mappingsByCo.set(co.id, mappingQueries[i]?.data ?? EMPTY_MAPPINGS)
  })

  // ── Derived ──────────────────────────────────────────────────────────────

  const courseIdsInTerm = termDefId
    ? courseSlots
        .filter((s) => s.curriculum_term_definition_id === termDefId)
        .map((s) => s.course_id)
    : []

  const coursesInTerm = allCourses.filter((c) => courseIdsInTerm.includes(c.id))
  const selectedCourse = allCourses.find((c) => c.id === courseId)
  const hasMatrix = !!courseId && cos.length > 0 && activeOptions.length > 0

  // ── Handlers ─────────────────────────────────────────────────────────────

  function handleChangeCurriculum(val: string | null) {
    setCurriculumId(val ?? "")
    setTermDefId("")
    setCourseId("")
  }

  function handleChangeTerm(val: string | null) {
    setTermDefId(val ?? "")
    setCourseId("")
  }

  function handleChangeCourse(val: string | null) {
    setCourseId(val ?? "")
  }

  // ── Mutations ────────────────────────────────────────────────────────────

  const invalidateCo = (coId: string) =>
    qc.invalidateQueries({ queryKey: queryKeys.complexMappings.byCo(kind, coId) })

  const createMutation = useMutation({
    mutationFn: async ({ coId, optionId }: { coId: string; optionId: string }) => {
      await apiClient.POST(config.mappingsPath as never, {
        body: { course_outcome_id: coId, [config.optionField]: optionId },
      } as never)
    },
    onSuccess: (_data, vars) => invalidateCo(vars.coId),
    onError: () => toast.error("Failed to add mapping"),
  })

  const approveMutation = useMutation({
    mutationFn: async (vars: { mappingId: string; coId: string }) => {
      await apiClient.POST(`${config.mappingsPath}/${vars.mappingId}/approve` as never, {} as never)
    },
    onSuccess: (_data, vars) => invalidateCo(vars.coId),
    onError: () => toast.error("Failed to approve mapping"),
  })

  const deleteMutation = useMutation({
    mutationFn: async (vars: { mappingId: string; coId: string }) => {
      await apiClient.DELETE(`${config.mappingsPath}/${vars.mappingId}` as never)
    },
    onSuccess: (_data, vars) => invalidateCo(vars.coId),
    onError: () => toast.error("Failed to remove mapping"),
  })

  const isMutating = createMutation.isPending || approveMutation.isPending || deleteMutation.isPending

  function handleCellClick(co: CourseOutcome, option: ComplexOption) {
    if (!canManage || isMutating) return
    const mappings = mappingsByCo.get(co.id) ?? []
    const existing = mappings.find((m) => getOptionId(m, kind) === option.id)

    if (!existing) {
      createMutation.mutate({ coId: co.id, optionId: option.id })
    } else if (existing.status === "DRAFT" && canApprove) {
      approveMutation.mutate({ mappingId: existing.id, coId: co.id })
    } else {
      deleteMutation.mutate({ mappingId: existing.id, coId: co.id })
    }
  }

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="space-y-4">
      <PageHeader title={config.title} description={config.description} />

      {/* Selectors */}
      <div className="rounded-xl border border-border bg-muted/30 p-4">
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
            <Select value={courseId} onValueChange={handleChangeCourse} disabled={!termDefId}>
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

        {/* Legend */}
        {hasMatrix && (
          <div className="mt-4 flex items-center gap-3 text-xs text-muted-foreground">
            <span className="flex items-center gap-1">
              <span className="w-5 h-5 inline-flex items-center justify-center rounded border border-dashed border-muted-foreground/30 text-muted-foreground/40 text-xs">—</span>
              Not mapped
            </span>
            <span className="flex items-center gap-1">
              <span className="w-5 h-5 inline-flex items-center justify-center rounded text-xs font-bold bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300">D</span>
              Draft{canManage && !canApprove ? " (click to remove)" : canApprove ? " (click to approve)" : ""}
            </span>
            <span className="flex items-center gap-1">
              <span className="w-5 h-5 inline-flex items-center justify-center rounded text-xs font-bold bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300">A</span>
              Approved{canManage ? " (click to remove)" : ""}
            </span>
          </div>
        )}
      </div>

      {/* Empty states */}
      {!courseId && (
        <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed border-border p-12 text-center">
          <Grid3x3 className="h-8 w-8 text-muted-foreground/50" />
          <p className="text-sm text-muted-foreground">
            {!curriculumId
              ? `Select a curriculum, semester, and course above to view or edit its ${config.columnLabel} mapping.`
              : !termDefId
              ? "Now select a semester."
              : "Now select a course."}
          </p>
        </div>
      )}

      {courseId && cos.length === 0 && (
        <div className="border border-dashed border-border rounded-lg p-12 text-center text-sm text-muted-foreground">
          No course outcomes for{" "}
          <strong>{selectedCourse ? `${selectedCourse.code} — ${selectedCourse.title}` : "this course"}</strong>.
          Add COs on the Course Outcomes page first.
        </div>
      )}

      {courseId && cos.length > 0 && activeOptions.length === 0 && (
        <div className="border border-dashed border-border rounded-lg p-12 text-center text-sm text-muted-foreground">
          No {config.columnLabel} options configured. Add some on the Complex Attributes page.
        </div>
      )}

      {/* Matrix */}
      {hasMatrix && (
        <div className="overflow-x-auto rounded-md border">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="bg-muted/50">
                <th className="px-3 py-2 text-left font-medium border-b border-r min-w-[200px] sticky left-0 bg-muted/50 z-10">
                  CO / {config.columnLabel}
                </th>
                {activeOptions.map((option) => (
                  <th
                    key={option.id}
                    className="px-2 py-2 text-center font-medium border-b border-r min-w-[64px] max-w-[64px]"
                    title={option.description}
                  >
                    {option.code}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {cos.map((co, i) => (
                <tr key={co.id} className={cn("hover:bg-muted/30", i % 2 !== 0 && "bg-muted/10")}>
                  <td
                    className="px-3 py-2 border-b border-r font-mono font-semibold text-xs sticky left-0 bg-background z-10"
                    title={co.statement}
                  >
                    {co.code}
                  </td>
                  {activeOptions.map((option) => {
                    const mappings = mappingsByCo.get(co.id) ?? []
                    const existing = mappings.find((m) => getOptionId(m, kind) === option.id)
                    const status = existing?.status ?? null
                    const cellTitle = `${co.code} × ${option.code}${status ? ` — ${status === "DRAFT" ? "Draft" : "Approved"}` : ""}`

                    const badge = status === "APPROVED" ? (
                      <span className="w-7 h-7 inline-flex items-center justify-center rounded text-xs font-bold bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300">
                        A
                      </span>
                    ) : status === "DRAFT" ? (
                      <span className="w-7 h-7 inline-flex items-center justify-center rounded text-xs font-bold bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300">
                        D
                      </span>
                    ) : (
                      <span className="w-7 h-7 inline-flex items-center justify-center rounded border border-dashed border-muted-foreground/20 text-muted-foreground/30 text-xs">
                        —
                      </span>
                    )

                    return (
                      <td key={option.id} className="border-b border-r text-center p-0">
                        {canManage ? (
                          <button
                            type="button"
                            className="w-full h-9 flex items-center justify-center hover:bg-accent/50 transition-colors disabled:opacity-50"
                            onClick={() => handleCellClick(co, option)}
                            disabled={isMutating}
                            title={cellTitle}
                          >
                            {badge}
                          </button>
                        ) : (
                          <div className="h-9 flex items-center justify-center" title={cellTitle}>
                            {badge}
                          </div>
                        )}
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
