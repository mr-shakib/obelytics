"use client"

import { useState, useEffect } from "react"
import { useParams, useRouter } from "next/navigation"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { ArrowLeft, Download, ExternalLink, Loader2, Save, Send } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Badge } from "@/components/ui/badge"
import {
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell,
} from "@/components/ui/table"
import { PageHeader } from "@/components/shared/page-header"
import { CoMappingsSummaryCard } from "@/components/courses/co-mappings-summary-card"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"

const GRADES = ["A+", "A", "A-", "B+", "B", "B-", "C+", "C", "D", "F"]

type MySection = {
  section_offering_id: string
  course_id: string
  curriculum_id: string
  course_code: string
  course_title: string
  batch_name: string
  term_name: string
  term_year: number
  term_season: string
  section_name: string
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
  bloom_level_ids?: string[]
}

type COAttainment = {
  course_outcome_id: string
  co_code: string
  average_attainment_pct: number
  students_above_threshold: number
  total_students: number
  is_attained: boolean
}

type AttainmentResponse = {
  cos: COAttainment[]
}

type EndReport = {
  id: string
  section_offering_id: string
  grade_distribution: Record<string, number>
  co_attainment: Record<string, number>
  unattained_co_explanations: { co_code: string; reason: string; suggestion: string }[]
  teacher_feedback: string | null
  course_drive_link: string | null
  status: string
  submitted_at: string | null
}

type ProgramOutcome = { id: string; code: string }
type BloomLevel = { id: string; code: string; order_index: number }

