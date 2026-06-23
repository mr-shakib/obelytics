"use client"

import { useEffect, useState, useMemo } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { Loader2, Plus, Settings, Trash2 } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogTrigger,
} from "@/components/ui/dialog"
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { PermissionGate } from "@/components/shared/permission-gate"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"

// ── Types ─────────────────────────────────────────────────────────────────────

type CourseOutcome = { id: string; code: string; statement: string }

type MarksheetQuestion = {
  id: string
  section_offering_id: string
  exam_type: string
  label: string
  max_marks: number
  course_outcome_id: string | null
  order_index: number
}

type DraftQuestion = {
  label: string
  max_marks: string
  course_outcome_id: string
}

type RawOffering = { id: string; course_id: string }

const EXAM_LABEL: Record<string, string> = { MID: "Mid Term", FINAL: "Final Exam" }
const EMPTY_QUESTION: DraftQuestion = { label: "", max_marks: "", course_outcome_id: "" }

// ── Configure Questions Dialog ────────────────────────────────────────────────
// Two-step dialog: set how many marks each CO is worth, then map individual
// exam questions to COs. Shared by both MID and FINAL at the course level.

function ConfigureQuestionsDialog({
  questions,
  courseOutcomes,
  examType,
  totalMarks,
  onSave,
  saving,
}: {
  questions: MarksheetQuestion[]
  courseOutcomes: CourseOutcome[]
  examType: string
  totalMarks: number
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

  const updateRow = (index: number, patch: Partial<DraftQuestion>) =>
    setDraft((prev) => prev.map((row, i) => (i === index ? { ...row, ...patch } : row)))

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

  const cosWithMarks = courseOutcomes.filter((co) => (Number(coTargets[co.id]) || 0) > 0)

  const handleSave = () => {
    const rows = draft.filter((row) => row.label.trim().length > 0)
    for (const row of rows) {
      const max = Number(row.max_marks)
      if (!Number.isFinite(max) || max <= 0) {
        toast.error(`"${row.label}" needs a valid marks value greater than 0`)
        return
      }
    }

    if (totalMarks > 0 && total > totalMarks) {
      toast.error(`Total marks (${total}) exceed the assigned ${totalMarks} marks for this assessment tool`)
      return
    }

    for (const co of cosWithMarks) {
      const target = Number(coTargets[co.id]) || 0
      const mapped = mappedByCo.get(co.id) ?? 0
      if (mapped > target) {
        toast.error(`${co.code} mapped marks (${mapped}) exceed its allocated ${target} marks`)
        return
      }
    }

    onSave(rows)
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={<Button variant="outline" size="sm" />}>
        <Settings className="h-3.5 w-3.5" />
        {EXAM_LABEL[examType] ?? examType}
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
                    onValueChange={(v) =>
                      updateRow(i, { course_outcome_id: v === "none" ? "" : (v as string) })
                    }
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
                      {cosWithMarks.map((co) => (
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
                  const over = mapped > target
                  const match = mapped === target
                  return (
                    <div key={co.id} className="flex items-center justify-between text-sm">
                      <span>{co.code}</span>
                      <span className={over ? "text-destructive font-medium" : match ? "text-green-600" : "text-amber-600"}>
                        {mapped} / {target} marks mapped{over ? " — exceeds!" : ""}
                      </span>
                    </div>
                  )
                })}
              </div>
            )}
            {totalMarks > 0 && (
              <p className={`text-sm font-medium ${total > totalMarks ? "text-destructive" : ""}`}>
                Total: {total} / {totalMarks}{total > totalMarks ? " — exceeds assigned marks!" : ""}
              </p>
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

// ── CourseExamConfig ──────────────────────────────────────────────────────────
// Reads questions from the first available section offering (canonical source),
// and on save writes the same questions to ALL section offerings for this course.

function CourseExamConfig({
  offeringIds,
  examType,
  courseOutcomes,
  totalMarks,
}: {
  offeringIds: string[]
  examType: "MID" | "FINAL"
  courseOutcomes: CourseOutcome[]
  totalMarks: number
}) {
  const qc = useQueryClient()
  const canonicalId = offeringIds[0] ?? ""

  const { data: questions = [] } = useQuery({
    queryKey: queryKeys.marksheets.questions(canonicalId, examType),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/marksheets/${canonicalId}/questions` as never, {
        params: { query: { exam_type: examType } },
      } as never)
      return ((data as unknown) as MarksheetQuestion[]) ?? []
    },
    enabled: !!canonicalId,
  })

  const saveQuestionsMutation = useMutation({
    mutationFn: async (draft: DraftQuestion[]) => {
      // Strip IDs — each section offering gets a fresh set of questions.
      // The PUT endpoint deletes existing questions and creates new ones when no id is provided.
      const body = {
        questions: draft.map((row, i) => ({
          label: row.label,
          max_marks: Number(row.max_marks),
          course_outcome_id: row.course_outcome_id || null,
          order_index: i,
        })),
      }
      await Promise.all(
        offeringIds.map((oid) =>
          apiClient.PUT(`/marksheets/${oid}/questions` as never, {
            params: { query: { exam_type: examType } },
            body,
          } as never)
        )
      )
    },
    onSuccess: () => {
      toast.success(`${EXAM_LABEL[examType]} questions applied to all sections`)
      for (const oid of offeringIds) {
        qc.invalidateQueries({ queryKey: queryKeys.marksheets.questions(oid, examType) })
        qc.invalidateQueries({ queryKey: queryKeys.marksheets.grid(oid, examType) })
      }
    },
    onError: () => toast.error("Failed to update questions"),
  })

  if (!canonicalId) {
    return (
      <Button variant="outline" size="sm" disabled>
        <Settings className="h-3.5 w-3.5" />
        {EXAM_LABEL[examType] ?? examType}
      </Button>
    )
  }

  return (
    <ConfigureQuestionsDialog
      questions={questions}
      courseOutcomes={courseOutcomes}
      examType={examType}
      totalMarks={totalMarks}
      onSave={(draft) => saveQuestionsMutation.mutate(draft)}
      saving={saveQuestionsMutation.isPending}
    />
  )
}

// ── QuestionConfigCard ────────────────────────────────────────────────────────

interface Props {
  courseId: string
  curriculumId: string
  midTotalMarks?: number
  finalTotalMarks?: number
}

export function QuestionConfigCard({ courseId, curriculumId, midTotalMarks = 0, finalTotalMarks = 0 }: Props) {
  const { data: offerings = [], isLoading } = useQuery({
    queryKey: queryKeys.sectionOfferings.byCourse(courseId),
    queryFn: async () => {
      const { data } = await apiClient.GET("/section-offerings" as never, {
        params: { query: { course_id: courseId } },
      } as never)
      return ((data as unknown) as RawOffering[]) ?? []
    },
  })

  const { data: courseOutcomes = [] } = useQuery({
    queryKey: queryKeys.courseOutcomes.list(curriculumId, courseId),
    queryFn: async () => {
      const { data } = await apiClient.GET("/course-outcomes" as never, {
        params: { query: { curriculum_id: curriculumId, course_id: courseId } },
      } as never)
      return ((data as unknown) as CourseOutcome[]) ?? []
    },
  })

  const offeringIds = offerings.map((o) => o.id)

  return (
    <PermissionGate permission="assessment.configure">
      <Card>
        <CardHeader>
          <CardTitle>Question Configuration</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Configure exam questions once at the course level — the same questions are applied
            to all sections automatically.
          </p>
          {isLoading ? (
            <div className="flex gap-3">
              <div className="h-9 w-28 animate-pulse rounded bg-muted" />
              <div className="h-9 w-28 animate-pulse rounded bg-muted" />
            </div>
          ) : offeringIds.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No sections have been created for this course yet.
            </p>
          ) : (
            <>
              <div className="flex flex-wrap gap-3">
                <CourseExamConfig
                  offeringIds={offeringIds}
                  examType="MID"
                  courseOutcomes={courseOutcomes}
                  totalMarks={midTotalMarks}
                />
                <CourseExamConfig
                  offeringIds={offeringIds}
                  examType="FINAL"
                  courseOutcomes={courseOutcomes}
                  totalMarks={finalTotalMarks}
                />
              </div>
              <p className="text-xs text-muted-foreground">
                Applies to {offeringIds.length} section{offeringIds.length !== 1 ? "s" : ""}.
              </p>
            </>
          )}
        </CardContent>
      </Card>
    </PermissionGate>
  )
}
