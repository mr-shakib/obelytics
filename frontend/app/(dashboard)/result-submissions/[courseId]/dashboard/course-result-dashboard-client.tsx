"use client"

import { useState } from "react"
import Link from "next/link"
import { useSearchParams } from "next/navigation"
import { useQuery } from "@tanstack/react-query"
import { ArrowLeft, BarChart3, ChartNoAxesCombined, Gauge, Radar } from "lucide-react"
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
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
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"
import { PageHeader } from "@/components/shared/page-header"
import { ResultStatusBadge } from "@/components/shared/result-status-badge"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"
import { CATEGORICAL_COLORS, GRADE_RAMP, SEQUENTIAL_PRIMARY, STATUS_CRITICAL, STATUS_GOOD } from "@/lib/result-colors"

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
const ALL_VALUE = "__all__"
// Per-outcome-code color in the "All" grouped view — fixed order, wraps if
// there are more codes than swatches rather than reassigning on re-render.
function codeColor(index: number) {
  return CATEGORICAL_COLORS[index % CATEGORICAL_COLORS.length]
}

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
  const [selectedCo, setSelectedCo] = useState("")
  const [selectedPo, setSelectedPo] = useState("")

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

      // Per-outcome, per-section breakdown — section labels can repeat (e.g. the
      // same section name offered in different terms), so values are averaged
      // rather than assumed to be a single data point.
      const coBySection: Record<string, Record<string, number[]>> = {}
      const poBySection: Record<string, Record<string, number[]>> = {}
      const sectionOrder: string[] = []

      for (const row of rows) {
        const label = `Sec ${row.section.section_name}`
        if (!sectionOrder.includes(label)) sectionOrder.push(label)

        for (const grade of GRADES) gradeTotals[grade] = (gradeTotals[grade] ?? 0) + Number(row.grades[grade] ?? 0)

        for (const co of row.attainment?.cos ?? []) {
          const values = coValues.get(co.co_code) ?? []
          const value = pct(co.students_above_threshold, co.total_students)
          values.push(value)
          coValues.set(co.co_code, values)

          if (!coBySection[co.co_code]) coBySection[co.co_code] = {}
          if (!coBySection[co.co_code][label]) coBySection[co.co_code][label] = []
          coBySection[co.co_code][label].push(value)
        }
        for (const po of row.attainment?.pos ?? []) {
          const values = poValues.get(po.po_code) ?? []
          const value = pct(po.students_above_threshold, po.total_students)
          values.push(value)
          poValues.set(po.po_code, values)

          if (!poBySection[po.po_code]) poBySection[po.po_code] = {}
          if (!poBySection[po.po_code][label]) poBySection[po.po_code][label] = []
          poBySection[po.po_code][label].push(value)
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

      // Section breakdown per outcome code, plus a trailing "Average" bar —
      // the same across-sections average already plotted on the spider graph —
      // so a section's attainment can be read against it directly.
      const coSectionSeries: Record<string, Array<{ section: string; value: number; isAverage?: boolean }>> = {}
      for (const code of coCodes) {
        coSectionSeries[code] = [
          ...sectionOrder
            .filter((label) => coBySection[code]?.[label])
            .map((label) => ({ section: label, value: average(coBySection[code][label]) })),
          { section: "Average", value: average(coValues.get(code) ?? []), isAverage: true },
        ]
      }
      const poSectionSeries: Record<string, Array<{ section: string; value: number; isAverage?: boolean }>> = {}
      for (const code of poCodes) {
        poSectionSeries[code] = [
          ...sectionOrder
            .filter((label) => poBySection[code]?.[label])
            .map((label) => ({ section: label, value: average(poBySection[code][label]) })),
          { section: "Average", value: average(poValues.get(code) ?? []), isAverage: true },
        ]
      }

      // "All" view: one grouped-bar row per section (plus a trailing "Average"
      // row matching coSummary/poSummary), one bar series per outcome code.
      type GroupedRow = { section: string; isAverage?: boolean } & Record<string, number | null | string | boolean | undefined>
      const coGrouped: GroupedRow[] = [
        ...sectionOrder.map((label) => {
          const row: GroupedRow = { section: label }
          for (const code of coCodes) row[code] = coBySection[code]?.[label] ? average(coBySection[code][label]) : null
          return row
        }),
        (() => {
          const row: GroupedRow = { section: "Average", isAverage: true }
          for (const code of coCodes) row[code] = average(coValues.get(code) ?? [])
          return row
        })(),
      ]
      const poGrouped: GroupedRow[] = [
        ...sectionOrder.map((label) => {
          const row: GroupedRow = { section: label }
          for (const code of poCodes) row[code] = poBySection[code]?.[label] ? average(poBySection[code][label]) : null
          return row
        }),
        (() => {
          const row: GroupedRow = { section: "Average", isAverage: true }
          for (const code of poCodes) row[code] = average(poValues.get(code) ?? [])
          return row
        })(),
      ]

      const threshold = Number(
        rows.find((row) => row.attainment)?.attainment?.threshold_co_score_pct ?? 50
      )

      return {
        rows,
        gradeChart,
        coSummary,
        poSummary,
        coCodes,
        poCodes,
        coSectionSeries,
        poSectionSeries,
        coGrouped,
        poGrouped,
        threshold,
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
  const activeCo = selectedCo || dashboard?.coCodes[0] || ""
  const activePo = selectedPo || dashboard?.poCodes[0] || ""
  const activeCoData = (activeCo && dashboard?.coSectionSeries[activeCo]) || []
  const activePoData = (activePo && dashboard?.poSectionSeries[activePo]) || []

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
            <ChartCard
              title="CO Attainment by Section"
              icon={<ChartNoAxesCombined className="h-4 w-4" />}
              empty={dashboard.coCodes.length === 0}
              actions={
                <Select value={activeCo} onValueChange={(v) => setSelectedCo((v as string) ?? "")}>
                  <SelectTrigger className="h-8 w-24 text-xs">
                    <SelectValue placeholder="CO">{activeCo === ALL_VALUE ? "All" : (activeCo || undefined)}</SelectValue>
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value={ALL_VALUE}>All</SelectItem>
                    {dashboard.coCodes.map((code) => (
                      <SelectItem key={code} value={code}>{code}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              }
            >
              {activeCo === ALL_VALUE ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={dashboard.coGrouped} margin={{ top: 16, right: 16, bottom: 8, left: -16 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="section" tickLine={false} axisLine={false} />
                    <YAxis domain={[0, 100]} tickLine={false} axisLine={false} unit="%" />
                    <RechartsTooltip formatter={(value, name) => [`${value}%`, name]} />
                    <Legend />
                    {dashboard.coCodes.map((code, i) => (
                      <Bar key={code} dataKey={code} name={code} fill={codeColor(i)} radius={[3, 3, 0, 0]}>
                        {dashboard.coGrouped.map((row) => {
                          const value = row[code] as number | null
                          const below = value != null && value < dashboard.threshold
                          return (
                            <Cell
                              key={row.section}
                              fill={codeColor(i)}
                              stroke={below ? STATUS_CRITICAL : undefined}
                              strokeWidth={below ? 2 : 0}
                            />
                          )
                        })}
                      </Bar>
                    ))}
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={activeCoData} margin={{ top: 16, right: 16, bottom: 8, left: -16 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="section" tickLine={false} axisLine={false} />
                    <YAxis domain={[0, 100]} tickLine={false} axisLine={false} unit="%" />
                    <RechartsTooltip formatter={(value) => [`${value}%`, `${activeCo} attainment`]} />
                    <Bar dataKey="value" name={`${activeCo} attainment`} radius={[4, 4, 0, 0]}>
                      {activeCoData.map((entry) => (
                        <Cell
                          key={entry.section}
                          fill={entry.value < dashboard.threshold ? STATUS_CRITICAL : CO_COLOR}
                          stroke={entry.isAverage ? "#111827" : undefined}
                          strokeWidth={entry.isAverage ? 2 : 0}
                          strokeDasharray={entry.isAverage ? "3 2" : undefined}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              )}
            </ChartCard>

            <ChartCard
              title="PO Attainment by Section"
              icon={<ChartNoAxesCombined className="h-4 w-4" />}
              empty={dashboard.poCodes.length === 0}
              actions={
                <Select value={activePo} onValueChange={(v) => setSelectedPo((v as string) ?? "")}>
                  <SelectTrigger className="h-8 w-24 text-xs">
                    <SelectValue placeholder="PO">{activePo === ALL_VALUE ? "All" : (activePo || undefined)}</SelectValue>
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value={ALL_VALUE}>All</SelectItem>
                    {dashboard.poCodes.map((code) => (
                      <SelectItem key={code} value={code}>{code}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              }
            >
              {activePo === ALL_VALUE ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={dashboard.poGrouped} margin={{ top: 16, right: 16, bottom: 8, left: -16 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="section" tickLine={false} axisLine={false} />
                    <YAxis domain={[0, 100]} tickLine={false} axisLine={false} unit="%" />
                    <RechartsTooltip formatter={(value, name) => [`${value}%`, name]} />
                    <Legend />
                    {dashboard.poCodes.map((code, i) => (
                      <Bar key={code} dataKey={code} name={code} fill={codeColor(i)} radius={[3, 3, 0, 0]}>
                        {dashboard.poGrouped.map((row) => {
                          const value = row[code] as number | null
                          const below = value != null && value < dashboard.threshold
                          return (
                            <Cell
                              key={row.section}
                              fill={codeColor(i)}
                              stroke={below ? STATUS_CRITICAL : undefined}
                              strokeWidth={below ? 2 : 0}
                            />
                          )
                        })}
                      </Bar>
                    ))}
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={activePoData} margin={{ top: 16, right: 16, bottom: 8, left: -16 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="section" tickLine={false} axisLine={false} />
                    <YAxis domain={[0, 100]} tickLine={false} axisLine={false} unit="%" />
                    <RechartsTooltip formatter={(value) => [`${value}%`, `${activePo} attainment`]} />
                    <Bar dataKey="value" name={`${activePo} attainment`} radius={[4, 4, 0, 0]}>
                      {activePoData.map((entry) => (
                        <Cell
                          key={entry.section}
                          fill={entry.value < dashboard.threshold ? STATUS_CRITICAL : PO_COLOR}
                          stroke={entry.isAverage ? "#111827" : undefined}
                          strokeWidth={entry.isAverage ? 2 : 0}
                          strokeDasharray={entry.isAverage ? "3 2" : undefined}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              )}
            </ChartCard>
          </div>

          <div className="grid gap-4 lg:grid-cols-3">
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

          <div className="grid gap-4 xl:grid-cols-[1fr_1.25fr]">
            <SummaryCard title="Average CO Attainment Across Sections" items={dashboard.coSummary} threshold={dashboard.threshold} />
            <SummaryCard title="Average PO Attainment Across Sections" items={dashboard.poSummary} threshold={dashboard.threshold} />
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

function SummaryCard({ title, items, threshold }: { title: string; items: Array<{ code: string; value: number }>; threshold: number }) {
  return (
    <Card>
      <CardHeader><CardTitle className="flex items-center gap-2 text-sm"><BarChart3 className="h-4 w-4" />{title}</CardTitle></CardHeader>
      <CardContent className="space-y-2">
        {items.length === 0 ? <p className="text-sm text-muted-foreground">No attainment data yet.</p> : items.map((item) => (
          <div key={item.code} className="flex items-center justify-between rounded border px-3 py-2">
            <span className="font-medium">{item.code}</span>
            <Badge variant={item.value >= threshold ? "default" : "destructive"}>{item.value}%</Badge>
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
  actions,
}: {
  title: string
  icon: React.ReactNode
  empty: boolean
  children: React.ReactNode
  heightClassName?: string
  actions?: React.ReactNode
}) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="flex items-center gap-2 text-sm">
          {icon}
          {title}
        </CardTitle>
        {actions}
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
