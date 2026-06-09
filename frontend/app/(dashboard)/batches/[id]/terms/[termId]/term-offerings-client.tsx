"use client"

import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import Link from "next/link"
import { toast } from "sonner"
import { ArrowLeft, Plus, Trash2, Loader2, BookOpen } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { StatusBadge } from "@/components/shared/status-badge"
import { PageHeader } from "@/components/shared/page-header"
import { usePermission } from "@/hooks/use-permission"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"
import { formatDate } from "@/lib/utils"

type OfferingInfo = {
  id: string
  section_id: string
  section_name: string
  capacity: number | null
  status: string
}

type OfferingCourse = {
  course_id: string
  curriculum_term_definition_id: string
  code: string
  title: string
  credits: number
  theory_hours: number
  lab_hours: number
  is_elective: boolean
  offerings: OfferingInfo[]
}

type BatchDetail = {
  id: string
  name: string
  term_calendar: Array<{
    academic_term_id: string
    name: string
    season: string
    year: number
    start_date: string
    end_date: string
    status: string
    term_number: number
  }>
}

const NEXT_SECTION_LABEL = (count: number) =>
  String.fromCharCode(65 + count) // A, B, C…

interface Props {
  batchId: string
  termId: string
}

function AddSectionInline({
  courseId,
  existingCount,
  onAdd,
}: {
  courseId: string
  existingCount: number
  onAdd: (courseId: string, name: string) => void
}) {
  const [open, setOpen] = useState(false)
  const [name, setName] = useState("")

  const suggested = NEXT_SECTION_LABEL(existingCount)

  const submit = () => {
    const label = (name.trim() || suggested).toUpperCase()
    if (!label) return
    onAdd(courseId, label)
    setName("")
    setOpen(false)
  }

  if (!open) {
    return (
      <Button
        size="sm"
        variant="outline"
        className="h-7 text-xs gap-1"
        onClick={() => setOpen(true)}
      >
        <Plus className="h-3 w-3" />
        Add Section
      </Button>
    )
  }

  return (
    <div className="flex items-center gap-2">
      <Input
        autoFocus
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder={suggested}
        className="h-7 w-20 text-xs"
        maxLength={20}
        onKeyDown={(e) => {
          if (e.key === "Enter") submit()
          if (e.key === "Escape") setOpen(false)
        }}
      />
      <Button size="sm" className="h-7 text-xs" onClick={submit}>Add</Button>
      <Button size="sm" variant="ghost" className="h-7 text-xs" onClick={() => setOpen(false)}>
        Cancel
      </Button>
    </div>
  )
}

