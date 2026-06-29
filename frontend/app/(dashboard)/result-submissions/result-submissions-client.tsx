"use client"

import Link from "next/link"
import { useMemo, useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { BarChart3, BookOpen, ChevronRight, GraduationCap, Loader2, Send } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { PageHeader } from "@/components/shared/page-header"
import { StatusBadge } from "@/components/shared/status-badge"
import { useHasAnyPermission } from "@/hooks/use-permission"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"
import { cn } from "@/lib/utils"

type ResultSubmission = {
  section_offering_id: string
  course_id: string
  course_code: string
  course_title: string
  batch_id: string
  batch_name: string
  academic_term_id: string
  term_name: string
  term_year: number
  term_season: string
  section_id: string
  section_name: string
  result_publication_id: string | null
  status: string
  submitted_at: string | null
  ml_rejection_comment: string | null
  student_count: number
}

const STATUS_OPTIONS: Record<string, string> = {
  ALL: "All statuses",
  DRAFT: "Not submitted",
  SUBMITTED: "Submitted",
  ML_APPROVED: "Approved (Module Leader)",
  PC_APPROVED: "Approved (Program Coordinator)",
  PUBLISHED: "Published",
}

// Determines the accent shown on a course card: the most "actionable" status
// present among its sections wins, so courses awaiting review stand out first.
const STATUS_PRIORITY = ["SUBMITTED", "ML_APPROVED", "PC_APPROVED", "DRAFT", "PUBLISHED"]

const CARD_ACCENT: Record<string, string> = {
  SUBMITTED: "border-blue-300 bg-blue-50/50 dark:border-blue-800 dark:bg-blue-950/20",
  ML_APPROVED: "border-cyan-300 bg-cyan-50/50 dark:border-cyan-800 dark:bg-cyan-950/20",
  PC_APPROVED: "border-teal-300 bg-teal-50/50 dark:border-teal-800 dark:bg-teal-950/20",
  PUBLISHED: "border-green-300 bg-green-50/50 dark:border-green-800 dark:bg-green-950/20",
  DRAFT: "border-gray-200 bg-gray-50/50 dark:border-gray-800 dark:bg-gray-900/20",
}

function courseAccentStatus(items: ResultSubmission[]): string {
  for (const status of STATUS_PRIORITY) {
    if (items.some((i) => i.status === status)) return status
  }
  return "DRAFT"
}

export function ResultSubmissionsClient() {
  const qc = useQueryClient()
  const [status, setStatus] = useState("ALL")
  const canSubmitToPC = useHasAnyPermission(["result.approve.ml"])

  const { data: submissions = [], isLoading } = useQuery({
    queryKey: queryKeys.results.submissions({ status }),
    queryFn: async () => {
      const { data } = await apiClient.GET("/results" as never, {
        params: { query: status === "ALL" ? {} : { status } },
      } as never)
      return ((data as unknown) as ResultSubmission[]) ?? []
    },
  })

  const bulkApproveMutation = useMutation({
    mutationFn: async (courseId: string) => {
      const { data } = await apiClient.POST("/results/bulk-approve-ml" as never, {
        body: { course_id: courseId },
      } as never)
      return (data as unknown) as { approved_count: number }
    },
    onSuccess: (data) => {
      toast.success(
        `Submitted ${data.approved_count} section${data.approved_count === 1 ? "" : "s"} to the Program Coordinator`
      )
      qc.invalidateQueries({ queryKey: queryKeys.results.all })
    },
    onError: () => toast.error("Failed to submit results to the Program Coordinator"),
  })

  const courseGroups = useMemo(() => {
    const map = new Map<string, { course_id: string; course_code: string; course_title: string; items: ResultSubmission[] }>()
    for (const item of submissions) {
      const group = map.get(item.course_id)
      if (group) {
        group.items.push(item)
      } else {
        map.set(item.course_id, {
          course_id: item.course_id,
          course_code: item.course_code,
          course_title: item.course_title,
          items: [item],
        })
      }
    }
    return Array.from(map.values())
  }, [submissions])

  const pendingReviewCount = submissions.filter((s) => s.status === "SUBMITTED").length

  return (
    <div className="space-y-6">
      <PageHeader
        title="Result Submissions"
        description="Section result reports submitted by section teachers, grouped by course, batch, and semester."
      />

      <div className="flex flex-wrap items-center gap-3">
        <Select value={status} onValueChange={(v) => v != null && setStatus(v as string)}>
          <SelectTrigger className="w-64">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {Object.entries(STATUS_OPTIONS).map(([value, label]) => (
              <SelectItem key={value} value={value}>{label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        {pendingReviewCount > 0 && (
          <Badge variant="secondary" className="bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-100">
            {pendingReviewCount} awaiting your review
          </Badge>
        )}
      </div>

      {isLoading && (
        <div className="grid gap-4 sm:grid-cols-2">
          {[...Array(4)].map((_, i) => <div key={i} className="h-24 bg-muted animate-pulse rounded-lg" />)}
        </div>
      )}

      {!isLoading && courseGroups.length === 0 && (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            No section result submissions found.
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        {courseGroups.map((course) => {
          const accent = courseAccentStatus(course.items)
          const total = course.items.length
          const submittedCount = course.items.filter((i) => i.status !== "DRAFT").length
          const notSubmittedCount = total - submittedCount
          const reviewCount = course.items.filter((i) => i.status === "SUBMITTED").length
          const firstItem = course.items[0]

          const isSubmitting = bulkApproveMutation.isPending && bulkApproveMutation.variables === course.course_id

          return (
            <Card key={course.course_id} className={cn("h-full", CARD_ACCENT[accent])}>
              <Link href={`/result-submissions/${course.course_id}?code=${encodeURIComponent(course.course_code)}&title=${encodeURIComponent(course.course_title)}`}>
                <CardHeader className="pb-2 transition-colors hover:bg-muted/40 rounded-t-xl">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-2">
                      <BookOpen className="h-4 w-4 text-muted-foreground shrink-0" />
                      <div>
                        <p className="font-mono text-sm font-semibold">{course.course_code}</p>
                        <p className="text-sm font-medium">{course.course_title}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <StatusBadge status={accent} />
                      <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0" />
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="pt-0 pb-3 transition-colors hover:bg-muted/40">
                  <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                    <Badge variant="outline" className="text-xs font-normal">
                      {total} section{total === 1 ? "" : "s"}
                    </Badge>
                    <Badge variant="outline" className="text-xs font-normal">
                      {submittedCount} submitted
                    </Badge>
                    <Badge variant="outline" className="text-xs font-normal">
                      {notSubmittedCount} not submitted
                    </Badge>
                    {reviewCount > 0 && (
                      <Badge className="text-xs font-normal bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-100">
                        {reviewCount} awaiting review
                      </Badge>
                    )}
                  </div>
                </CardContent>
              </Link>
              <CardContent className="flex flex-wrap gap-2 pt-0">
                <Button
                  size="sm"
                  variant="outline"
                  nativeButton={false}
                  render={
                    <Link
                      href={`/result-submissions/${course.course_id}/dashboard?code=${encodeURIComponent(course.course_code)}&title=${encodeURIComponent(course.course_title)}`}
                    />
                  }
                >
                  <BarChart3 /> Course Dashboard
                </Button>
                {firstItem && (
                  <Button
                    size="sm"
                    variant="outline"
                    nativeButton={false}
                    render={
                      <Link
                        href={`/result-submissions/batches/${firstItem.batch_id}/dashboard?batch=${encodeURIComponent(firstItem.batch_name)}`}
                      />
                    }
                  >
                    <GraduationCap /> Batch PO Dashboard
                  </Button>
                )}
              </CardContent>
              {canSubmitToPC && reviewCount > 0 && (
                <CardContent className="pt-0">
                  <Button
                    size="sm"
                    className="w-full"
                    disabled={isSubmitting}
                    onClick={() => bulkApproveMutation.mutate(course.course_id)}
                  >
                    {isSubmitting ? <Loader2 className="animate-spin" /> : <Send />}
                    Submit {reviewCount} section{reviewCount === 1 ? "" : "s"} to Program Coordinator
                  </Button>
                </CardContent>
              )}
            </Card>
          )
        })}
      </div>
    </div>
  )
}
