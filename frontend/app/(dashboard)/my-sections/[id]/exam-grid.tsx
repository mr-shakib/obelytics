"use client"

import { useEffect, useState, useCallback, useMemo } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { Loader2, Settings, Plus, Trash2 } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent } from "@/components/ui/card"
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogTrigger,
} from "@/components/ui/dialog"
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select"
import {
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell,
} from "@/components/ui/table"
import {
  Tabs, TabsList, TabsTrigger, TabsContent,
} from "@/components/ui/tabs"
import { useHasAnyPermission } from "@/hooks/use-permission"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"
import { cn } from "@/lib/utils"

// ── Types ──────────────────────────────────────────────────────────────────────

type CourseOutcome = {
  id: string
  code: string
  statement: string
  status: string
}

type MarksheetQuestion = {
  id: string
  section_offering_id: string
  exam_type: string
  label: string
  max_marks: number
  course_outcome_id: string | null
  order_index: number
}

type MarkCell = {
  mark_id: string | null
  marks_obtained: number | null
  is_absent: boolean
}

type StudentRow = {
  enrollment_id: string
  student_id_number: string
  full_name: string
  marks: Record<string, MarkCell>
  total: number
}

type GridResponse = {
  section_offering_id: string
  exam_type: string
  questions: MarksheetQuestion[]
  students: StudentRow[]
}

type DraftQuestion = {
  id?: string
  label: string
  max_marks: string
  course_outcome_id: string
}

type CellState = {
  value: number | ""
}

interface Props {
  sectionOfferingId: string
  examType: "MID" | "FINAL"
  courseOutcomes: CourseOutcome[]
  locked?: boolean
}

const EXAM_LABEL: Record<string, string> = { MID: "Mid Term", FINAL: "Final Exam" }

const EMPTY_QUESTION: DraftQuestion = { label: "", max_marks: "", course_outcome_id: "" }

// ── Configure Questions dialog ───────────────────────────────────────────────
// Section teachers define the actual questions on the exam paper (e.g. Q1, Q2a,
// Q2b), set how many marks each is worth, and map each one to a course outcome.
// Multiple questions can map to the same CO — PO attainment is then computed
// automatically from the CO-PO mapping.

