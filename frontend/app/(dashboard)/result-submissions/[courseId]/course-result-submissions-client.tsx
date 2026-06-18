"use client"

import Link from "next/link"
import { useState } from "react"
import { useSearchParams } from "next/navigation"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { formatDistanceToNow } from "date-fns"
import { ArrowLeft, ArrowRight, Download, FileText, Loader2, Send } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { PageHeader } from "@/components/shared/page-header"
import { StatusBadge } from "@/components/shared/status-badge"
import { useHasAnyPermission } from "@/hooks/use-permission"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"

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
  end_report_status: string | null
}

function SubmittedAt({ value }: { value: string | null }) {
  if (!value) return <span>Not submitted yet</span>
  return <span>Submitted {formatDistanceToNow(new Date(value), { addSuffix: true })}</span>
}

function groupByBatchTerm(items: ResultSubmission[]) {
  const map = new Map<
    string,
    { label: string; batch_id: string; academic_term_id: string; items: ResultSubmission[] }
  >()
  for (const item of items) {
    const key = `${item.batch_id}__${item.academic_term_id}`
    const label = `${item.batch_name} · ${item.term_name} (${item.term_season} ${item.term_year})`
    const group = map.get(key)
    if (group) {
      group.items.push(item)
    } else {
      map.set(key, { label, batch_id: item.batch_id, academic_term_id: item.academic_term_id, items: [item] })
    }
  }
  return Array.from(map.values())
}

interface Props {
  courseId: string
}

export function CourseResultSubmissionsClient({ courseId }: Props) {
  const qc = useQueryClient()
  const searchParams = useSearchParams()
  const code = searchParams.get("code")
  const title = searchParams.get("title")
  const canSubmitToPC = useHasAnyPermission(["result.approve.ml"])
  const [downloadingKey, setDownloadingKey] = useState<string | null>(null)

  const { data: submissions = [], isLoading } = useQuery({
    queryKey: queryKeys.results.submissions({ course_id: courseId }),
    queryFn: async () => {
      const { data } = await apiClient.GET("/results" as never, {
        params: { query: { course_id: courseId } },
      } as never)
      return ((data as unknown) as ResultSubmission[]) ?? []
    },
  })

  const bulkApproveMutation = useMutation({
    mutationFn: async (vars: { batchId: string; academicTermId: string }) => {
      const { data } = await apiClient.POST("/results/bulk-approve-ml" as never, {
        body: { course_id: courseId, batch_id: vars.batchId, academic_term_id: vars.academicTermId },
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

  async function handleDownloadCombinedReport(group: { label: string; batch_id: string; academic_term_id: string }) {
    setDownloadingKey(group.label)
    try {
      const { data: blob, error } = await apiClient.GET("/marksheets/course-report-pdf" as never, {
        params: { query: { course_id: courseId, batch_id: group.batch_id, academic_term_id: group.academic_term_id } },
        parseAs: "blob",
      } as never)
      if (error || !blob) {
        toast.error("Failed to generate combined report")
        return
      }
      const url = URL.createObjectURL(blob as Blob)
      const a = document.createElement("a")
      a.href = url
      a.download = `${headerCode ?? "course"}_combined_section_report.pdf`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch {
      toast.error("Failed to generate combined report")
    } finally {
      setDownloadingKey(null)
    }
  }

  const termGroups = groupByBatchTerm(submissions)
  const headerCode = code ?? submissions[0]?.course_code
  const headerTitle = title ?? submissions[0]?.course_title

  return (
    <div className="space-y-6">
      <PageHeader
        title={headerCode ? `${headerCode} — ${headerTitle}` : "Result Submissions"}
        description="Section result reports for this course, grouped by batch and semester."
        actions={
          <Button
            size="sm"
            variant="outline"
            nativeButton={false}
            render={<Link href="/result-submissions" />}
          >
            <ArrowLeft /> Back to courses
          </Button>
        }
      />

      {isLoading && (
        <div className="space-y-2">
          {[...Array(3)].map((_, i) => <div key={i} className="h-16 bg-muted animate-pulse rounded-lg" />)}
        </div>
      )}

      {!isLoading && termGroups.length === 0 && (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            No section result submissions found for this course.
          </CardContent>
        </Card>
      )}

      <div className="space-y-4">
        {termGroups.map((group) => {
          const reviewCount = group.items.filter((i) => i.status === "SUBMITTED").length
          const isSubmitting =
            bulkApproveMutation.isPending &&
            bulkApproveMutation.variables?.batchId === group.batch_id &&
            bulkApproveMutation.variables?.academicTermId === group.academic_term_id
          const isDownloading = downloadingKey === group.label

          return (
          <div key={group.label} className="space-y-2">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                {group.label}
              </p>
              <div className="flex flex-wrap items-center gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  nativeButton={false}
                  render={
                    <Link
                      href={`/result-submissions/${courseId}/combined-end-report?batch_id=${group.batch_id}&term_id=${group.academic_term_id}&code=${encodeURIComponent(headerCode ?? "")}&title=${encodeURIComponent(headerTitle ?? "")}`}
                    />
                  }
                >
                  <FileText /> Combined End Report
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={isDownloading}
                  onClick={() => handleDownloadCombinedReport(group)}
                >
                  {isDownloading ? <Loader2 className="animate-spin" /> : <Download />}
                  Download Combined Report
                </Button>
                {canSubmitToPC && reviewCount > 0 && (
                  <Button
                    size="sm"
                    disabled={isSubmitting}
                    onClick={() =>
                      bulkApproveMutation.mutate({ batchId: group.batch_id, academicTermId: group.academic_term_id })
                    }
                  >
                    {isSubmitting ? <Loader2 className="animate-spin" /> : <Send />}
                    Submit {reviewCount} section{reviewCount === 1 ? "" : "s"} to Program Coordinator
                  </Button>
                )}
              </div>
            </div>
            <div className="divide-y rounded-md border bg-background/60">
              {group.items.map((item) => (
                <div
                  key={item.section_offering_id}
                  className="flex items-center justify-between gap-4 p-3"
                >
                  <div className="space-y-1">
                    <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                      <Badge variant="outline" className="text-xs font-normal">Section {item.section_name}</Badge>
                      <Badge variant="outline" className="text-xs font-normal">
                        {item.student_count} student{item.student_count === 1 ? "" : "s"}
                      </Badge>
                      <StatusBadge status={item.status} />
                      {item.end_report_status === "SUBMITTED" && (
                        <Badge variant="outline" className="text-xs font-normal border-green-300 text-green-700">
                          End Report ✓
                        </Badge>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground"><SubmittedAt value={item.submitted_at} /></p>
                  </div>
                  <div className="flex items-center gap-2">
                    {item.end_report_status === "SUBMITTED" && (
                      <Button
                        size="sm"
                        variant="outline"
                        nativeButton={false}
                        render={<Link href={`/results/${item.section_offering_id}/end-report`} />}
                      >
                        End Report
                      </Button>
                    )}
                    <Button
                      size="sm"
                      variant="outline"
                      nativeButton={false}
                      render={
                        <Link
                          href={`/results/${item.section_offering_id}?label=${encodeURIComponent(`${headerCode} — Section ${item.section_name}`)}`}
                        />
                      }
                    >
                      Review <ArrowRight />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </div>
          )
        })}
      </div>
    </div>
  )
}
