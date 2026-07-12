"use client"

import { useMemo, useState } from "react"
import Link from "next/link"
import { useSearchParams } from "next/navigation"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { ArrowLeft, BarChart3, Check, GraduationCap, Loader2, PieChartIcon, Radar } from "lucide-react"
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar as RadarSeries,
  RadarChart,
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
import { useHasAnyPermission } from "@/hooks/use-permission"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"
import { CATEGORICAL_COLORS, SEQUENTIAL_PRIMARY } from "@/lib/result-colors"

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
  student_count: number
}

type AttainmentResponse = {
  pos: Array<{ po_code: string; students_above_threshold: number; total_students: number }>
}

interface Props {
  batchId: string
}

// One hue for PO attainment (bar + radar both show the same data role, so
// they share a color); the categorical palette is reserved for the
// course-contribution pie, where slices are genuinely distinct courses.
const PO_COLOR = SEQUENTIAL_PRIMARY
const COURSE_COLORS = CATEGORICAL_COLORS

function pct(count: number, total: number) {
  return total > 0 ? Math.round((count / total) * 1000) / 10 : 0
}

function average(values: number[]) {
  return values.length ? Math.round(values.reduce((s, n) => s + n, 0) / values.length * 10) / 10 : 0
}

function naturalSort(a: string, b: string) {
  return a.localeCompare(b, undefined, { numeric: true, sensitivity: "base" })
}

