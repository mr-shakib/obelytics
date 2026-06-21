"use client"

import { useQuery } from "@tanstack/react-query"
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine, Cell, LabelList,
} from "recharts"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { apiClient } from "@/lib/api/client"
import { cn } from "@/lib/utils"

// ── Types ─────────────────────────────────────────────────────────────────────

interface COResult {
  co_code: string
  co_statement: string
  attainment_percentage: number
  threshold: number
  is_threshold_met: boolean
}

interface POResult {
  po_code: string
  po_statement?: string | null
  attainment_percentage: number
  threshold: number
  is_threshold_met: boolean
}

interface CourseResult {
  course_code: string
  course_title: string
  term_name: string
  result_status: string
  total_marks_obtained: number
  total_marks: number
  percentage: number
  grade?: string
  co_results: COResult[]
  po_results: POResult[]
}

// ── PO Aggregation ────────────────────────────────────────────────────────────

interface POAggregate {
  po_code: string
  po_statement: string | null
  avg_pct: number
  threshold: number
  is_attained: boolean
  contributions: { course_code: string; course_title: string; pct: number }[]
}

function aggregatePOs(courses: CourseResult[]): POAggregate[] {
  const map = new Map<string, {
    statement: string | null
    threshold: number
    values: { course_code: string; course_title: string; pct: number }[]
  }>()

  for (const course of courses) {
    for (const po of course.po_results ?? []) {
      if (!map.has(po.po_code)) {
        map.set(po.po_code, { statement: po.po_statement ?? null, threshold: po.threshold, values: [] })
      }
      map.get(po.po_code)!.values.push({
        course_code: course.course_code,
        course_title: course.course_title,
        pct: po.attainment_percentage,
      })
    }
  }

  return Array.from(map.entries())
    .map(([po_code, { statement, threshold, values }]) => {
      const avg_pct = values.reduce((s, v) => s + v.pct, 0) / values.length
      return { po_code, po_statement: statement, avg_pct, threshold, is_attained: avg_pct >= threshold, contributions: values }
    })
    .sort((a, b) => a.po_code.localeCompare(b.po_code, undefined, { numeric: true }))
}

// ── Custom tooltip ────────────────────────────────────────────────────────────

function POChartTooltip({ active, payload }: { active?: boolean; payload?: { payload: POAggregate }[] }) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div className="rounded-lg border bg-popover px-3 py-2.5 text-xs shadow-lg min-w-[200px] max-w-[280px]">
      <p className="font-bold text-sm mb-0.5">{d.po_code}</p>
      {d.po_statement && (
        <p className="text-muted-foreground mb-2 leading-snug">{d.po_statement}</p>
      )}
      <div className="border-t pt-1.5 space-y-1">
        <p className="text-muted-foreground font-medium mb-1">Course Breakdown</p>
        {d.contributions.map((c) => (
          <div key={c.course_code} className="flex items-center justify-between gap-3">
            <span className="text-muted-foreground truncate">{c.course_code}</span>
            <span className={cn("tabular-nums font-semibold", c.pct >= d.threshold ? "text-green-600" : "text-red-500")}>
              {c.pct.toFixed(1)}%
            </span>
          </div>
        ))}
        <div className="border-t mt-1 pt-1 flex items-center justify-between font-semibold">
          <span>Average</span>
          <span className={d.is_attained ? "text-green-600" : "text-red-500"}>{d.avg_pct.toFixed(1)}%</span>
        </div>
      </div>
    </div>
  )
}

// ── PO Summary Chart ──────────────────────────────────────────────────────────

