"use client"

import Link from "next/link"
import { useSearchParams } from "next/navigation"
import { useQuery } from "@tanstack/react-query"
import { ArrowLeft, BarChart3 } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"
import { PageHeader } from "@/components/shared/page-header"
import { StatusBadge } from "@/components/shared/status-badge"
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
  section_name: string
  status: string
  submitted_at: string | null
  student_count: number
  end_report_status: string | null
}

type AttainmentResponse = {
  threshold_co_score_pct: number
  cos: Array<{ co_code: string; students_above_threshold: number; total_students: number; is_attained: boolean }>
  pos: Array<{ po_code: string; students_above_threshold: number; total_students: number; is_attained: boolean }>
}

type GradeDistribution = Record<string, number>

interface Props {
  courseId: string
}

const GRADES = ["A+", "A", "A-", "B+", "B", "B-", "C+", "C", "D", "F"]

function pct(count: number, total: number) {
  return total > 0 ? Math.round((count / total) * 1000) / 10 : 0
}

function average(values: number[]) {
  return values.length ? Math.round(values.reduce((s, n) => s + n, 0) / values.length * 10) / 10 : 0
}

function groupLabel(item: ResultSubmission) {
  return `${item.batch_name} · ${item.term_name} (${item.term_season} ${item.term_year})`
}

export function CourseResultDashboardClient({ courseId }: Props) {
  const searchParams = useSearchParams()
  const headerCode = searchParams.get("code")
  const headerTitle = searchParams.get("title")

  const { data: submissions = [], isLoading: loadingSubmissions } = useQuery({
    queryKey: queryKeys.results.submissions({ course_id: courseId, dashboard: true }),
    queryFn: async () => {
      const { data } = await apiClient.GET("/results" as never, {
        params: { query: { course_id: courseId } },
      } as never)
      return ((data as unknown) as ResultSubmission[]) ?? []
    },
  })

  const { data: dashboard, isLoading: loadingDetails } = useQuery({
    queryKey: ["result-submissions", courseId, "course-dashboard", submissions.map((s) => s.section_offering_id).join(",")],
    enabled: submissions.length > 0,
    queryFn: async () => {
      const rows = await Promise.all(
        submissions.map(async (section) => {
          const [attainmentRes, gradesRes] = await Promise.all([
            apiClient.GET(`/marksheets/${section.section_offering_id}/attainment` as never).catch(() => ({ data: null })),
            apiClient.GET(`/marksheets/${section.section_offering_id}/grade-distribution` as never).catch(() => ({ data: null })),
          ])
          return {
            section,
            attainment: attainmentRes.data as AttainmentResponse | null,
            grades: (gradesRes.data as GradeDistribution | null) ?? {},
          }
        })
      )

      const coValues = new Map<string, number[]>()
      const poValues = new Map<string, number[]>()
      const gradeTotals: GradeDistribution = Object.fromEntries(GRADES.map((g) => [g, 0]))
      for (const row of rows) {
        for (const grade of GRADES) gradeTotals[grade] = (gradeTotals[grade] ?? 0) + Number(row.grades[grade] ?? 0)
        for (const co of row.attainment?.cos ?? []) {
          const values = coValues.get(co.co_code) ?? []
          values.push(pct(co.students_above_threshold, co.total_students))
          coValues.set(co.co_code, values)
        }
        for (const po of row.attainment?.pos ?? []) {
          const values = poValues.get(po.po_code) ?? []
          values.push(pct(po.students_above_threshold, po.total_students))
          poValues.set(po.po_code, values)
        }
      }

      return {
        rows,
        gradeTotals,
        coSummary: Array.from(coValues.entries()).map(([code, values]) => ({ code, value: average(values) })),
        poSummary: Array.from(poValues.entries()).map(([code, values]) => ({ code, value: average(values) })),
      }
    },
  })

  const isLoading = loadingSubmissions || loadingDetails
  const courseCode = headerCode ?? submissions[0]?.course_code
  const courseTitle = headerTitle ?? submissions[0]?.course_title
  const totalSections = submissions.length
  const submittedSections = submissions.filter((s) => s.status !== "DRAFT").length
  const totalStudents = submissions.reduce((sum, s) => sum + Number(s.student_count ?? 0), 0)

  return (
    <div className="space-y-6">
      <PageHeader
        title={courseCode ? `${courseCode} Dashboard` : "Course Dashboard"}
        description={courseTitle ?? "Course-level view across submitted sections, batches, and semesters."}
        actions={
          <Button size="sm" variant="outline" nativeButton={false} render={<Link href={`/result-submissions/${courseId}`} />}>
            <ArrowLeft /> Back
          </Button>
        }
      />

      <div className="grid gap-4 sm:grid-cols-3">
        <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">Sections</p><p className="text-2xl font-semibold">{totalSections}</p></CardContent></Card>
        <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">Submitted</p><p className="text-2xl font-semibold">{submittedSections}</p></CardContent></Card>
        <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">Students</p><p className="text-2xl font-semibold">{totalStudents}</p></CardContent></Card>
      </div>

      {isLoading && <div className="h-40 animate-pulse rounded-lg bg-muted" />}

      {!isLoading && dashboard && (
        <>
          <div className="grid gap-4 lg:grid-cols-2">
            <SummaryCard title="Average CO Attainment Across Sections" items={dashboard.coSummary} />
            <SummaryCard title="Average PO Attainment Across Sections" items={dashboard.poSummary} />
          </div>

          <Card>
            <CardHeader><CardTitle className="text-sm">Combined Grade Distribution</CardTitle></CardHeader>
            <CardContent>
              <div className="grid grid-cols-5 gap-2 sm:grid-cols-10">
                {GRADES.map((grade) => (
                  <div key={grade} className="rounded border p-2 text-center">
                    <p className="text-xs text-muted-foreground">{grade}</p>
                    <p className="text-lg font-semibold">{dashboard.gradeTotals[grade] ?? 0}</p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle className="text-sm">Section Results</CardTitle></CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Batch / Semester</TableHead>
                    <TableHead>Section</TableHead>
                    <TableHead className="text-right">Students</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>CO Attainment</TableHead>
                    <TableHead>PO Attainment</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {dashboard.rows.map(({ section, attainment }) => (
                    <TableRow key={section.section_offering_id}>
                      <TableCell>{groupLabel(section)}</TableCell>
                      <TableCell>Section {section.section_name}</TableCell>
                      <TableCell className="text-right">{section.student_count}</TableCell>
                      <TableCell><StatusBadge status={section.status} /></TableCell>
                      <TableCell>{(attainment?.cos ?? []).map((co) => `${co.co_code}: ${pct(co.students_above_threshold, co.total_students)}%`).join(", ") || "No data"}</TableCell>
                      <TableCell>{(attainment?.pos ?? []).map((po) => `${po.po_code}: ${pct(po.students_above_threshold, po.total_students)}%`).join(", ") || "No data"}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}

function SummaryCard({ title, items }: { title: string; items: Array<{ code: string; value: number }> }) {
  return (
    <Card>
      <CardHeader><CardTitle className="flex items-center gap-2 text-sm"><BarChart3 className="h-4 w-4" />{title}</CardTitle></CardHeader>
      <CardContent className="space-y-2">
        {items.length === 0 ? <p className="text-sm text-muted-foreground">No attainment data yet.</p> : items.map((item) => (
          <div key={item.code} className="flex items-center justify-between rounded border px-3 py-2">
            <span className="font-medium">{item.code}</span>
            <Badge variant={item.value >= 50 ? "default" : "destructive"}>{item.value}%</Badge>
          </div>
        ))}
      </CardContent>
    </Card>
  )
}