export function BatchPoDashboardClient({ batchId }: Props) {
  const qc = useQueryClient()
  const searchParams = useSearchParams()
  const termId = searchParams.get("term_id")
  const batchName = searchParams.get("batch")
  const termLabel = searchParams.get("term")
  const [selectedPo, setSelectedPo] = useState<string>("")
  const canPublish = useHasAnyPermission(["result.approve.pc"])

  const { data: submissions = [], isLoading: loadingSubmissions } = useQuery({
    queryKey: queryKeys.results.submissions({ batch_id: batchId, term_id: termId ?? undefined, batch_dashboard: true }),
    queryFn: async () => {
      const { data } = await apiClient.GET("/results" as never, {
        params: { query: termId ? { batch_id: batchId, academic_term_id: termId } : { batch_id: batchId } },
      } as never)
      return ((data as unknown) as ResultSubmission[]) ?? []
    },
  })

  const { data: dashboard, isLoading: loadingDetails } = useQuery({
    queryKey: ["result-submissions", "batch-po-dashboard", batchId, termId, submissions.map((s) => s.section_offering_id).join(",")],
    enabled: submissions.length > 0,
    queryFn: async () => {
      const rows = await Promise.all(
        submissions.map(async (section) => {
          const { data } = await apiClient.GET(`/marksheets/${section.section_offering_id}/attainment` as never).catch(() => ({ data: null }))
          return { section, attainment: data as AttainmentResponse | null }
        })
      )

      const poValues = new Map<string, number[]>()
      const coursePoValues = new Map<string, { course: ResultSubmission; values: Map<string, number[]> }>()
      for (const row of rows) {
        const courseKey = row.section.course_id
        const courseBucket = coursePoValues.get(courseKey) ?? { course: row.section, values: new Map<string, number[]>() }
        for (const po of row.attainment?.pos ?? []) {
          const value = pct(po.students_above_threshold, po.total_students)
          const all = poValues.get(po.po_code) ?? []
          all.push(value)
          poValues.set(po.po_code, all)

          const courseVals = courseBucket.values.get(po.po_code) ?? []
          courseVals.push(value)
          courseBucket.values.set(po.po_code, courseVals)
        }
        coursePoValues.set(courseKey, courseBucket)
      }

      const poCodes = Array.from(poValues.keys()).sort(naturalSort)
      return {
        rows,
        poSummary: poCodes.map((code) => ({ code, value: average(poValues.get(code) ?? []) })),
        courseRows: Array.from(coursePoValues.values()).map((entry) => ({
          course: entry.course,
          po: Object.fromEntries(poCodes.map((code) => [code, average(entry.values.get(code) ?? [])])),
        })),
        poCodes,
      }
    },
  })

  const publishMutation = useMutation({
    mutationFn: async () => {
      const { data } = await apiClient.POST("/results/bulk-approve-pc" as never, {
        body: { batch_id: batchId, academic_term_id: termId },
      } as never)
      return (data as unknown) as { published_count: number }
    },
    onSuccess: (data) => {
      toast.success(
        `Published ${data.published_count} section${data.published_count === 1 ? "" : "s"} — students can now see their results`
      )
      qc.invalidateQueries({ queryKey: queryKeys.results.all })
    },
    onError: () => toast.error("Failed to publish results for this semester"),
  })

  const pieData = useMemo(() => {
    if (!dashboard || !selectedPo) return []
    return dashboard.courseRows
      .filter((row) => (row.po[selectedPo] ?? 0) > 0)
      .map((row, index) => ({
        name: row.course.course_code,
        value: row.po[selectedPo],
        fill: COURSE_COLORS[index % COURSE_COLORS.length],
      }))
  }, [dashboard, selectedPo])

  const isLoading = loadingSubmissions || loadingDetails
  const resolvedBatchName = batchName ?? submissions[0]?.batch_name ?? "Batch"
  const resolvedTermLabel = termLabel ?? (submissions[0] ? `${submissions[0].term_name} (${submissions[0].term_season} ${submissions[0].term_year})` : "")
  const totalCourses = new Set(submissions.map((s) => s.course_id)).size
  const totalSections = submissions.length
  const pcReviewCount = submissions.filter((s) => s.status === "ML_APPROVED").length

  const effectiveSelectedPo = selectedPo || dashboard?.poCodes[0] || ""

  return (
    <div className="space-y-6">
      <PageHeader
        title={`${resolvedBatchName} PO Dashboard`}
        description={termId ? `Batch-level PO attainment for ${resolvedTermLabel}.` : "Batch-level PO attainment across courses and semesters."}
        actions={
          <div className="flex items-center gap-2">
            {canPublish && termId && pcReviewCount > 0 && (
              <Button
                size="sm"
                disabled={publishMutation.isPending}
                onClick={() => publishMutation.mutate()}
              >
                {publishMutation.isPending ? <Loader2 className="animate-spin" /> : <Check />}
                Publish {pcReviewCount} section{pcReviewCount === 1 ? "" : "s"} for this semester
              </Button>
            )}
            <Button size="sm" variant="outline" nativeButton={false} render={<Link href="/result-submissions" />}>
              <ArrowLeft /> Result Submissions
            </Button>
          </div>
        }
      />

      {canPublish && !termId && (
        <p className="text-xs text-muted-foreground">
          Select a specific semester (open this dashboard from a course&apos;s batch/term group) to publish results for it.
        </p>
      )}

      <div className="grid gap-4 sm:grid-cols-3">
        <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">Courses</p><p className="text-2xl font-semibold">{totalCourses}</p></CardContent></Card>
        <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">Sections</p><p className="text-2xl font-semibold">{totalSections}</p></CardContent></Card>
        <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">Scope</p><p className="text-sm font-medium">{termId ? resolvedTermLabel : "All visible semesters"}</p></CardContent></Card>
      </div>

      {isLoading && <div className="h-40 animate-pulse rounded-lg bg-muted" />}

      {!isLoading && dashboard && (
        <>
          <div className="grid gap-4 lg:grid-cols-2">
            <ChartCard
              title="PO Attainment Overview"
              icon={<BarChart3 className="h-4 w-4" />}
              empty={dashboard.poSummary.length === 0}
            >
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={dashboard.poSummary} margin={{ top: 16, right: 16, bottom: 8, left: -16 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="code" tickLine={false} axisLine={false} />
                  <YAxis domain={[0, 100]} tickLine={false} axisLine={false} unit="%" />
                  <RechartsTooltip formatter={(value) => [`${value}%`, "Attainment"]} />
                  <Bar dataKey="value" name="Attainment" fill={PO_COLOR} radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>

            <ChartCard
              title="Batch PO Attainment Spider Graph"
              icon={<Radar className="h-4 w-4" />}
              empty={dashboard.poSummary.length === 0}
            >
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart data={dashboard.poSummary.map((p) => ({ outcome: p.code, attainment: p.value }))} outerRadius="72%">
                  <PolarGrid />
                  <PolarAngleAxis dataKey="outcome" tick={{ fontSize: 12 }} />
                  <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fontSize: 11 }} tickCount={6} />
                  <RadarSeries
                    name="Attainment"
                    dataKey="attainment"
                    stroke={PO_COLOR}
                    fill={PO_COLOR}
                    fillOpacity={0.24}
                    dot={{ r: 3, fill: PO_COLOR }}
                  />
                  <RechartsTooltip formatter={(value) => [`${value}%`, "Attainment"]} />
                </RadarChart>
              </ResponsiveContainer>
            </ChartCard>
          </div>

          <Card>
            <CardHeader>
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <CardTitle className="flex items-center gap-2 text-sm">
                  <PieChartIcon className="h-4 w-4" />Course Contribution to a PO
                </CardTitle>
                <div className="w-32">
                  <Select value={effectiveSelectedPo} onValueChange={(v) => v != null && setSelectedPo(v as string)}>
                    <SelectTrigger className="h-8 text-xs">
                      <SelectValue placeholder="Select PO" />
                    </SelectTrigger>
                    <SelectContent>
                      {dashboard.poCodes.map((code) => (
                        <SelectItem key={code} value={code}>{code}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {pieData.length === 0 ? (
                <div className="flex h-64 items-center justify-center rounded-md border border-dashed text-sm text-muted-foreground">
                  No attainment data yet for {effectiveSelectedPo || "this PO"}.
                </div>
              ) : (
                <div className="h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius="80%" label={(d) => `${d.name}: ${d.value}%`}>
                        {pieData.map((entry) => <Cell key={entry.name} fill={entry.fill} />)}
                      </Pie>
                      <RechartsTooltip formatter={(value, _name, item) => [`${value}%`, item.payload.name]} />
                      <Legend />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle className="flex items-center gap-2 text-sm"><GraduationCap className="h-4 w-4" />Overall PO Attainment</CardTitle></CardHeader>
            <CardContent className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
              {dashboard.poSummary.length === 0 ? (
                <p className="text-sm text-muted-foreground">No PO attainment data yet.</p>
              ) : dashboard.poSummary.map((po) => (
                <div key={po.code} className="flex items-center justify-between rounded border px-3 py-2">
                  <span className="font-medium">{po.code}</span>
                  <Badge variant={po.value >= 50 ? "default" : "destructive"}>{po.value}%</Badge>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle className="text-sm">Course Contributions to Batch PO Attainment</CardTitle></CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Course</TableHead>
                    <TableHead>Semester</TableHead>
                    {dashboard.poCodes.map((po) => <TableHead key={po} className="text-right">{po}</TableHead>)}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {dashboard.courseRows.map((row) => (
                    <TableRow key={row.course.course_id}>
                      <TableCell>
                        <div className="font-mono text-xs">{row.course.course_code}</div>
                        <div>{row.course.course_title}</div>
                      </TableCell>
                      <TableCell>{row.course.term_name} ({row.course.term_season} {row.course.term_year})</TableCell>
                      {dashboard.poCodes.map((po) => (
                        <TableCell key={po} className="text-right">
                          {row.po[po] ? `${row.po[po]}%` : "—"}
                        </TableCell>
                      ))}
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

function ChartCard({
  title,
  icon,
  empty,
  children,
}: {
  title: string
  icon: React.ReactNode
  empty: boolean
  children: React.ReactNode
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
          <div className="flex h-64 items-center justify-center rounded-md border border-dashed text-sm text-muted-foreground">
            No chart data yet.
          </div>
        ) : (
          <div className="h-72">{children}</div>
        )}
      </CardContent>
    </Card>
  )
}
