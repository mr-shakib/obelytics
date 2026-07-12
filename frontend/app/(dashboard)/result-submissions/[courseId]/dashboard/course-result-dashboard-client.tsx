"use client"

import Link from "next/link"
import { useSearchParams } from "next/navigation"
import { useQuery } from "@tanstack/react-query"
import { ArrowLeft, BarChart3, ChartNoAxesCombined, Gauge, Radar } from "lucide-react"
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  LabelList,
  Legend,
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar as RadarSeries,
  RadarChart,
  RadialBar,
  RadialBarChart,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
  XAxis,
  YAxis,
} from "recharts"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"
import { PageHeader } from "@/components/shared/page-header"
import { ResultStatusBadge } from "@/components/shared/result-status-badge"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"
import { CATEGORICAL_COLORS, GRADE_RAMP, SEQUENTIAL_PRIMARY, STATUS_GOOD } from "@/lib/result-colors"

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
// One consistent hue per data role — CO vs PO — reused across every chart in
// this dashboard, instead of a different color per chart.
const CO_COLOR = SEQUENTIAL_PRIMARY
const PO_COLOR = CATEGORICAL_COLORS[4]
const GRADE_COLORS = GRADES.map((g) => GRADE_RAMP[g])

function pct(count: number, total: number) {
  return total > 0 ? Math.round((count / total) * 1000) / 10 : 0
}

function average(values: number[]) {
  return values.length ? Math.round(values.reduce((s, n) => s + n, 0) / values.length * 10) / 10 : 0
}

