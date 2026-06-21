"use client"

import { useState } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { useQuery } from "@tanstack/react-query"
import { toast } from "sonner"
import { ArrowLeft, Download, FileText, Loader2, Send } from "lucide-react"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { PageHeader } from "@/components/shared/page-header"
import { StatusBadge } from "@/components/shared/status-badge"
import { useHasAnyPermission, usePermission } from "@/hooks/use-permission"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"
import { ExamGrid } from "./exam-grid"
import { AttainmentPanel } from "./attainment-panel"
import { MarksCoPoPanel } from "./marks-co-po-panel"
import { RosterPanel } from "./roster-panel"
import { QuestionConfigCard } from "@/app/(dashboard)/courses/[id]/assessment/course-assessment-question-config"

type MySection = {
  section_offering_id: string
  course_id: string
  course_code: string
  course_title: string
  batch_name: string
  term_name: string
  term_year: number
  term_season: string
  section_name: string
  status: string
  student_count: number
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
  status: string
}

type ResultPublication = {
  id: string
  section_offering_id: string
  status: string
  submitted_at: string | null
  ml_rejection_comment: string | null
}

interface Props {
  sectionOfferingId: string
}

export function MarksheetClient({ sectionOfferingId }: Props) {
  const router = useRouter()
  const canSubmit = useHasAnyPermission(["result.submit"])
  const canManageCurriculum = usePermission("curriculum.create") // PC / SA
  const [isDownloading, setIsDownloading] = useState(false)
  const [isDownloadingEndReport, setIsDownloadingEndReport] = useState(false)

  const { data: sections = [] } = useQuery({
    queryKey: queryKeys.facultyAssignments.mySections,
    queryFn: async () => {
      const { data } = await apiClient.GET("/faculty-assignments/my-sections" as never)
      return ((data as unknown) as MySection[]) ?? []
    },
  })

  const section = sections.find((s) => s.section_offering_id === sectionOfferingId)

  const { data: offering } = useQuery({
    queryKey: ["section-offerings", sectionOfferingId],
    queryFn: async () => {
      const { data } = await apiClient.GET(`/section-offerings/${sectionOfferingId}` as never)
      return (data as unknown) as SectionOffering
    },
  })

  const { data: myModuleAssignments = [] } = useQuery({
    queryKey: queryKeys.moduleLeaderAssignments.mine,
    queryFn: async () => {
      const { data } = await apiClient.GET("/module-leader-assignments/mine" as never)
      return ((data as unknown) as { course_id: string }[]) ?? []
    },
    enabled: !canManageCurriculum,
  })

  const isMyModule = canManageCurriculum || myModuleAssignments.some((a) => a.course_id === offering?.course_id)

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

  const { data: result } = useQuery({
    queryKey: queryKeys.results.byOffering(sectionOfferingId),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/results/${sectionOfferingId}` as never)
      return (data as unknown) as ResultPublication
    },
  })

  const { data: midQuestions = [] } = useQuery({
    queryKey: queryKeys.marksheets.questions(sectionOfferingId, "MID"),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/marksheets/${sectionOfferingId}/questions` as never, {
        params: { query: { exam_type: "MID" } },
      } as never)
      return ((data as unknown) as { id: string }[]) ?? []
    },
  })

  const { data: finalQuestions = [] } = useQuery({
    queryKey: queryKeys.marksheets.questions(sectionOfferingId, "FINAL"),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/marksheets/${sectionOfferingId}/questions` as never, {
        params: { query: { exam_type: "FINAL" } },
      } as never)
      return ((data as unknown) as { id: string }[]) ?? []
    },
  })

  const { data: endReport } = useQuery({
    queryKey: queryKeys.endReports.byOffering(sectionOfferingId),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/end-reports/${sectionOfferingId}` as never)
      return (data as unknown) as { id: string; status: string }
    },
  })

  const hasMidMarks = midQuestions.length > 0
  const hasFinalMarks = finalQuestions.length > 0
  const endReportSubmitted = endReport?.status === "SUBMITTED"
  const canSubmitToML = canSubmit && result?.status === "DRAFT" && hasMidMarks && hasFinalMarks && !endReportSubmitted
  const endReportExists = endReport && endReport.id !== "00000000-0000-0000-0000-000000000000"

  async function handleDownloadEndReportPdf() {
    setIsDownloadingEndReport(true)
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
      a.download = `${section?.course_code ?? "section"}_end_report.pdf`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch {
      toast.error("Failed to generate end report PDF")
    } finally {
      setIsDownloadingEndReport(false)
    }
  }

  async function handleDownloadPdf() {
    setIsDownloading(true)
    try {
      const { data: blob, error } = await apiClient.GET(
        `/marksheets/${sectionOfferingId}/report-pdf` as never,
        { parseAs: "blob" } as never
      )
      if (error || !blob) {
        toast.error("Failed to generate section report")
        return
      }
      const url = URL.createObjectURL(blob as Blob)
      const a = document.createElement("a")
      a.href = url
      a.download = `${section?.course_code ?? "section"}_report.pdf`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch {
      toast.error("Failed to generate section report")
    } finally {
      setIsDownloading(false)
    }
  }

  const isLocked = (result?.status != null && result.status !== "DRAFT") || endReportSubmitted

  return (
    <div className="space-y-6">
      <PageHeader
        title={section ? `${section.course_code} — ${section.course_title}` : "Marksheet"}
        description={
          section
            ? `${section.batch_name} · Section ${section.section_name} · ${section.term_name} (${section.term_season} ${section.term_year}) · ${section.student_count} students`
            : undefined
        }
        actions={
          <div className="flex items-center gap-2">
            {section && <StatusBadge status={section.status} />}
            {result && result.status !== "DRAFT" && <StatusBadge status={result.status} />}
            <Button variant="outline" size="sm" onClick={handleDownloadPdf} disabled={isDownloading}>
              {isDownloading ? <Loader2 className="animate-spin" /> : <Download />} Section Report
            </Button>
            {endReportSubmitted && (
              <Button variant="outline" size="sm" onClick={handleDownloadEndReportPdf} disabled={isDownloadingEndReport}>
                {isDownloadingEndReport ? <Loader2 className="animate-spin" /> : <Download />} End Report PDF
              </Button>
            )}
            {endReportExists && (
              <Button variant="outline" size="sm" onClick={() => router.push(`/my-sections/${sectionOfferingId}/end-report`)}>
                <FileText className="h-4 w-4" /> End Report
              </Button>
            )}
            {canSubmitToML && (
              <Button size="sm" onClick={() => router.push(`/my-sections/${sectionOfferingId}/end-report`)}>
                <Send className="h-4 w-4" /> Submit Report
              </Button>
            )}
            {canSubmit && result?.status === "DRAFT" && !endReportSubmitted && (!hasMidMarks || !hasFinalMarks) && (
              <div className="text-xs text-muted-foreground max-w-48">
                Enter both MID and FINAL marks before submitting
              </div>
            )}
            <Button variant="outline" size="sm" nativeButton={false} render={<Link href="/my-sections" />}>
              <ArrowLeft /> Back
            </Button>
          </div>
        }
      />

      {result?.status === "DRAFT" && result.ml_rejection_comment && (
        <Alert className="border-amber-300 bg-amber-50 text-amber-900">
          <AlertTitle>Sent back by Module Leader</AlertTitle>
          <AlertDescription className="text-amber-800">{result.ml_rejection_comment}</AlertDescription>
        </Alert>
      )}

      {isLocked && (
        <Alert>
          <AlertTitle>Section locked</AlertTitle>
          <AlertDescription>
            {endReportSubmitted
              ? "The end report has been submitted. This section is now locked — enrollment and marks cannot be changed."
              : "This section's results have been submitted and are locked. Contact your Module Leader if you need to make changes."}
          </AlertDescription>
        </Alert>
      )}

      {offering && isMyModule && (
        <QuestionConfigCard courseId={offering.course_id} curriculumId={offering.curriculum_id} />
      )}

      <Tabs defaultValue="roster">
        <TabsList>
          <TabsTrigger value="roster">Students</TabsTrigger>
          <TabsTrigger value="MID">Mid Term</TabsTrigger>
          <TabsTrigger value="FINAL">Final Exam</TabsTrigger>
          <TabsTrigger value="marks-co-po">Marks vs CO/PO</TabsTrigger>
          <TabsTrigger value="attainment">CO/PO Attainment</TabsTrigger>
        </TabsList>

        <TabsContent value="roster" className="mt-4">
          <RosterPanel sectionOfferingId={sectionOfferingId} locked={isLocked} />
        </TabsContent>

        <TabsContent value="MID" className="mt-4">
          <ExamGrid sectionOfferingId={sectionOfferingId} examType="MID" courseOutcomes={courseOutcomes} locked={isLocked} />
        </TabsContent>

        <TabsContent value="FINAL" className="mt-4">
          <ExamGrid sectionOfferingId={sectionOfferingId} examType="FINAL" courseOutcomes={courseOutcomes} locked={isLocked} />
        </TabsContent>

        <TabsContent value="marks-co-po" className="mt-4">
          <MarksCoPoPanel sectionOfferingId={sectionOfferingId} />
        </TabsContent>

        <TabsContent value="attainment" className="mt-4">
          <AttainmentPanel sectionOfferingId={sectionOfferingId} />
        </TabsContent>
      </Tabs>
    </div>
  )
}
