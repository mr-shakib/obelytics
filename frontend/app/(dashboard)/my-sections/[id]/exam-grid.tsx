"use client"

import { useEffect, useState, useCallback, useMemo, useRef } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { Loader2, Upload, Download } from "lucide-react"
import * as XLSX from "xlsx"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent } from "@/components/ui/card"
import {
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell,
} from "@/components/ui/table"
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

// ── Main exam grid ────────────────────────────────────────────────────────────

export function ExamGrid({ sectionOfferingId, examType, courseOutcomes, locked }: Props) {
  const qc = useQueryClient()
  const canEnterMarks = useHasAnyPermission(["marks.enter"]) && !locked

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

  const hasOverMaxMarks = useMemo(() => {
    for (const key of dirtyCells) {
      const [enrollmentId, questionId] = key.split(":")
      const q = questions.find((q) => q.id === questionId)
      const cell = cells.get(key)
      if (q && typeof cell?.value === "number" && cell.value > Number(q.max_marks)) {
        return true
      }
    }
    return false
  }, [dirtyCells, questions, cells])

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

  // ── Bulk Import ──────────────────────────────────────────────────────────

  const fileInputRef = useRef<HTMLInputElement>(null)

  function downloadTemplate() {
    const headers = ["Student ID", ...questions.map((q) => q.label)]
    const sampleRow = grid?.students.slice(0, 2).map((s) => [s.student_id_number, ...questions.map(() => "")]) ?? []
    const ws = XLSX.utils.aoa_to_sheet([headers, ...sampleRow])
    ws["!cols"] = [{ wch: 18 }, ...questions.map(() => ({ wch: 10 }))]
    const wb = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(wb, ws, "Marks")
    XLSX.writeFile(wb, `${examType}_marks_template.xlsx`)
  }

  function handleBulkImport(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    e.target.value = ""

    const reader = new FileReader()
    reader.onload = (evt) => {
      try {
        const wb = XLSX.read(evt.target?.result, { type: "array" })
        const ws = wb.Sheets[wb.SheetNames[0]]
        const rows = XLSX.utils.sheet_to_json<Record<string, unknown>>(ws)

        if (rows.length === 0) {
          toast.error("No data found in the file")
          return
        }

        const questionMap = new Map(questions.map((q) => [q.label.toLowerCase(), q]))
        const studentMap = new Map(grid?.students.map((s) => [s.student_id_number, s]) ?? [])
        let updated = 0
        let skipped = 0
        const newCells = new Map(cells)
        const newDirty = new Set(dirtyCells)

        for (const row of rows) {
          const studentId = String(row["Student ID"] ?? row["student_id"] ?? Object.values(row)[0] ?? "").trim()
          if (!studentId) continue

          const student = studentMap.get(studentId)
          if (!student) { skipped++; continue }

          for (const [col, val] of Object.entries(row)) {
            const colLower = col.toLowerCase().trim()
            if (colLower === "student id" || colLower === "student_id") continue

            const question = questionMap.get(colLower)
            if (!question) continue

            const marks = Number(val)
            if (!Number.isFinite(marks) || marks < 0) continue

            const key = `${student.enrollment_id}:${question.id}`
            newCells.set(key, { value: marks })
            newDirty.add(key)
            updated++
          }
        }

        setCells(newCells)
        setDirtyCells(newDirty)
        toast.success(`Imported ${updated} marks${skipped ? ` (${skipped} students not found)` : ""}`)
      } catch {
        toast.error("Failed to parse Excel file")
      }
    }
    reader.readAsArrayBuffer(file)
  }

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
        {canEnterMarks ? (
          <div className="flex items-center gap-3">
            {hasOverMaxMarks && (
              <span className="text-sm text-red-600 font-medium">Some marks exceed maximum</span>
            )}
            {hasUnsavedChanges && !hasOverMaxMarks && (
              <span className="text-sm text-amber-600">Unsaved changes</span>
            )}
            {questions.length > 0 && grid && grid.students.length > 0 && (
              <>
                <Button variant="outline" size="sm" onClick={downloadTemplate}>
                  <Download className="h-3.5 w-3.5" />
                  Template
                </Button>
                <Button variant="outline" size="sm" onClick={() => fileInputRef.current?.click()}>
                  <Upload className="h-3.5 w-3.5" />
                  Bulk Import
                </Button>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".xlsx,.xls,.csv"
                  className="hidden"
                  onChange={handleBulkImport}
                />
              </>
            )}
            <Button
              size="sm"
              onClick={() => saveMarksMutation.mutate()}
              disabled={!hasUnsavedChanges || hasOverMaxMarks || saveMarksMutation.isPending}
            >
              {saveMarksMutation.isPending && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
              Save Marks
            </Button>
          </div>
        ) : (
          locked && <span className="text-sm text-muted-foreground">Locked</span>
        )}
      </div>

      {questions.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            {EXAM_LABEL[examType] ?? examType} questions have not been configured yet.
            Use the Question Configuration section to set them up.
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
                            {canEnterMarks ? (
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
                                  typeof cell?.value === "number" && cell.value > Number(q.max_marks)
                                    ? "border-red-500 ring-1 ring-red-500/30 bg-red-50 dark:bg-red-950/20"
                                    : dirty && "border-amber-500 ring-1 ring-amber-500/30"
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
                        {canEnterMarks ? (
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