export default function EndReportPage() {
  const params = useParams()
  const router = useRouter()
  const qc = useQueryClient()
  const sectionOfferingId = params.id as string

  const [isDownloadingPdf, setIsDownloadingPdf] = useState(false)
  const [gradeDistribution, setGradeDistribution] = useState<Record<string, number>>({})
  const [coAttainment, setCoAttainment] = useState<Record<string, number>>({})
  const [unattainedExplanations, setUnattainedExplanations] = useState<
    { co_code: string; reason: string; suggestion: string }[]
  >([])
  const [teacherFeedback, setTeacherFeedback] = useState("")
  const [driveLink, setDriveLink] = useState("")

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

  const { data: attainment } = useQuery({
    queryKey: queryKeys.marksheets.attainment(sectionOfferingId),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/marksheets/${sectionOfferingId}/attainment` as never)
      return (data as unknown) as AttainmentResponse
    },
  })


  const { data: programOutcomes = [] } = useQuery({
    queryKey: queryKeys.programOutcomes.all,
    queryFn: async () => {
      const { data } = await apiClient.GET("/program-outcomes" as never)
      return ((data as unknown) as ProgramOutcome[]) ?? []
    },
  })

  const { data: bloomLevels = [] } = useQuery({
    queryKey: queryKeys.refData.bloomLevels,
    queryFn: async () => {
      const { data } = await apiClient.GET("/ref-data/bloom-levels" as never)
      return ((data as unknown) as BloomLevel[]) ?? []
    },
  })

  const { data: existingReport, isLoading: loadingReport } = useQuery({
    queryKey: queryKeys.endReports.byOffering(sectionOfferingId),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/end-reports/${sectionOfferingId}` as never)
      return (data as unknown) as EndReport
    },
  })

  useEffect(() => {
    if (!existingReport || existingReport.id === "00000000-0000-0000-0000-000000000000") return
    setGradeDistribution(existingReport.grade_distribution ?? {})
    setCoAttainment(existingReport.co_attainment ?? {})
    setUnattainedExplanations(existingReport.unattained_co_explanations ?? [])
    setTeacherFeedback(existingReport.teacher_feedback ?? "")
    setDriveLink(existingReport.course_drive_link ?? "")
  }, [existingReport])

  useEffect(() => {
    if (attainment?.cos && Object.keys(coAttainment).length === 0) {
      const initial: Record<string, number> = {}
      for (const co of attainment.cos) {
        initial[co.co_code] = co.total_students > 0
          ? Math.round((co.students_above_threshold / co.total_students) * 1000) / 10
          : 0
      }
      setCoAttainment(initial)
    }
  }, [attainment])

  useEffect(() => {
    if (attainment?.cos && unattainedExplanations.length === 0) {
      const unattained = attainment.cos.filter((co) => !co.is_attained)
      if (unattained.length > 0) {
        setUnattainedExplanations(
          unattained.map((co) => ({ co_code: co.co_code, reason: "", suggestion: "" }))
        )
      }
    }
  }, [attainment])

  const isSubmitted = existingReport?.status === "SUBMITTED"

  async function handleDownloadEndReportPdf() {
    setIsDownloadingPdf(true)
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
      a.download = `${section?.course_code ?? "course"}_end_report.pdf`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch {
      toast.error("Failed to generate end report PDF")
    } finally {
      setIsDownloadingPdf(false)
    }
  }

  const handleGradeChange = (grade: string, value: string) => {
    setGradeDistribution((prev) => ({ ...prev, [grade]: parseInt(value) || 0 }))
  }

  const handleExplanationChange = (index: number, field: "reason" | "suggestion", value: string) => {
    setUnattainedExplanations((prev) => {
      const next = [...prev]
      next[index] = { ...next[index], [field]: value }
      return next
    })
  }

  const saveDraftMutation = useMutation({
    mutationFn: async () => {
      await apiClient.POST(`/end-reports/${sectionOfferingId}/save-draft` as never, {
        body: {
          grade_distribution: gradeDistribution,
          co_attainment: coAttainment,
          unattained_co_explanations: unattainedExplanations,
          teacher_feedback: teacherFeedback || null,
          course_drive_link: driveLink.trim() || null,
        },
      } as never)
    },
    onSuccess: () => {
      toast.success("Draft saved")
      qc.invalidateQueries({ queryKey: queryKeys.endReports.byOffering(sectionOfferingId) })
    },
    onError: () => toast.error("Failed to save draft"),
  })

  const submitMutation = useMutation({
    mutationFn: async () => {
      await apiClient.POST(`/end-reports/${sectionOfferingId}/submit` as never, {
        body: {
          grade_distribution: gradeDistribution,
          co_attainment: coAttainment,
          unattained_co_explanations: unattainedExplanations,
          teacher_feedback: teacherFeedback || null,
          course_drive_link: driveLink.trim() || null,
        },
      } as never)
    },
    onSuccess: () => {
      toast.success("End report submitted to Module Leader")
      qc.invalidateQueries({ queryKey: queryKeys.endReports.byOffering(sectionOfferingId) })
      qc.invalidateQueries({ queryKey: queryKeys.results.byOffering(sectionOfferingId) })
    },
    onError: () => toast.error("Failed to submit end report"),
  })

  const enrolledCount = section?.student_count ?? 0
  const totalStudents = Object.values(gradeDistribution).reduce((sum, n) => sum + n, 0)
  const gradeOverEnrolled = enrolledCount > 0 && totalStudents > enrolledCount

  const driveLinkTrimmed = driveLink.trim()
  const driveLinkValid = driveLinkTrimmed.length > 0 && driveLinkTrimmed.includes("drive.google.com")
  const driveLinkInvalid = driveLinkTrimmed.length > 0 && !driveLinkTrimmed.includes("drive.google.com")

  if (loadingReport) {
    return <div className="h-64 animate-pulse bg-muted rounded-lg" />
  }

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      <PageHeader
        title="Course End Report"
        description={
          section
            ? `${section.course_code} — ${section.course_title} · Section ${section.section_name} · ${section.batch_name} · ${section.term_name} (${section.term_season} ${section.term_year})`
            : undefined
        }
        actions={
          <div className="flex items-center gap-2">
            {isSubmitted && <Badge variant="default">Submitted</Badge>}
            {isSubmitted && (
              <Button variant="outline" size="sm" onClick={handleDownloadEndReportPdf} disabled={isDownloadingPdf}>
                {isDownloadingPdf ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
                Download PDF
              </Button>
            )}
            <Button variant="outline" size="sm" onClick={() => router.push(`/my-sections/${sectionOfferingId}`)}>
              <ArrowLeft className="h-4 w-4" /> Back to Marksheet
            </Button>
          </div>
        }
      />

      {isSubmitted && (
        <Card className="border-green-200 bg-green-50">
          <CardContent className="py-4 text-sm text-green-800">
            This end report has been submitted to the Module Leader. It cannot be edited.
          </CardContent>
        </Card>
      )}

      {/* Course Information */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Course Information</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
            <div><span className="text-muted-foreground">Course Code:</span> <strong>{section?.course_code}</strong></div>
            <div><span className="text-muted-foreground">Course Title:</span> <strong>{section?.course_title}</strong></div>
            <div><span className="text-muted-foreground">Section:</span> <strong>{section?.section_name}</strong></div>
            <div><span className="text-muted-foreground">Batch:</span> <strong>{section?.batch_name}</strong></div>
            <div><span className="text-muted-foreground">Semester:</span> <strong>{section?.term_name}</strong></div>
            <div><span className="text-muted-foreground">Year:</span> <strong>{section?.term_year}</strong></div>
            <div><span className="text-muted-foreground">Total Students:</span> <strong>{section?.student_count}</strong></div>
          </div>
        </CardContent>
      </Card>

      {/* Course Outcomes with Mappings */}
      {offering && (
        <CoMappingsSummaryCard
          cos={courseOutcomes}
          pos={programOutcomes}
          bloomLevels={bloomLevels}
          curriculumId={offering.curriculum_id}
          courseId={offering.course_id}
        />
      )}

      {/* Grade Distribution */}
      <Card className={gradeOverEnrolled ? "border-destructive" : undefined}>
        <CardHeader>
          <CardTitle className="text-lg">Grade Distribution</CardTitle>
          <CardDescription>
            Enter the number of students who received each grade. Enrolled: <strong>{enrolledCount}</strong> students.
            {totalStudents > 0 && (
              <span className={gradeOverEnrolled ? " text-destructive font-semibold" : ""}>
                {" "}Total entered: {totalStudents}
                {gradeOverEnrolled && ` — exceeds enrolled count by ${totalStudents - enrolledCount}`}
              </span>
            )}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-5 md:grid-cols-10 gap-3">
            {GRADES.map((grade) => (
              <div key={grade} className="space-y-1">
                <Label className="text-xs text-center block font-semibold">{grade}</Label>
                <Input
                  type="number"
                  min={0}
                  value={gradeDistribution[grade] ?? ""}
                  onChange={(e) => handleGradeChange(grade, e.target.value)}
                  disabled={isSubmitted}
                  className="h-9 text-center"
                  placeholder="0"
                />
              </div>
            ))}
          </div>
          {gradeOverEnrolled && (
            <p className="mt-3 text-sm text-destructive font-medium">
              Total grade count ({totalStudents}) exceeds the number of enrolled students ({enrolledCount}). Please correct before saving.
            </p>
          )}
          {totalStudents > 0 && (
            <div className="mt-4 overflow-auto rounded-lg border">
              <Table>
                <TableHeader>
                  <TableRow>
                    {GRADES.map((g) => (
                      <TableHead key={g} className="text-center text-xs">{g}</TableHead>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  <TableRow>
                    {GRADES.map((g) => {
                      const count = gradeDistribution[g] ?? 0
                      const pct = totalStudents > 0 ? ((count / totalStudents) * 100).toFixed(1) : "0.0"
                      return (
                        <TableCell key={g} className="text-center text-xs">
                          <div>{count}</div>
                          <div className="text-muted-foreground">{pct}%</div>
                        </TableCell>
                      )
                    })}
                  </TableRow>
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* CO Attainment */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">CO Attainment</CardTitle>
          <CardDescription>
            Attainment percentage for each course outcome, calculated from marks data.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {courseOutcomes.length === 0 ? (
            <p className="text-sm text-muted-foreground">No course outcomes defined.</p>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
              {courseOutcomes.map((co) => {
                const value = coAttainment[co.code] ?? 0
                const attained = value >= 50
                return (
                  <div key={co.id} className="space-y-1">
                    <Label className="text-xs text-center block font-semibold">{co.code}</Label>
                    <div className={`h-9 flex items-center justify-center rounded-md border text-sm font-medium ${attained ? "border-green-300 bg-green-50 text-green-800" : "border-red-300 bg-red-50 text-red-800"}`}>
                      {Number(value).toFixed(1)}%
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Submit Course Link */}
      <Card className={driveLinkInvalid ? "border-destructive" : driveLinkValid ? "border-green-400" : undefined}>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <ExternalLink className="h-5 w-5 text-muted-foreground" />
            Submit Course Link
          </CardTitle>
          <CardDescription>
            Provide a Google Drive link containing course materials (e.g., scanned marksheets, attendance). This is
            required before you can submit the end report to the Module Leader.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          <Input
            type="url"
            value={driveLink}
            onChange={(e) => setDriveLink(e.target.value)}
            disabled={isSubmitted}
            placeholder="https://drive.google.com/drive/folders/..."
            className={driveLinkInvalid ? "border-destructive focus-visible:ring-destructive" : driveLinkValid ? "border-green-400" : undefined}
          />
          {driveLinkInvalid && (
            <p className="text-sm text-destructive font-medium">
              Please enter a valid Google Drive link (must contain &quot;drive.google.com&quot;).
            </p>
          )}
          {driveLinkValid && (
            <p className="text-sm text-green-700 font-medium flex items-center gap-1">
              <ExternalLink className="h-3.5 w-3.5" />
              <a href={driveLinkTrimmed} target="_blank" rel="noopener noreferrer" className="underline hover:no-underline">
                Open link to verify
              </a>
            </p>
          )}
          {!isSubmitted && !driveLinkTrimmed && (
            <p className="text-xs text-muted-foreground">
              You must provide this link to submit the end report.
            </p>
          )}
        </CardContent>
      </Card>

      {/* Unattained CO Explanation */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Unattained CO Explanation</CardTitle>
          <CardDescription>
            For each CO with attainment below 50%, provide reasons and improvement suggestions.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {unattainedExplanations.length === 0 ? (
            <p className="text-sm text-muted-foreground">All COs are attained (≥50%). No explanations needed.</p>
          ) : (
            <div className="space-y-4">
              {unattainedExplanations.map((exp, idx) => (
                <div key={idx} className="rounded-lg border p-4 space-y-3">
                  <div className="flex items-center gap-2">
                    <Badge variant="destructive">{exp.co_code}</Badge>
                    <span className="text-sm text-muted-foreground">
                      Attainment: {coAttainment[exp.co_code] ?? 0}%
                    </span>
                  </div>
                  <div className="space-y-2">
                    <Label>Identified Reasons (CO &lt; 50%)</Label>
                    <Textarea
                      value={exp.reason}
                      onChange={(e) => handleExplanationChange(idx, "reason", e.target.value)}
                      disabled={isSubmitted}
                      rows={2}
                      placeholder="Why did students struggle with this CO?"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Suggestions for Improvement</Label>
                    <Textarea
                      value={exp.suggestion}
                      onChange={(e) => handleExplanationChange(idx, "suggestion", e.target.value)}
                      disabled={isSubmitted}
                      rows={2}
                      placeholder="What can be improved next semester?"
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Overall Feedback */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Overall Feedback from Course Teacher</CardTitle>
          <CardDescription>General observations and feedback about the course delivery.</CardDescription>
        </CardHeader>
        <CardContent>
          <Textarea
            value={teacherFeedback}
            onChange={(e) => setTeacherFeedback(e.target.value)}
            disabled={isSubmitted}
            rows={4}
            placeholder="Enter your overall feedback about the course, student engagement, and suggestions for future offerings..."
          />
        </CardContent>
      </Card>

      {/* Actions */}
      {!isSubmitted && (
        <div className="flex justify-end gap-3">
          <Button
            variant="outline"
            onClick={() => saveDraftMutation.mutate()}
            disabled={saveDraftMutation.isPending || gradeOverEnrolled}
          >
            {saveDraftMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
            Save Draft
          </Button>
          <Button
            onClick={() => submitMutation.mutate()}
            disabled={submitMutation.isPending || gradeOverEnrolled || !driveLinkValid}
            title={!driveLinkValid ? "A valid Google Drive link is required to submit" : undefined}
          >
            {submitMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            Submit to Module Leader
          </Button>
        </div>
      )}
    </div>
  )
}
