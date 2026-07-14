"use client"

import { useParams, useRouter } from "next/navigation"
import { useQuery } from "@tanstack/react-query"
import { ArrowLeft, Download, ExternalLink, Loader2 } from "lucide-react"
import { useState } from "react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell,
} from "@/components/ui/table"
import { PageHeader } from "@/components/shared/page-header"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"

const GRADES = ["A+", "A", "A-", "B+", "B", "B-", "C+", "C", "D", "F"]

type EndReport = {
  id: string
  section_offering_id: string
  course_code: string
  course_title: string
  section_name: string
  batch_name: string
  term_name: string
  term_season: string
  term_year: number
  credits: number
  grade_distribution: Record<string, number>
  co_attainment: Record<string, number>
  // Computed from actual marks + the course's CO-PO mapping, not manually
  // entered like co_attainment above.
  po_attainment: Record<string, number>
  unattained_co_explanations: { co_code: string; reason: string; suggestion: string }[]
  teacher_feedback: string | null
  course_drive_link: string | null
  status: string
  submitted_at: string | null
}

type SectionOffering = {
  id: string
  curriculum_id: string
  course_id: string
}

type CourseOutcome = {
  id: string
  code: string
  statement: string
}

export default function EndReportReviewPage() {
  const params = useParams()
  const router = useRouter()
  const sectionOfferingId = params.offering_id as string
  const [isDownloading, setIsDownloading] = useState(false)

  const { data: offering } = useQuery({
    queryKey: ["section-offerings", sectionOfferingId],
    queryFn: async () => {
      const { data } = await apiClient.GET(`/section-offerings/${sectionOfferingId}` as never)
      return (data as unknown) as SectionOffering
    },
  })

  const { data: courseOutcomes = [] } = useQuery({
    queryKey: queryKeys.courseOutcomes.list(offering?.curriculum_id, offering?.course_id),
    queryFn: async () => {
      const { data } = await apiClient.GET("/course-outcomes" as never, {
        params: { query: { curriculum_id: offering!.curriculum_id, course_id: offering!.course_id } },
      } as never)
      return ((data as unknown) as CourseOutcome[]) ?? []
    },
    enabled: !!offering,
  })

  const { data: endReport, isLoading } = useQuery({
    queryKey: queryKeys.endReports.byOffering(sectionOfferingId),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/end-reports/${sectionOfferingId}` as never)
      return (data as unknown) as EndReport
    },
  })

  async function handleDownloadEndReportPdf() {
    setIsDownloading(true)
    try {
      const { data: blob, error } = await apiClient.GET(
        `/end-reports/${sectionOfferingId}/pdf` as never,
        { parseAs: "blob" } as never
      )
      if (error || !blob) {
        toast.error("Failed to generate end report PDF")
        return
      }
      const url = URL.createObjectURL(blob as Blob)
      const a = document.createElement("a")
      a.href = url
      a.download = `${endReport?.course_code ?? "section"}_end_report.pdf`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch {
      toast.error("Failed to generate end report PDF")
    } finally {
      setIsDownloading(false)
    }
  }

  if (isLoading) return <div className="h-64 animate-pulse bg-muted rounded-lg" />

  if (!endReport || endReport.id === "00000000-0000-0000-0000-000000000000") {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Course End Report"
          description="No end report found for this section."
          actions={
            <Button variant="outline" size="sm" onClick={() => router.back()}>
              <ArrowLeft className="h-4 w-4" /> Back
            </Button>
          }
        />
      </div>
    )
  }

  const totalStudents = Object.values(endReport.grade_distribution).reduce((sum, n) => sum + n, 0)

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      <PageHeader
        title="Course End Report"
        description={`${endReport.course_code} — ${endReport.course_title} · Section ${endReport.section_name} · ${endReport.batch_name}`}
        actions={
          <div className="flex items-center gap-2">
            <Badge variant={endReport.status === "SUBMITTED" ? "default" : "secondary"}>
              {endReport.status}
            </Badge>
            <Button variant="outline" size="sm" onClick={handleDownloadEndReportPdf} disabled={isDownloading}>
              {isDownloading ? <Loader2 className="animate-spin" /> : <Download className="h-4 w-4" />} End Report PDF
            </Button>
            <Button variant="outline" size="sm" onClick={() => router.back()}>
              <ArrowLeft className="h-4 w-4" /> Back
            </Button>
          </div>
        }
      />

      {/* Course Information */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Course Information</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
            <div><span className="text-muted-foreground">Course:</span> <strong>{endReport.course_code} — {endReport.course_title}</strong></div>
            <div><span className="text-muted-foreground">Section:</span> <strong>{endReport.section_name}</strong></div>
            <div><span className="text-muted-foreground">Batch:</span> <strong>{endReport.batch_name}</strong></div>
            <div><span className="text-muted-foreground">Term:</span> <strong>{endReport.term_name} ({endReport.term_season} {endReport.term_year})</strong></div>
          </div>
        </CardContent>
      </Card>

      {/* Submit Course Link */}
      {endReport.course_drive_link && (
        <Card className="border-blue-200 bg-blue-50/50 dark:border-blue-800 dark:bg-blue-950/20">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <ExternalLink className="h-5 w-5 text-blue-600" />
              Submit Course Link
            </CardTitle>
            <CardDescription>
              The section teacher has attached a Google Drive link with course materials. Review the link before
              submitting to the Program Coordinator.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <a
              href={endReport.course_drive_link}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 text-sm font-medium text-blue-700 hover:text-blue-900 underline underline-offset-2 break-all"
            >
              <ExternalLink className="h-4 w-4 shrink-0" />
              {endReport.course_drive_link}
            </a>
          </CardContent>
        </Card>
      )}

      {/* Course Outcomes */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Course Outcomes (COs)</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-20">CO</TableHead>
                <TableHead>Description</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {courseOutcomes.map((co) => (
                <TableRow key={co.id}>
                  <TableCell className="font-mono font-semibold">{co.code}</TableCell>
                  <TableCell>{co.statement}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Grade Distribution */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Grade Distribution</CardTitle>
          <CardDescription>Total: {totalStudents} students</CardDescription>
        </CardHeader>
        <CardContent>
          {totalStudents > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  {GRADES.map((g) => (
                    <TableHead key={g} className="text-center">{g}</TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                <TableRow>
                  {GRADES.map((g) => (
                    <TableCell key={g} className="text-center">
                      <div className="font-medium">{endReport.grade_distribution[g] ?? 0}</div>
                      <div className="text-xs text-muted-foreground">
                        {totalStudents > 0 ? (((endReport.grade_distribution[g] ?? 0) / totalStudents) * 100).toFixed(1) : "0.0"}%
                      </div>
                    </TableCell>
                  ))}
                </TableRow>
              </TableBody>
            </Table>
          ) : (
            <p className="text-sm text-muted-foreground">No grade distribution data entered.</p>
          )}
        </CardContent>
      </Card>

      {/* CO Attainment */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">CO Attainment</CardTitle>
        </CardHeader>
        <CardContent>
          {Object.keys(endReport.co_attainment).length > 0 ? (
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
              {Object.entries(endReport.co_attainment).map(([coCode, pct]) => {
                const attained = pct >= 50
                return (
                  <div key={coCode} className="text-center p-3 rounded-lg border">
                    <div className="font-mono font-semibold text-lg">{coCode}</div>
                    <div className={`text-2xl font-bold ${attained ? "text-green-600" : "text-red-600"}`}>
                      {pct}%
                    </div>
                    <Badge variant={attained ? "default" : "destructive"} className="mt-1 text-xs">
                      {attained ? "Attained" : "Not Attained"}
                    </Badge>
                  </div>
                )
              })}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No CO attainment data.</p>
          )}
        </CardContent>
      </Card>

      {/* PO Attainment */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">PO Attainment</CardTitle>
          <CardDescription>Computed from marks and the course&apos;s CO-PO mapping.</CardDescription>
        </CardHeader>
        <CardContent>
          {Object.keys(endReport.po_attainment).length > 0 ? (
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
              {Object.entries(endReport.po_attainment).map(([poCode, pct]) => {
                const attained = pct >= 50
                return (
                  <div key={poCode} className="text-center p-3 rounded-lg border">
                    <div className="font-mono font-semibold text-lg">{poCode}</div>
                    <div className={`text-2xl font-bold ${attained ? "text-green-600" : "text-red-600"}`}>
                      {pct}%
                    </div>
                    <Badge variant={attained ? "default" : "destructive"} className="mt-1 text-xs">
                      {attained ? "Attained" : "Not Attained"}
                    </Badge>
                  </div>
                )
              })}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No program outcomes mapped for this course.</p>
          )}
        </CardContent>
      </Card>

      {/* Unattained CO Explanation */}
      {endReport.unattained_co_explanations.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Unattained CO Explanation</CardTitle>
            <CardDescription>Reasons and improvement suggestions for COs below 50% attainment.</CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-24">Unattained CO</TableHead>
                  <TableHead>Identified Reasons (CO &lt; 50%)</TableHead>
                  <TableHead>Suggestions for Improvement</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {endReport.unattained_co_explanations.map((exp, idx) => (
                  <TableRow key={idx}>
                    <TableCell>
                      <Badge variant="destructive">{exp.co_code}</Badge>
                      <div className="text-xs text-muted-foreground mt-1">
                        {endReport.co_attainment[exp.co_code] ?? 0}%
                      </div>
                    </TableCell>
                    <TableCell className="whitespace-normal">{exp.reason || "—"}</TableCell>
                    <TableCell className="whitespace-normal">{exp.suggestion || "—"}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* Overall Feedback */}
      {endReport.teacher_feedback && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Overall Feedback from Course Teacher</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm whitespace-pre-wrap">{endReport.teacher_feedback}</p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