function ConfigureQuestionsDialog({
  questions,
  courseOutcomes,
  examType,
  onSave,
  saving,
}: {
  questions: MarksheetQuestion[]
  courseOutcomes: CourseOutcome[]
  examType: string
  onSave: (questions: DraftQuestion[]) => void
  saving: boolean
}) {
  const [open, setOpen] = useState(false)
  const [step, setStep] = useState<"co-marks" | "questions">("co-marks")
  const [draft, setDraft] = useState<DraftQuestion[]>([])
  const [coTargets, setCoTargets] = useState<Record<string, string>>({})

  useEffect(() => {
    if (!open) return
    setStep("co-marks")
    if (questions.length > 0) {
      setDraft(
        [...questions]
          .sort((a, b) => a.order_index - b.order_index)
          .map((q) => ({
            id: q.id,
            label: q.label,
            max_marks: String(q.max_marks),
            course_outcome_id: q.course_outcome_id ?? "",
          }))
      )
    } else {
      setDraft([{ ...EMPTY_QUESTION }])
    }
    const targets: Record<string, string> = {}
    for (const co of courseOutcomes) {
      const sum = questions
        .filter((q) => q.course_outcome_id === co.id)
        .reduce((s, q) => s + Number(q.max_marks), 0)
      targets[co.id] = sum > 0 ? String(sum) : ""
    }
    setCoTargets(targets)
  }, [open, questions, courseOutcomes])

  const updateRow = (index: number, patch: Partial<DraftQuestion>) => {
    setDraft((prev) => prev.map((row, i) => (i === index ? { ...row, ...patch } : row)))
  }

  const addRow = () => setDraft((prev) => [...prev, { ...EMPTY_QUESTION }])

  const removeRow = (index: number) => setDraft((prev) => prev.filter((_, i) => i !== index))

  const total = draft.reduce((sum, row) => sum + (Number(row.max_marks) || 0), 0)

  const mappedByCo = useMemo(() => {
    const map = new Map<string, number>()
    for (const row of draft) {
      if (!row.course_outcome_id) continue
      map.set(row.course_outcome_id, (map.get(row.course_outcome_id) ?? 0) + (Number(row.max_marks) || 0))
    }
    return map
  }, [draft])

  const coTargetTotal = Object.values(coTargets).reduce((sum, v) => sum + (Number(v) || 0), 0)

  const cosWithTargetsOrMappings = courseOutcomes.filter(
    (co) => (Number(coTargets[co.id]) || 0) > 0 || (mappedByCo.get(co.id) ?? 0) > 0
  )

  const handleSave = () => {
    const rows = draft.filter((row) => row.label.trim().length > 0)
    for (const row of rows) {
      const max = Number(row.max_marks)
      if (!Number.isFinite(max) || max <= 0) {
        toast.error(`"${row.label}" needs a valid marks value greater than 0`)
        return
      }
    }
    onSave(rows)
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={<Button variant="outline" size="sm" />}>
        <Settings className="h-3.5 w-3.5" />
        Configure Questions
      </DialogTrigger>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>{EXAM_LABEL[examType] ?? examType} — Questions</DialogTitle>
        </DialogHeader>

        <Tabs value={step} onValueChange={(v) => setStep(v as "co-marks" | "questions")} className="min-w-0">
          <TabsList className="w-full">
            <TabsTrigger value="co-marks" className="flex-1">1. CO Marks</TabsTrigger>
            <TabsTrigger value="questions" className="flex-1">2. Map Questions</TabsTrigger>
          </TabsList>

          <TabsContent value="co-marks" className="space-y-3 pt-3">
            <p className="text-sm text-muted-foreground">
              Decide how many marks each course outcome is worth in this{" "}
              {EXAM_LABEL[examType]?.toLowerCase() ?? "exam"}. You&apos;ll map individual
              questions to these COs next.
            </p>
            {courseOutcomes.length === 0 ? (
              <p className="text-sm text-muted-foreground">No course outcomes defined for this course yet.</p>
            ) : (
              <div className="space-y-2 max-h-80 overflow-y-auto pr-1">
                {courseOutcomes.map((co) => (
                  <div key={co.id} className="flex items-center gap-2">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium">{co.code}</p>
                      <p className="text-xs text-muted-foreground line-clamp-2">{co.statement}</p>
                    </div>
                    <Input
                      type="number"
                      min={0}
                      step="0.5"
                      placeholder="0"
                      value={coTargets[co.id] ?? ""}
                      onChange={(e) => setCoTargets((prev) => ({ ...prev, [co.id]: e.target.value }))}
                      className="w-20"
                    />
                  </div>
                ))}
              </div>
            )}
            <p className="text-sm font-medium">Total allocated: {coTargetTotal}</p>
          </TabsContent>

          <TabsContent value="questions" className="space-y-3 pt-3">
            <p className="text-sm text-muted-foreground">
              Add one row per question on the exam paper, set how many marks it&apos;s worth, and
              choose the course outcome it assesses. Multiple questions can map to the same CO —
              PO attainment is calculated automatically from these mappings.
            </p>
            <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
              {draft.map((row, i) => (
                <div key={i} className="flex items-center gap-2">
                  <Input
                    placeholder={`Q${i + 1}`}
                    value={row.label}
                    onChange={(e) => updateRow(i, { label: e.target.value })}
                    className="flex-1"
                  />
                  <Input
                    type="number"
                    min={0}
                    step="0.5"
                    placeholder="Marks"
                    value={row.max_marks}
                    onChange={(e) => updateRow(i, { max_marks: e.target.value })}
                    className="w-20"
                  />
                  <Select
                    value={row.course_outcome_id || "none"}
                    onValueChange={(v) => updateRow(i, { course_outcome_id: v === "none" ? "" : (v as string) })}
                  >
                    <SelectTrigger className="w-28">
                      <SelectValue placeholder="CO">
                        {row.course_outcome_id
                          ? courseOutcomes.find((co) => co.id === row.course_outcome_id)?.code
                          : "—"}
                      </SelectValue>
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">—</SelectItem>
                      {courseOutcomes.map((co) => (
                        <SelectItem key={co.id} value={co.id}>{co.code}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    onClick={() => removeRow(i)}
                    disabled={draft.length === 1}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              ))}
            </div>
            <Button type="button" variant="outline" size="sm" onClick={addRow} className="gap-1.5">
              <Plus className="h-3.5 w-3.5" />
              Add Question
            </Button>
            <p className="text-sm font-medium">Total: {total}</p>

            {cosWithTargetsOrMappings.length > 0 && (
              <div className="rounded-md border p-2 space-y-1">
                <p className="text-xs font-medium text-muted-foreground">CO mark check</p>
                {cosWithTargetsOrMappings.map((co) => {
                  const target = Number(coTargets[co.id]) || 0
                  const mapped = mappedByCo.get(co.id) ?? 0
                  const match = mapped === target
                  return (
                    <div key={co.id} className="flex items-center justify-between text-sm">
                      <span>{co.code}</span>
                      <span className={match ? "text-green-600" : "text-amber-600"}>
                        {mapped} / {target} marks mapped
                      </span>
                    </div>
                  )
                })}
              </div>
            )}
          </TabsContent>
        </Tabs>

        <DialogFooter>
          {step === "co-marks" ? (
            <>
              <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
              <Button onClick={() => setStep("questions")}>Next: Map Questions</Button>
            </>
          ) : (
            <>
              <Button variant="outline" onClick={() => setStep("co-marks")}>Back</Button>
              <Button disabled={saving} onClick={handleSave}>
                {saving && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                Save
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ── Main exam grid ────────────────────────────────────────────────────────────

export function ExamGrid({ sectionOfferingId, examType, courseOutcomes, locked }: Props) {
  const qc = useQueryClient()
  const canManage = useHasAnyPermission(["marks.enter", "assessment.configure"]) && !locked

  const [cells, setCells] = useState<Map<string, CellState>>(new Map())
  const [absent, setAbsent] = useState<Map<string, boolean>>(new Map())
  const [dirtyCells, setDirtyCells] = useState<Set<string>>(new Set())
  const [dirtyRows, setDirtyRows] = useState<Set<string>>(new Set())

  const { data: questions = [], isLoading: loadingQuestions } = useQuery({
    queryKey: queryKeys.marksheets.questions(sectionOfferingId, examType),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/marksheets/${sectionOfferingId}/questions` as never, {
        params: { query: { exam_type: examType } },
      } as never)
      return ((data as unknown) as MarksheetQuestion[]) ?? []
    },
  })

  const { data: grid, isLoading: loadingGrid } = useQuery({
    queryKey: queryKeys.marksheets.grid(sectionOfferingId, examType),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/marksheets/${sectionOfferingId}/grid` as never, {
        params: { query: { exam_type: examType } },
      } as never)
      return (data as unknown) as GridResponse
    },
  })

  // Initialize local cell/absent state from grid data
  useEffect(() => {
    if (!grid) return
    const cellMap = new Map<string, CellState>()
    const absentMap = new Map<string, boolean>()
    for (const student of grid.students) {
      let rowAbsent = false
      for (const q of grid.questions) {
        const cell = student.marks[q.id]
        cellMap.set(`${student.enrollment_id}:${q.id}`, {
          value: cell?.marks_obtained != null ? Number(cell.marks_obtained) : "",
        })
        if (cell?.is_absent) rowAbsent = true
      }
      absentMap.set(student.enrollment_id, rowAbsent)
    }
    setCells(cellMap)
    setAbsent(absentMap)
    setDirtyCells(new Set())
    setDirtyRows(new Set())
  }, [grid])

  // Warn before leaving the page if there are unsaved mark changes
  useEffect(() => {
    if (dirtyCells.size === 0 && dirtyRows.size === 0) return
    const handler = (e: BeforeUnloadEvent) => e.preventDefault()
    window.addEventListener("beforeunload", handler)
    return () => window.removeEventListener("beforeunload", handler)
  }, [dirtyCells, dirtyRows])

  const invalidateAll = useCallback(() => {
    qc.invalidateQueries({ queryKey: queryKeys.marksheets.grid(sectionOfferingId, examType) })
    qc.invalidateQueries({ queryKey: queryKeys.marksheets.attainment(sectionOfferingId) })
  }, [qc, sectionOfferingId, examType])

  const saveQuestionsMutation = useMutation({
    mutationFn: async (draft: DraftQuestion[]) => {
      await apiClient.PUT(`/marksheets/${sectionOfferingId}/questions` as never, {
        params: { query: { exam_type: examType } },
        body: {
          questions: draft.map((row, i) => ({
            id: row.id,
            label: row.label,
            max_marks: Number(row.max_marks),
            course_outcome_id: row.course_outcome_id || null,
            order_index: i,
          })),
        },
      } as never)
    },
    onSuccess: () => {
      toast.success("Questions updated")
      qc.invalidateQueries({ queryKey: queryKeys.marksheets.questions(sectionOfferingId, examType) })
      invalidateAll()
    },
    onError: () => toast.error("Failed to update questions"),
  })

  const handleCellChange = (enrollmentId: string, questionId: string, raw: string) => {
    const value = raw === "" ? "" : Number(raw)
    const key = `${enrollmentId}:${questionId}`
    setCells((prev) => {
      const next = new Map(prev)
      next.set(key, { value })
      return next
    })
    setDirtyCells((prev) => new Set(prev).add(key))
  }

  const toggleAbsent = (enrollmentId: string, checked: boolean) => {
    setAbsent((prev) => new Map(prev).set(enrollmentId, checked))
    setDirtyRows((prev) => new Set(prev).add(enrollmentId))
  }

  const hasUnsavedChanges = dirtyCells.size > 0 || dirtyRows.size > 0

  const saveMarksMutation = useMutation({
    mutationFn: async () => {
      type MarkUpdate = { question_id: string; student_enrollment_id: string; marks_obtained: number | null; is_absent: boolean }
      const updates = new Map<string, MarkUpdate>()

      for (const enrollmentId of dirtyRows) {
        const rowAbsent = absent.get(enrollmentId) ?? false
        for (const q of questions) {
          const key = `${enrollmentId}:${q.id}`
          const value = cells.get(key)?.value ?? ""
          updates.set(key, {
            question_id: q.id,
            student_enrollment_id: enrollmentId,
            marks_obtained: rowAbsent ? null : (value === "" ? 0 : value),
            is_absent: rowAbsent,
          })
        }
      }

      for (const key of dirtyCells) {
        if (updates.has(key)) continue
        const [enrollmentId, questionId] = key.split(":")
        const rowAbsent = absent.get(enrollmentId) ?? false
        const value = cells.get(key)?.value ?? ""
        if (!rowAbsent && value === "") continue
        updates.set(key, {
          question_id: questionId,
          student_enrollment_id: enrollmentId,
          marks_obtained: rowAbsent ? null : (value === "" ? 0 : value),
          is_absent: rowAbsent,
        })
      }

      await Promise.all(
        Array.from(updates.values()).map((body) =>
          apiClient.PATCH(`/marksheets/${sectionOfferingId}/marks` as never, { body } as never)
        )
      )
    },
    onSuccess: () => {
      toast.success("Marks saved")
      setDirtyCells(new Set())
      setDirtyRows(new Set())
      invalidateAll()
    },
    onError: () => toast.error("Failed to save marks"),
  })

  const totalMaxMarks = useMemo(
    () => questions.reduce((sum, q) => sum + Number(q.max_marks), 0),
    [questions]
  )

  const mappedCoCount = useMemo(
    () => new Set(questions.filter((q) => q.course_outcome_id).map((q) => q.course_outcome_id)).size,
    [questions]
  )

  const rowTotal = (enrollmentId: string) =>
    questions.reduce((sum, q) => {
      const cell = cells.get(`${enrollmentId}:${q.id}`)
      return sum + (typeof cell?.value === "number" ? cell.value : 0)
    }, 0)

  if (loadingQuestions || loadingGrid) {
    return <div className="h-64 animate-pulse bg-muted rounded-lg" />
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          {questions.length > 0
            ? `${questions.length} question${questions.length === 1 ? "" : "s"} · ${totalMaxMarks} total marks · ${mappedCoCount} CO${mappedCoCount === 1 ? "" : "s"} mapped`
            : "No questions configured for this exam yet."}
        </p>
        {canManage ? (
          <div className="flex items-center gap-3">
            {hasUnsavedChanges && (
              <span className="text-sm text-amber-600">Unsaved changes</span>
            )}
            <Button
              size="sm"
              onClick={() => saveMarksMutation.mutate()}
              disabled={!hasUnsavedChanges || saveMarksMutation.isPending}
            >
              {saveMarksMutation.isPending && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
              Save Marks
            </Button>
            <ConfigureQuestionsDialog
              questions={questions}
              courseOutcomes={courseOutcomes}
              examType={examType}
              onSave={(draft) => saveQuestionsMutation.mutate(draft)}
              saving={saveQuestionsMutation.isPending}
            />
          </div>
        ) : (
          locked && <span className="text-sm text-muted-foreground">Locked</span>
        )}
      </div>

      {questions.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            {canManage
              ? `Configure the questions for the ${EXAM_LABEL[examType]?.toLowerCase() ?? "exam"} to start entering marks.`
              : `${EXAM_LABEL[examType] ?? examType} marks have not been configured yet.`}
          </CardContent>
        </Card>
      ) : !grid || grid.students.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            No students enrolled in this section.
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-10">SL</TableHead>
                  <TableHead>ID</TableHead>
                  <TableHead>Name</TableHead>
                  {questions.map((q) => {
                    const co = courseOutcomes.find((c) => c.id === q.course_outcome_id)
                    return (
                      <TableHead key={q.id} className="text-center">
                        <div>{q.label}</div>
                        <div className="text-xs font-normal text-muted-foreground">
                          /{Number(q.max_marks)}{co && co.code !== q.label ? ` · ${co.code}` : ""}
                        </div>
                      </TableHead>
                    )
                  })}
                  <TableHead className="text-center">Total (/{totalMaxMarks})</TableHead>
                  <TableHead className="text-center">Absent</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {grid.students.map((student, idx) => {
                  const rowAbsent = absent.get(student.enrollment_id) ?? false
                  return (
                    <TableRow key={student.enrollment_id}>
                      <TableCell className="text-muted-foreground">{idx + 1}</TableCell>
                      <TableCell className="font-mono text-xs">{student.student_id_number}</TableCell>
                      <TableCell>{student.full_name}</TableCell>
                      {questions.map((q) => {
                        const key = `${student.enrollment_id}:${q.id}`
                        const cell = cells.get(key)
                        const dirty = dirtyCells.has(key) || dirtyRows.has(student.enrollment_id)
                        return (
                          <TableCell key={q.id} className="text-center">
                            {canManage ? (
                              <Input
                                type="number"
                                min={0}
                                max={Number(q.max_marks)}
                                step="0.5"
                                disabled={rowAbsent}
                                value={cell?.value ?? ""}
                                onChange={(e) => handleCellChange(student.enrollment_id, q.id, e.target.value)}
                                className={cn(
                                  "h-8 w-16 px-1 text-center mx-auto disabled:opacity-40",
                                  "[appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none",
                                  dirty && "border-amber-500 ring-1 ring-amber-500/30"
                                )}
                              />
                            ) : (
                              <span>{rowAbsent ? "AB" : cell?.value ?? "—"}</span>
                            )}
                          </TableCell>
                        )
                      })}
                      <TableCell className="text-center font-medium">
                        {rowAbsent ? "AB" : rowTotal(student.enrollment_id)}
                      </TableCell>
                      <TableCell className="text-center">
                        {canManage ? (
                          <input
                            type="checkbox"
                            checked={rowAbsent}
                            onChange={(e) => toggleAbsent(student.enrollment_id, e.target.checked)}
                            className="h-4 w-4 rounded border-border"
                          />
                        ) : (
                          <span>{rowAbsent ? "Yes" : "No"}</span>
                        )}
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