function POSummarySection({ courses }: { courses: CourseResult[] }) {
  const pos = aggregatePOs(courses)
  if (pos.length === 0) return null

  const threshold = pos[0]?.threshold ?? 50
  const attainedCount = pos.filter((p) => p.is_attained).length

  // collect unique courses that appear in PO data
  const allCourseCodes = Array.from(
    new Set(pos.flatMap((p) => p.contributions.map((c) => c.course_code)))
  ).sort()

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2 flex-wrap">
          <div>
            <CardTitle className="text-lg">Program Outcome Attainment</CardTitle>
            <CardDescription className="mt-0.5">
              Average PO attainment across all your courses
            </CardDescription>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <Badge variant={attainedCount === pos.length ? "default" : "secondary"}>
              {attainedCount}/{pos.length} POs attained
            </Badge>
            <Badge variant="outline" className="text-xs">Threshold: {threshold}%</Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-5">
        {/* Bar Chart */}
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={pos} margin={{ top: 20, right: 8, left: -20, bottom: 4 }} barSize={28}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-border" vertical={false} />
              <XAxis dataKey="po_code" tick={{ fontSize: 11, fontWeight: 600 }} axisLine={false} tickLine={false} />
              <YAxis domain={[0, 100]} tick={{ fontSize: 10 }} axisLine={false} tickLine={false} tickFormatter={(v) => `${v}%`} />
              <Tooltip content={<POChartTooltip />} cursor={{ fill: "hsl(var(--muted))", opacity: 0.5 }} />
              <ReferenceLine
                y={threshold}
                stroke="hsl(var(--destructive))"
                strokeDasharray="5 3"
                label={{ value: `${threshold}%`, fontSize: 9, fill: "hsl(var(--destructive))", position: "insideTopRight" }}
              />
              <Bar dataKey="avg_pct" radius={[4, 4, 0, 0]}>
                <LabelList
                  dataKey="avg_pct"
                  position="top"
                  formatter={(v: number) => `${v.toFixed(0)}%`}
                  style={{ fontSize: 10, fontWeight: 700 }}
                />
                {pos.map((entry) => (
                  <Cell
                    key={entry.po_code}
                    fill={entry.is_attained ? "hsl(142 71% 45%)" : "hsl(var(--destructive))"}
                    fillOpacity={0.85}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Legend */}
        <div className="flex items-center gap-4 text-xs text-muted-foreground justify-end">
          <span className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-sm bg-green-500 inline-block" /> Attained
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-sm bg-destructive inline-block" /> Not attained
          </span>
        </div>

        {/* Per-course breakdown table */}
        {allCourseCodes.length > 1 && (
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
              Attainment by Course
            </p>
            <div className="overflow-x-auto rounded-lg border">
              <table className="w-full text-xs">
                <thead>
                  <tr className="bg-muted/50">
                    <th className="text-left px-3 py-2 font-semibold">PO</th>
                    {allCourseCodes.map((code) => (
                      <th key={code} className="text-center px-3 py-2 font-semibold">{code}</th>
                    ))}
                    <th className="text-center px-3 py-2 font-semibold border-l">Avg</th>
                    <th className="text-center px-3 py-2 font-semibold">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {pos.map((po, i) => {
                    const contribMap = Object.fromEntries(po.contributions.map((c) => [c.course_code, c.pct]))
                    return (
                      <tr key={po.po_code} className={i % 2 === 0 ? "bg-background" : "bg-muted/20"}>
                        <td className="px-3 py-1.5 font-semibold">{po.po_code}</td>
                        {allCourseCodes.map((code) => {
                          const pct = contribMap[code]
                          return (
                            <td key={code} className="text-center px-3 py-1.5">
                              {pct !== undefined ? (
                                <span className={cn("font-medium", pct >= threshold ? "text-green-600" : "text-red-500")}>
                                  {pct.toFixed(1)}%
                                </span>
                              ) : (
                                <span className="text-muted-foreground">—</span>
                              )}
                            </td>
                          )
                        })}
                        <td className={cn("text-center px-3 py-1.5 font-semibold border-l", po.is_attained ? "text-green-600" : "text-red-500")}>
                          {po.avg_pct.toFixed(1)}%
                        </td>
                        <td className="text-center px-3 py-1.5">
                          <Badge variant={po.is_attained ? "default" : "destructive"} className="text-[10px] px-1.5 py-0">
                            {po.is_attained ? "Attained" : "Not Attained"}
                          </Badge>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Single-course simple list */}
        {allCourseCodes.length === 1 && (
          <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 gap-2">
            {pos.map((po) => (
              <div
                key={po.po_code}
                className={cn(
                  "rounded-lg border px-3 py-2 text-center",
                  po.is_attained ? "border-green-300 bg-green-50" : "border-red-300 bg-red-50"
                )}
              >
                <p className="text-xs font-bold">{po.po_code}</p>
                <p className={cn("text-sm font-semibold mt-0.5", po.is_attained ? "text-green-700" : "text-red-600")}>
                  {po.avg_pct.toFixed(1)}%
                </p>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

// ── Per-course card ───────────────────────────────────────────────────────────

function CourseCard({ course }: { course: CourseResult }) {
  const sortedCOs = [...(course.co_results ?? [])].sort((a, b) =>
    a.co_code.localeCompare(b.co_code, undefined, { numeric: true })
  )
  const sortedPOs = [...(course.po_results ?? [])].sort((a, b) =>
    a.po_code.localeCompare(b.po_code, undefined, { numeric: true })
  )

  return (
    <Card>
      {/* Course header */}
      <CardHeader className="pb-3 border-b">
        <div className="flex items-start justify-between gap-3 flex-wrap">
          <div>
            <CardTitle className="text-base leading-snug">{course.course_title}</CardTitle>
            <p className="text-xs text-muted-foreground mt-0.5">{course.course_code} · {course.term_name}</p>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {course.grade && (
              <Badge className="text-sm font-bold px-2.5">{course.grade}</Badge>
            )}
            <span className="text-sm font-semibold tabular-nums">
              {course.total_marks_obtained}/{course.total_marks}
              <span className="text-muted-foreground font-normal ml-1">({course.percentage.toFixed(1)}%)</span>
            </span>
          </div>
        </div>
      </CardHeader>

      <CardContent className="pt-4 space-y-5">
        {/* CO Attainment */}
        {sortedCOs.length > 0 && (
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">
              Course Outcome Attainment
            </p>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
              {sortedCOs.map((co) => (
                <div
                  key={co.co_code}
                  className={cn(
                    "rounded-lg border px-3 py-2",
                    co.is_threshold_met
                      ? "border-green-200 bg-green-50 dark:bg-green-950/30 dark:border-green-800"
                      : "border-red-200 bg-red-50 dark:bg-red-950/30 dark:border-red-800"
                  )}
                >
                  <div className="flex items-center justify-between gap-1">
                    <span className="text-xs font-bold">{co.co_code}</span>
                    <span className={cn("text-xs", co.is_threshold_met ? "text-green-600" : "text-red-500")}>
                      {co.is_threshold_met ? "✓" : "✗"}
                    </span>
                  </div>
                  <p className={cn("text-sm font-semibold mt-0.5", co.is_threshold_met ? "text-green-700" : "text-red-600")}>
                    {co.attainment_percentage.toFixed(1)}%
                  </p>
                  <p className="text-[10px] text-muted-foreground leading-tight mt-0.5 line-clamp-2">
                    {co.co_statement}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* PO Attainment */}
        {sortedPOs.length > 0 && (
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">
              Program Outcome Attainment
            </p>
            <div className="space-y-2">
              {sortedPOs.map((po) => (
                <div key={po.po_code} className="flex items-center gap-3">
                  <span className="font-mono text-xs font-bold w-10 shrink-0 text-right">{po.po_code}</span>
                  <div className="flex-1 h-2.5 rounded-full bg-muted overflow-hidden">
                    <div
                      className={cn("h-full rounded-full transition-all", po.is_threshold_met ? "bg-green-500" : "bg-red-500")}
                      style={{ width: `${Math.min(100, Math.max(0, po.attainment_percentage))}%` }}
                    />
                  </div>
                  <span className="text-xs tabular-nums font-semibold w-12 text-right">
                    {po.attainment_percentage.toFixed(1)}%
                  </span>
                  <span className={cn("text-xs w-4 font-bold shrink-0", po.is_threshold_met ? "text-green-600" : "text-red-500")}>
                    {po.is_threshold_met ? "✓" : "✗"}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export function MyResultsClient() {
  const { data, isLoading } = useQuery({
    queryKey: ["student", "results"],
    queryFn: async () => {
      const { data } = await apiClient.GET("/students/me/results" as never)
      return (data as unknown) as CourseResult[]
    },
  })

  if (isLoading) {
    return (
      <div className="space-y-4">
        {[...Array(3)].map((_, i) => <Skeleton key={i} className="h-52 w-full" />)}
      </div>
    )
  }

  if (!data?.length) {
    return <p className="text-muted-foreground text-sm">No published results available yet.</p>
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">My Results</h1>

      {/* PO summary at the top */}
      <POSummarySection courses={data} />

      {/* Per-course breakdown */}
      <div className="space-y-4">
        <h2 className="text-base font-semibold text-muted-foreground uppercase tracking-wide">
          Course-wise Breakdown
        </h2>
        {data.map((course) => (
          <CourseCard key={course.course_code} course={course} />
        ))}
      </div>
    </div>
  )
}