function naturalSort(a: string, b: string) {
  return a.localeCompare(b, undefined, { numeric: true, sensitivity: "base" })
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
      const sectionComparison = rows.map((row) => {
        const coAttainment = (row.attainment?.cos ?? []).map((co) => pct(co.students_above_threshold, co.total_students))
        const poAttainment = (row.attainment?.pos ?? []).map((po) => pct(po.students_above_threshold, po.total_students))
        return {
          section: `Sec ${row.section.section_name}`,
          students: row.section.student_count,
          coAvg: average(coAttainment),
          poAvg: average(poAttainment),
          status: row.section.status,
        }
      })

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

      const coCodes = Array.from(coValues.keys()).sort(naturalSort)
      const poCodes = Array.from(poValues.keys()).sort(naturalSort)
      const gradeChart = GRADES.map((grade, index) => ({
        grade,
        students: gradeTotals[grade] ?? 0,
        fill: GRADE_COLORS[index],
      }))
      const coSummary = coCodes.map((code) => ({ code, value: average(coValues.get(code) ?? []) }))
      const poSummary = poCodes.map((code) => ({ code, value: average(poValues.get(code) ?? []) }))

      return {
        rows,
        gradeChart,
        coSummary,
        poSummary,
        sectionComparison,
        overallCo: average(coSummary.map((item) => item.value)),
        overallPo: average(poSummary.map((item) => item.value)),
      }
    },
  })

  const isLoading = loadingSubmissions || loadingDetails
  const courseCode = headerCode ?? submissions[0]?.course_code
  const courseTitle = headerTitle ?? submissions[0]?.course_title
  const totalSections = submissions.length
  const submittedSections = submissions.filter((s) => s.status !== "DRAFT").length
  const totalStudents = submissions.reduce((sum, s) => sum + Number(s.student_count ?? 0), 0)
  const submittedPct = pct(submittedSections, totalSections)

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

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">Sections</p><p className="text-2xl font-semibold">{totalSections}</p></CardContent></Card>
        <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">Submitted</p><p className="text-2xl font-semibold">{submittedSections}</p></CardContent></Card>
        <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">Students</p><p className="text-2xl font-semibold">{totalStudents}</p></CardContent></Card>
        <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">Average CO</p><p className="text-2xl font-semibold">{dashboard?.overallCo ?? 0}%</p></CardContent></Card>
        <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">Average PO</p><p className="text-2xl font-semibold">{dashboard?.overallPo ?? 0}%</p></CardContent></Card>
      </div>

      {isLoading && <div className="h-40 animate-pulse rounded-lg bg-muted" />}

      {!isLoading && dashboard && (
        <>
          <div className="grid gap-4 xl:grid-cols-[1.4fr_1fr]">
            <ChartCard
              title="Section Attainment Comparison"
              icon={<ChartNoAxesCombined className="h-4 w-4" />}
              empty={dashboard.sectionComparison.length === 0}
            >
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={dashboard.sectionComparison} margin={{ top: 16, right: 16, bottom: 8, left: -16 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="section" tickLine={false} axisLine={false} />
                  <YAxis domain={[0, 100]} tickLine={false} axisLine={false} unit="%" />
                  <RechartsTooltip formatter={(value) => [`${value}%`, "Attainment"]} />
                  <Legend />
                  <Bar dataKey="coAvg" name="CO average" fill={CO_COLOR} radius={[4, 4, 0, 0]} />
                  <Bar dataKey="poAvg" name="PO average" fill={PO_COLOR} radius={[4, 4, 0, 0]} />
                </ComposedChart>
              </ResponsiveContainer>
            </ChartCard>

            <ChartCard
              title="Submission Readiness"
              icon={<Gauge className="h-4 w-4" />}
              empty={totalSections === 0}
            >
              <ResponsiveContainer width="100%" height="100%">
                <RadialBarChart
                  innerRadius="68%"
                  outerRadius="94%"
                  data={[{ name: "Submitted", value: submittedPct, fill: STATUS_GOOD }]}
                  startAngle={90}
                  endAngle={-270}
                >
                  <RadialBar dataKey="value" cornerRadius={10} background={{ fill: "#e5e7eb" }} />
                  <RechartsTooltip formatter={(value) => [`${value}%`, "Submitted"]} />
                  <text x="50%" y="47%" textAnchor="middle" dominantBaseline="middle" className="fill-foreground text-3xl font-semibold">
                    {submittedPct}%
                  </text>
                  <text x="50%" y="60%" textAnchor="middle" dominantBaseline="middle" className="fill-muted-foreground text-xs">
                    {submittedSections} of {totalSections} sections
                  </text>
                </RadialBarChart>
              </ResponsiveContainer>
            </ChartCard>
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <ChartCard
              title="CO Attainment Spider Graph"
              icon={<Radar className="h-4 w-4" />}
              empty={dashboard.coSummary.length === 0}
            >
              <AttainmentRadar data={dashboard.coSummary} color={CO_COLOR} />
            </ChartCard>

            <ChartCard
              title="PO Attainment Spider Graph"
              icon={<Radar className="h-4 w-4" />}
              empty={dashboard.poSummary.length === 0}
            >
              <AttainmentRadar data={dashboard.poSummary} color={PO_COLOR} />
            </ChartCard>
          </div>

          <div className="grid gap-4 xl:grid-cols-[1fr_1.25fr]">
            <SummaryCard title="Average CO Attainment Across Sections" items={dashboard.coSummary} />
            <SummaryCard title="Average PO Attainment Across Sections" items={dashboard.poSummary} />
          </div>

          <ChartCard
            title="Combined Grade Distribution"
            icon={<BarChart3 className="h-4 w-4" />}
            empty={dashboard.gradeChart.every((item) => item.students === 0)}
            heightClassName="h-80"
          >
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={dashboard.gradeChart} margin={{ top: 24, right: 8, bottom: 8, left: -16 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="grade" tickLine={false} axisLine={false} />
                <YAxis allowDecimals={false} tickLine={false} axisLine={false} />
                <RechartsTooltip formatter={(value) => [value, "Students"]} />
                <Bar dataKey="students" name="Students" radius={[5, 5, 0, 0]}>
                  {dashboard.gradeChart.map((entry) => (
                    <Cell key={entry.grade} fill={entry.fill} />
                  ))}
                  <LabelList dataKey="students" position="top" className="fill-foreground text-xs" />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>

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
                      <TableCell><ResultStatusBadge status={section.status} /></TableCell>
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

function ChartCard({
  title,
  icon,
  empty,
  children,
  heightClassName = "h-72",
}: {
  title: string
  icon: React.ReactNode
  empty: boolean
  children: React.ReactNode
  heightClassName?: string
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-sm">
          {icon}
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {empty ? (
          <div className="flex h-48 items-center justify-center rounded-md border border-dashed text-sm text-muted-foreground">
            No chart data yet.
          </div>
        ) : (
          <div className={heightClassName}>{children}</div>
        )}
      </CardContent>
    </Card>
  )
}

function AttainmentRadar({ data, color }: { data: Array<{ code: string; value: number }>; color: string }) {
  const chartData = data.map((item) => ({ outcome: item.code, attainment: item.value }))

  return (
    <ResponsiveContainer width="100%" height="100%">
      <RadarChart data={chartData} outerRadius="72%">
        <PolarGrid />
        <PolarAngleAxis dataKey="outcome" tick={{ fontSize: 12 }} />
        <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fontSize: 11 }} tickCount={6} />
        <RadarSeries
          name="Attainment"
          dataKey="attainment"
          stroke={color}
          fill={color}
          fillOpacity={0.24}
          dot={{ r: 3, fill: color }}
        />
        <RechartsTooltip formatter={(value) => [`${value}%`, "Attainment"]} />
      </RadarChart>
    </ResponsiveContainer>
  )
}
