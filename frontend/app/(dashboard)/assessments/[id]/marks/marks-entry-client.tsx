"use client"

import { useState, useEffect, useRef, useCallback } from "react"
import { useQuery } from "@tanstack/react-query"
import { toast } from "sonner"
import { CheckCircle, Loader2 } from "lucide-react"

import { PageHeader } from "@/components/shared/page-header"
import { PermissionGate } from "@/components/shared/permission-gate"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"

type Enrollment = {
  id: string
  student_name: string
  roll_number: string
}

type Mark = {
  enrollment_id: string
  marks_obtained: number | null
  is_absent: boolean
}

type MarksData = {
  enrollments: Enrollment[]
  marks: Mark[]
  total_marks: number
  status: string
}

type CellState = {
  marks: number | ""
  is_absent: boolean
  saving: boolean
}

interface Props {
  assessmentId: string
}

export function MarksEntryClient({ assessmentId }: Props) {
  const [cells, setCells] = useState<Map<string, CellState>>(new Map())
  const [allSaved, setAllSaved] = useState(true)
  const debounceTimers = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map())

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.marks.byAssessment(assessmentId),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/marks/by-assessment/${assessmentId}` as never)
      return (data as unknown) as MarksData
    },
  })

  // Initialize cells from query data
  useEffect(() => {
    if (!data) return
    const map = new Map<string, CellState>()
    for (const enrollment of data.enrollments) {
      const mark = data.marks.find((m) => m.enrollment_id === enrollment.id)
      map.set(enrollment.id, {
        marks: mark?.marks_obtained ?? "",
        is_absent: mark?.is_absent ?? false,
        saving: false,
      })
    }
    setCells(map)
  }, [data])

  const saveMark = useCallback(
    async (enrollmentId: string, marks: number | "", isAbsent: boolean) => {
      setCells((prev) => {
        const next = new Map(prev)
        const cell = next.get(enrollmentId)
        if (cell) next.set(enrollmentId, { ...cell, saving: true })
        return next
      })
      setAllSaved(false)
      try {
        await apiClient.PATCH(`/marks/${enrollmentId}` as never, {
          body: { marks_obtained: marks === "" ? null : marks, is_absent: isAbsent },
        } as never)
      } catch {
        toast.error("Failed to save marks")
      } finally {
        setCells((prev) => {
          const next = new Map(prev)
          const cell = next.get(enrollmentId)
          if (cell) next.set(enrollmentId, { ...cell, saving: false })
          return next
        })
        // Check if all cells are done saving
        setAllSaved(true)
      }
    },
    []
  )

  const scheduleDebounce = useCallback(
    (enrollmentId: string, marks: number | "", isAbsent: boolean) => {
      const existing = debounceTimers.current.get(enrollmentId)
      if (existing) clearTimeout(existing)
      const timer = setTimeout(() => {
        saveMark(enrollmentId, marks, isAbsent)
        debounceTimers.current.delete(enrollmentId)
      }, 800)
      debounceTimers.current.set(enrollmentId, timer)
    },
    [saveMark]
  )

  const handleMarksChange = (enrollmentId: string, value: string) => {
    const parsed = value === "" ? "" : Number(value)
    setCells((prev) => {
      const next = new Map(prev)
      const cell = next.get(enrollmentId)
      if (cell) next.set(enrollmentId, { ...cell, marks: parsed })
      return next
    })
    const cell = cells.get(enrollmentId)
    if (cell) {
      setAllSaved(false)
      scheduleDebounce(enrollmentId, parsed, cell.is_absent)
    }
  }

  const handleAbsentChange = (enrollmentId: string, checked: boolean) => {
    setCells((prev) => {
      const next = new Map(prev)
      const cell = next.get(enrollmentId)
      if (cell) next.set(enrollmentId, { ...cell, is_absent: checked })
      return next
    })
    const cell = cells.get(enrollmentId)
    if (cell) {
      setAllSaved(false)
      scheduleDebounce(enrollmentId, checked ? "" : cell.marks, checked)
    }
  }

  if (isLoading) return <div className="animate-pulse h-40 bg-muted rounded-md" />
  if (!data) return <p className="text-muted-foreground">Assessment not found.</p>

  const isLocked = data.status === "LOCKED"
  const anySaving = Array.from(cells.values()).some((c) => c.saving)

  return (
    <div className="space-y-4">
      <PageHeader
        title="Marks Entry"
        description={`Total marks: ${data.total_marks}`}
        actions={
          <div className="flex items-center gap-2 text-sm">
            {anySaving ? (
              <span className="flex items-center gap-1 text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                Saving...
              </span>
            ) : allSaved ? (
              <span className="flex items-center gap-1 text-green-600">
                <CheckCircle className="h-4 w-4" />
                All changes saved
              </span>
            ) : null}
          </div>
        }
      />

      <div className="rounded-md border overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-muted/50">
              <th className="px-4 py-3 text-left font-medium">Student Name</th>
              <th className="px-4 py-3 text-left font-medium">Roll No</th>
              <th className="px-4 py-3 text-left font-medium">
                Marks (/{data.total_marks})
              </th>
              <th className="px-4 py-3 text-center font-medium">Absent</th>
            </tr>
          </thead>
          <tbody>
            {data.enrollments.map((enrollment) => {
              const cell = cells.get(enrollment.id)
              return (
                <tr key={enrollment.id} className="border-b last:border-0 hover:bg-muted/30">
                  <td className="px-4 py-2">{enrollment.student_name}</td>
                  <td className="px-4 py-2 text-muted-foreground">{enrollment.roll_number}</td>
                  <td className="px-4 py-2">
                    <PermissionGate
                      permission="marks.enter"
                      fallback={
                        <span>{cell?.marks === "" ? "—" : cell?.marks}</span>
                      }
                    >
                      <div className="flex items-center gap-2">
                        <input
                          type="number"
                          min={0}
                          max={data.total_marks}
                          disabled={isLocked || cell?.is_absent}
                          value={cell?.marks ?? ""}
                          onChange={(e) => handleMarksChange(enrollment.id, e.target.value)}
                          className="w-24 rounded-md border bg-background px-2 py-1 text-sm disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-ring"
                        />
                        {cell?.saving && (
                          <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />
                        )}
                      </div>
                    </PermissionGate>
                  </td>
                  <td className="px-4 py-2 text-center">
                    <PermissionGate
                      permission="marks.enter"
                      fallback={
                        <span>{cell?.is_absent ? "Yes" : "No"}</span>
                      }
                    >
                      <input
                        type="checkbox"
                        disabled={isLocked}
                        checked={cell?.is_absent ?? false}
                        onChange={(e) => handleAbsentChange(enrollment.id, e.target.checked)}
                        className="h-4 w-4 rounded border-border disabled:opacity-50 disabled:cursor-not-allowed"
                      />
                    </PermissionGate>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
