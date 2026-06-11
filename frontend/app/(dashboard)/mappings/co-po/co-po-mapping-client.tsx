"use client"

import { useState, useEffect, useRef } from "react"
import Link from "next/link"
import { useSearchParams } from "next/navigation"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { Loader2, Save, Grid3x3, AlertTriangle, CheckCircle2, ArrowRight } from "lucide-react"
import { useResolveCourseLocation } from "@/hooks/use-course-location"
import { PageHeader } from "@/components/shared/page-header"
import { PermissionGate } from "@/components/shared/permission-gate"
import { Button } from "@/components/ui/button"
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
type ProgramOutcome = { id: string; code: string; statement: string }
type CourseOutcome  = { id: string; code: string; statement: string }

type MappingSet = { id: string }
type MappingEntry = {
  id: string
  mapping_set_id: string
  course_outcome_id: string
  program_outcome_id: string
  weight: 1 | 2 | 3
}

type ValidationIssue = {
  course_outcome_id: string
  course_outcome_code: string
  missing_cep: boolean
  missing_cea: boolean
}
type ValidationResponse = { is_valid: boolean; issues: ValidationIssue[] }

// ── Helpers ───────────────────────────────────────────────────────────────────

type Weight = 1 | 2 | 3

const WEIGHT_LABELS: Record<Weight, string> = { 1: "L", 2: "M", 3: "H" }
const WEIGHT_COLORS: Record<Weight, string> = {
  1: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300",
  2: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300",
  3: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300",
}

function nextWeight(w: Weight | null): Weight | null {
  if (w === null) return 1
  if (w === 1) return 2
  if (w === 2) return 3
  return null
}

function matrixKey(coId: string, poId: string) {
  return `${coId}:${poId}`
}

const EMPTY_ENTRIES: MappingEntry[] = []

// ── Component ─────────────────────────────────────────────────────────────────