export function TermOfferingsClient({ batchId, termId }: Props) {
  const qc = useQueryClient()
  const canManage = usePermission("section_offering.create")
  const [deletingId, setDeletingId] = useState<string | null>(null)

  // Fetch batch to get the term info for the header
  const { data: batch } = useQuery({
    queryKey: queryKeys.batches.detail(batchId),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/batches/${batchId}` as never)
      return (data as unknown) as BatchDetail
    },
  })

  const termInfo = batch?.term_calendar?.find((t) => t.academic_term_id === termId)

  const { data: courses = [], isLoading } = useQuery({
    queryKey: queryKeys.batches.termOfferings(batchId, termId),
    queryFn: async () => {
      const { data } = await apiClient.GET(
        `/batches/${batchId}/terms/${termId}/offerings` as never
      )
      return ((data as unknown) as OfferingCourse[]) ?? []
    },
  })

  const addMutation = useMutation({
    mutationFn: async ({ courseId, sectionName }: { courseId: string; sectionName: string }) => {
      await apiClient.POST(`/batches/${batchId}/terms/${termId}/offerings` as never, {
        body: { course_id: courseId, section_name: sectionName },
      } as never)
    },
    onSuccess: () => {
      toast.success("Section added")
      qc.invalidateQueries({ queryKey: queryKeys.batches.termOfferings(batchId, termId) })
    },
    onError: (err: unknown) => {
      const msg = (err as { detail?: string })?.detail
      toast.error(msg ?? "Failed to add section")
    },
  })

  const deleteMutation = useMutation({
    mutationFn: async (offeringId: string) => {
      setDeletingId(offeringId)
      await apiClient.DELETE(`/section-offerings/${offeringId}` as never)
    },
    onSuccess: () => {
      toast.success("Section removed")
      qc.invalidateQueries({ queryKey: queryKeys.batches.termOfferings(batchId, termId) })
    },
    onError: () => toast.error("Failed to remove section"),
    onSettled: () => setDeletingId(null),
  })

  const totalOfferings = courses.reduce((s, c) => s + c.offerings.length, 0)
  const totalCredits = courses.reduce((s, c) => s + c.credits, 0)

  return (
    <div className="max-w-5xl space-y-6">
      {/* Back nav */}
      <Link
        href={`/batches/${batchId}`}
        className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to {batch?.name ?? "Batch"}
      </Link>

      <PageHeader
        title={termInfo ? `${termInfo.name} — Section Offerings` : "Section Offerings"}
        description={
          termInfo
            ? `${formatDate(termInfo.start_date)} – ${formatDate(termInfo.end_date)}`
            : undefined
        }
        actions={termInfo && <StatusBadge status={termInfo.status} />}
      />

      {/* Summary strip */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: "Courses This Semester", value: courses.length },
          { label: "Total Credits",          value: totalCredits },
          { label: "Section Offerings",      value: totalOfferings },
        ].map(({ label, value }) => (
          <Card key={label} className="py-4">
            <CardContent className="text-center">
              <p className="text-2xl font-bold">{value}</p>
              <p className="text-xs text-muted-foreground mt-1">{label}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Course-by-course offerings */}
      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-24 animate-pulse bg-muted rounded-lg" />
          ))}
        </div>
      ) : courses.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            No courses assigned to this semester in the curriculum.
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {courses.map((course) => (
            <Card key={course.course_id}>
              <CardHeader className="pb-2">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-center gap-3">
                    <BookOpen className="h-4 w-4 text-muted-foreground mt-0.5 shrink-0" />
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-sm font-semibold">{course.code}</span>
                        <span className="text-sm font-medium">{course.title}</span>
                        {course.is_elective ? (
                          <Badge variant="outline" className="text-xs">Elective</Badge>
                        ) : (
                          <Badge variant="secondary" className="text-xs">Core</Badge>
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        {course.credits} credits · {course.theory_hours}h theory · {course.lab_hours}h lab
                      </p>
                    </div>
                  </div>
                  {canManage && (
                    <AddSectionInline
                      courseId={course.course_id}
                      existingCount={course.offerings.length}
                      onAdd={(courseId, sectionName) =>
                        addMutation.mutate({ courseId, sectionName })
                      }
                    />
                  )}
                </div>
              </CardHeader>

              <CardContent>
                {course.offerings.length === 0 ? (
                  <p className="text-xs text-muted-foreground italic">
                    No sections offered yet.
                    {canManage && ' Use "Add Section" to define one.'}
                  </p>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    {course.offerings.map((o) => (
                      <div
                        key={o.id}
                        className="flex items-center gap-2 border border-border rounded-lg px-3 py-1.5 text-sm bg-muted/30"
                      >
                        <span className="font-semibold">Section {o.section_name}</span>
                        {o.capacity != null && (
                          <span className="text-xs text-muted-foreground">cap {o.capacity}</span>
                        )}
                        <StatusBadge status={o.status} />
                        {canManage && (
                          <button
                            type="button"
                            className="text-muted-foreground hover:text-destructive transition-colors ml-1"
                            disabled={deletingId === o.id}
                            onClick={() => deleteMutation.mutate(o.id)}
                            title="Remove section"
                          >
                            {deletingId === o.id ? (
                              <Loader2 className="h-3.5 w-3.5 animate-spin" />
                            ) : (
                              <Trash2 className="h-3.5 w-3.5" />
                            )}
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