export function CoPoMappingClient() {
  const qc = useQueryClient()
  const searchParams = useSearchParams()
  const initialCourseId = searchParams.get("course_id") ?? ""

  const [curriculumId, setCurriculumId] = useState("")
  const [termDefId,    setTermDefId]    = useState("")
  const [courseId,     setCourseId]     = useState("")
  const [setId,        setSetId]        = useState<string | null>(null)
  const [matrix,       setMatrix]       = useState<Map<string, Weight>>(new Map())
  const [dirty,        setDirty]        = useState(false)

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

  const selectedCurriculum = curricula.find((c) => c.id === curriculumId)
  const programId = selectedCurriculum?.program_id ?? ""

  const { data: pos = [] } = useQuery({
    queryKey: queryKeys.programOutcomes.list({ program_id: programId }),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/program-outcomes?program_id=${programId}` as never)
      return ((data as unknown) as ProgramOutcome[]) ?? []
    },
    enabled: !!programId,
  })

  const { data: cos = [] } = useQuery({
    queryKey: queryKeys.courseOutcomes.list(curriculumId, courseId),
    queryFn: async () => {
      const { data } = await apiClient.GET(
        `/course-outcomes?curriculum_id=${curriculumId}&course_id=${courseId}` as never
      )
      return ((data as unknown) as CourseOutcome[]) ?? []
    },
    enabled: !!curriculumId && !!courseId,
  })

  // ── Existing mapping set ─────────────────────────────────────────────────

  const { data: existingSet } = useQuery({
    queryKey: queryKeys.coPoMappings.byCourse(curriculumId, courseId),
    queryFn: async () => {
      try {
        const { data, response } = await apiClient.GET(
          `/mappings/co-po?curriculum_id=${curriculumId}&course_id=${courseId}` as never
        ) as { data: unknown; response: Response }
        if (response.status === 404) return null
        return ((data as unknown) as MappingSet) ?? null
      } catch {
        return null
      }
    },
    enabled: !!curriculumId && !!courseId,
    retry: false,
  })

  const { data: existingEntries = EMPTY_ENTRIES } = useQuery({
    queryKey: queryKeys.coPoMappings.entries(setId ?? ""),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/mappings/co-po/${setId}/entries` as never)
      return ((data as unknown) as MappingEntry[]) ?? []
    },
    enabled: !!setId,
  })

  const { data: validation } = useQuery({
    queryKey: queryKeys.coPoMappings.validation(setId ?? ""),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/mappings/co-po/${setId}/validate` as never)
      return ((data as unknown) as ValidationResponse) ?? null
    },
    enabled: !!setId,
  })

  // ── Sync state from loaded data ──────────────────────────────────────────

  useEffect(() => {
    if (existingSet !== undefined) {
      setSetId(existingSet?.id ?? null)
    }
  }, [existingSet])

  useEffect(() => {
    const m = new Map<string, Weight>()
    for (const e of existingEntries) {
      m.set(matrixKey(e.course_outcome_id, e.program_outcome_id), e.weight)
    }
    setMatrix(m)
    setDirty(false)
  }, [existingEntries])

  // ── Derived ──────────────────────────────────────────────────────────────

  const courseIdsInTerm = termDefId
    ? courseSlots
        .filter((s) => s.curriculum_term_definition_id === termDefId)
        .map((s) => s.course_id)
    : []

  const coursesInTerm = allCourses.filter((c) => courseIdsInTerm.includes(c.id))
  const selectedCourse = allCourses.find((c) => c.id === courseId)
  const hasMatrix = !!courseId && cos.length > 0 && pos.length > 0

  // ── Handlers ─────────────────────────────────────────────────────────────

  function handleChangeCurriculum(val: string | null) {
    setCurriculumId(val ?? "")
    setTermDefId("")
    setCourseId("")
    setSetId(null)
    setMatrix(new Map())
    setDirty(false)
  }

  function handleChangeTerm(val: string | null) {
    setTermDefId(val ?? "")
    setCourseId("")
    setSetId(null)
    setMatrix(new Map())
    setDirty(false)
  }

  function handleChangeCourse(val: string | null) {
    setCourseId(val ?? "")
    setSetId(null)
    setMatrix(new Map())
    setDirty(false)
  }

  function toggleCell(coId: string, poId: string) {
    const key = matrixKey(coId, poId)
    setMatrix((prev) => {
      const next = new Map(prev)
      const current = prev.get(key) ?? null
      const nextVal = nextWeight(current)
      if (nextVal === null) next.delete(key)
      else next.set(key, nextVal)
      return next
    })
    setDirty(true)
  }

  // ── Save ─────────────────────────────────────────────────────────────────

  const saveMutation = useMutation({
    mutationFn: async () => {
      const { data: setData } = await apiClient.POST("/mappings/co-po" as never, {
        body: { curriculum_id: curriculumId, course_id: courseId },
      } as never) as { data: unknown }
      const resolvedSetId = (setData as MappingSet).id

      const entries = Array.from(matrix.entries()).map(([key, weight]) => {
        const [course_outcome_id, program_outcome_id] = key.split(":")
        return { course_outcome_id, program_outcome_id, weight }
      })

      await apiClient.PUT(`/mappings/co-po/${resolvedSetId}/entries` as never, {
        body: entries,
      } as never)

      return resolvedSetId
    },
    onSuccess: (resolvedSetId: string) => {
      toast.success("CO-PO mapping saved")
      setSetId(resolvedSetId)
      setDirty(false)
      qc.invalidateQueries({ queryKey: queryKeys.coPoMappings.entries(resolvedSetId) })
      qc.invalidateQueries({ queryKey: queryKeys.coPoMappings.byCourse(curriculumId, courseId) })
      qc.invalidateQueries({ queryKey: queryKeys.coPoMappings.validation(resolvedSetId) })
    },
    onError: () => toast.error("Failed to save mapping"),
  })

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="space-y-4">
      <PageHeader
        title="CO-PO Mapping"
        description="Map course outcomes to program outcomes per course. Click cells to cycle: empty → Low → Medium → High → empty."
        actions={
          dirty && (
            <PermissionGate permission="mapping.co_po.update">
              <Button onClick={() => saveMutation.mutate()} disabled={saveMutation.isPending}>
                {saveMutation.isPending ? <Loader2 className="animate-spin" /> : <Save />}
                Save Matrix
              </Button>
            </PermissionGate>
          )
        }
      />

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
            {([1, 2, 3] as Weight[]).map((w) => (
              <span key={w} className="flex items-center gap-1">
                <span className={cn(
                  "w-5 h-5 inline-flex items-center justify-center rounded text-xs font-bold",
                  WEIGHT_COLORS[w]
                )}>
                  {WEIGHT_LABELS[w]}
                </span>
                {w === 1 ? "Low" : w === 2 ? "Medium" : "High"}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Empty states */}
      {!courseId && (
        <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed border-border p-12 text-center">
          <Grid3x3 className="h-8 w-8 text-muted-foreground/50" />
          <p className="text-sm text-muted-foreground">
            {!curriculumId
              ? "Select a curriculum, semester, and course above to view or edit its CO-PO mapping."
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

      {courseId && cos.length > 0 && pos.length === 0 && (
        <div className="border border-dashed border-border rounded-lg p-12 text-center text-sm text-muted-foreground">
          No program outcomes found for this curriculum&apos;s program.
        </div>
      )}

      {/* Matrix */}
      {hasMatrix && (
        <div className="overflow-x-auto rounded-md border">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="bg-muted/50">
                <th className="px-3 py-2 text-left font-medium border-b border-r min-w-[200px] sticky left-0 bg-muted/50 z-10">
                  CO / PO
                </th>
                {pos.map((po) => (
                  <th
                    key={po.id}
                    className="px-2 py-2 text-center font-medium border-b border-r min-w-[54px] max-w-[54px]"
                    title={po.statement}
                  >
                    {po.code}
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
                  {pos.map((po) => {
                    const key    = matrixKey(co.id, po.id)
                    const weight = matrix.get(key) ?? null
                    return (
                      <td key={po.id} className="border-b border-r text-center p-0">
                        <PermissionGate
                          permission="mapping.co_po.update"
                          fallback={
                            <div className="h-9 flex items-center justify-center">
                              {weight !== null && (
                                <span className={cn(
                                  "w-7 h-7 inline-flex items-center justify-center rounded text-xs font-bold",
                                  WEIGHT_COLORS[weight]
                                )}>
                                  {WEIGHT_LABELS[weight]}
                                </span>
                              )}
                            </div>
                          }
                        >
                          <button
                            type="button"
                            className="w-full h-9 flex items-center justify-center hover:bg-accent/50 transition-colors"
                            onClick={() => toggleCell(co.id, po.id)}
                            title={`${co.code} × ${po.code}${weight ? ` — ${weight === 1 ? "Low" : weight === 2 ? "Medium" : "High"}` : ""}`}
                          >
                            {weight !== null ? (
                              <span className={cn(
                                "w-7 h-7 inline-flex items-center justify-center rounded text-xs font-bold",
                                WEIGHT_COLORS[weight]
                              )}>
                                {WEIGHT_LABELS[weight]}
                              </span>
                            ) : (
                              <span className="w-7 h-7 inline-flex items-center justify-center rounded border border-dashed border-muted-foreground/20 text-muted-foreground/30 text-xs">
                                —
                              </span>
                            )}
                          </button>
                        </PermissionGate>
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* CEP/CEA validation checklist */}
      {hasMatrix && validation && (
        <div className={cn(
          "rounded-xl border p-4",
          validation.is_valid
            ? "border-green-200 bg-green-50 dark:border-green-900/40 dark:bg-green-900/10"
            : "border-amber-200 bg-amber-50 dark:border-amber-900/40 dark:bg-amber-900/10"
        )}>
          {validation.is_valid ? (
            <div className="flex items-center gap-2 text-sm text-green-800 dark:text-green-300">
              <CheckCircle2 className="h-4 w-4" />
              All COs mapped to PO1–PO7 have a CEP mapping, and all COs mapped to PO10 have a CEA mapping.
            </div>
          ) : (
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-sm font-medium text-amber-800 dark:text-amber-300">
                <AlertTriangle className="h-4 w-4" />
                Some course outcomes are missing required CEP/CEA mappings
              </div>
              <ul className="space-y-1.5 text-sm">
                {validation.issues.map((issue) => (
                  <li key={issue.course_outcome_id} className="flex flex-wrap items-center gap-2">
                    <span className="font-mono font-semibold">{issue.course_outcome_code}</span>
                    {issue.missing_cep && (
                      <Link
                        href={`/mappings/co-cp?course_id=${courseId}`}
                        className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800 hover:bg-amber-200 dark:bg-amber-900/30 dark:text-amber-300"
                      >
                        Missing CEP <ArrowRight className="h-3 w-3" />
                      </Link>
                    )}
                    {issue.missing_cea && (
                      <Link
                        href={`/mappings/co-ca?course_id=${courseId}`}
                        className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800 hover:bg-amber-200 dark:bg-amber-900/30 dark:text-amber-300"
                      >
                        Missing CEA <ArrowRight className="h-3 w-3" />
                      </Link>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
