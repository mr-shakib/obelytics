"use client"

import { useMemo, useState } from "react"
import Link from "next/link"
import { ArrowLeft, ArrowRight, Download, Loader2 } from "lucide-react"
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine, Cell, LabelList,
  PieChart, Pie, Legend,
} from "recharts"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { CATEGORICAL_COLORS, STATUS_GOOD } from "@/lib/result-colors"
import { cn } from "@/lib/utils"

interface Outcome {
  co_code?: string
  po_code?: string
  co_statement?: string
  po_statement?: string | null
  attainment_percentage: number
  threshold: number
  is_threshold_met: boolean
}

interface CourseResult {
  course_code: string
  course_title: string
  term_name: string
  co_results: Outcome[]
  po_results: Outcome[]
}

const PIE_COLORS = CATEGORICAL_COLORS

interface ProgramOutcomeSummary {
  po_code: string
  po_statement?: string | null
}

interface PublicResults {
  student_id_number: string
  full_name: string
  results: CourseResult[]
  program_outcomes: ProgramOutcomeSummary[]
}

function initials(name: string) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase())
    .join("")
}

function OutcomeBar({ code, pct, threshold, met }: { code: string; pct: number; threshold: number; met: boolean }) {
  const w = Math.min(100, Math.max(0, pct))
  return (
    <div className="flex items-center gap-3">
      <span className="font-mono text-xs font-bold w-10 shrink-0 text-right">{code}</span>
      <div className="relative flex-1 h-2.5 rounded-full bg-muted overflow-hidden">
        <div
          className={cn("h-full rounded-full transition-all", met ? "bg-green-500" : "bg-destructive")}
          style={{ width: `${w}%` }}
        />
        <span className="absolute top-0 bottom-0 w-px bg-foreground/25" style={{ left: `${threshold}%` }} />
      </div>
      <span className="text-xs tabular-nums font-semibold w-12 text-right">{pct.toFixed(1)}%</span>
      <span className={cn("text-xs w-4 font-bold shrink-0", met ? "text-green-600" : "text-destructive")}>
        {met ? "✓" : "✗"}
      </span>
    </div>
  )
}

// ── PO aggregation ────────────────────────────────────────────────────────────

interface POBar {
  po_code: string
  avg_pct: number
  threshold: number
  is_attained: boolean
  contributions: { course_code: string; pct: number }[]
}

function aggregatePOs(results: CourseResult[], allPOs: ProgramOutcomeSummary[] = []): POBar[] {
  const map = new Map<string, { threshold: number; values: { course_code: string; pct: number }[] }>()
  for (const course of results) {
    for (const po of course.po_results ?? []) {
      if (!map.has(po.po_code!)) map.set(po.po_code!, { threshold: po.threshold, values: [] })
      map.get(po.po_code!)!.values.push({ course_code: course.course_code, pct: po.attainment_percentage })
    }
  }
  // Every active program outcome gets a slot even if none of the student's
  // published courses map to it yet — those show up with no bar and no contributions.
  const fallbackThreshold = map.size > 0 ? Array.from(map.values())[0].threshold : 50
  for (const po of allPOs) {
    if (!map.has(po.po_code)) map.set(po.po_code, { threshold: fallbackThreshold, values: [] })
  }
  return Array.from(map.entries())
    .map(([po_code, { threshold, values }]) => {
      const avg_pct = values.length ? values.reduce((s, v) => s + v.pct, 0) / values.length : 0
      return { po_code, avg_pct, threshold, is_attained: values.length > 0 && avg_pct >= threshold, contributions: values }
    })
    .sort((a, b) => a.po_code.localeCompare(b.po_code, undefined, { numeric: true }))
}

// ── PO tooltip ────────────────────────────────────────────────────────────────

function POTooltip({ active, payload }: { active?: boolean; payload?: { payload: POBar }[] }) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div className="rounded-lg border bg-popover px-3 py-2.5 text-xs shadow-lg min-w-[160px]">
      <p className="font-bold text-sm mb-1">{d.po_code}</p>
      {d.contributions.map((c) => (
        <div key={c.course_code} className="flex items-center justify-between gap-3">
          <span className="text-muted-foreground">{c.course_code}</span>
          <span className={cn("font-semibold", c.pct >= d.threshold ? "text-green-600" : "text-destructive")}>
            {c.pct.toFixed(1)}%
          </span>
        </div>
      ))}
      {d.contributions.length > 1 && (
        <div className="border-t mt-1 pt-1 flex items-center justify-between font-semibold">
          <span>Average</span>
          <span className={d.is_attained ? "text-green-600" : "text-destructive"}>{d.avg_pct.toFixed(1)}%</span>
        </div>
      )}
    </div>
  )
}

// ── PO summary chart ──────────────────────────────────────────────────────────

function POSummarySection({
  results,
  allPOs,
  selectedPo,
  onSelectPo,
}: {
  results: CourseResult[]
  allPOs: ProgramOutcomeSummary[]
  selectedPo: string
  onSelectPo: (code: string) => void
}) {
  const pos = aggregatePOs(results, allPOs)
  if (pos.length === 0) return null
  const threshold = pos[0].threshold
  const attained = pos.filter((p) => p.is_attained).length
  const chartData = pos.map((p) => ({ ...p, bar_pct: p.is_attained ? p.avg_pct : 0 }))
  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2 flex-wrap">
          <div>
            <CardTitle className="text-lg">Program Outcome Attainment</CardTitle>
            <CardDescription className="mt-0.5">
              Average attainment across all your courses — hover a bar for the course breakdown, or click it to see the split below
            </CardDescription>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <Badge variant={attained === pos.length ? "default" : "secondary"}>
              {attained}/{pos.length} attained
            </Badge>
            <Badge variant="outline" className="text-xs">Threshold {threshold}%</Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 20, right: 8, left: -20, bottom: 4 }} barSize={26}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-border" vertical={false} />
              <XAxis dataKey="po_code" tick={{ fontSize: 11, fontWeight: 600 }} axisLine={false} tickLine={false} />
              <YAxis domain={[0, 100]} tick={{ fontSize: 10 }} axisLine={false} tickLine={false} tickFormatter={(v) => `${v}%`} />
              <Tooltip content={<POTooltip />} cursor={{ fill: "var(--muted)", opacity: 0.5 }} />
              <ReferenceLine y={threshold} stroke="var(--destructive)" strokeDasharray="5 3"
                label={{ value: `${threshold}%`, fontSize: 9, fill: "var(--destructive)", position: "insideTopRight" }} />
              <Bar
                dataKey="bar_pct"
                radius={[4, 4, 0, 0]}
                background={{ fill: "var(--muted)", radius: 4 }}
                onClick={(entry) => onSelectPo((entry as unknown as POBar).po_code)}
                cursor="pointer"
              >
                <LabelList dataKey="bar_pct" position="top"
                  formatter={(v) => (Number(v) > 0 ? `${Number(v).toFixed(0)}%` : "")}
                  style={{ fontSize: 10, fontWeight: 700 }} />
                {chartData.map((p) => (
                  <Cell
                    key={p.po_code}
                    fill={STATUS_GOOD}
                    fillOpacity={!selectedPo || selectedPo === p.po_code ? 0.9 : 0.5}
                    stroke={selectedPo === p.po_code ? "var(--foreground)" : undefined}
                    strokeWidth={selectedPo === p.po_code ? 2 : 0}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="flex items-center gap-4 text-xs text-muted-foreground justify-end mt-2">
          <span className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-sm bg-green-500 inline-block" /> Attained
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-sm bg-muted border border-border inline-block" /> Not attained
          </span>
        </div>
      </CardContent>
    </Card>
  )
}

// ── PO course-contribution pie chart ──────────────────────────────────────────

function POContributionSection({
  results,
  allPOs,
  selectedPo,
  onSelectPo,
}: {
  results: CourseResult[]
  allPOs: ProgramOutcomeSummary[]
  selectedPo: string
  onSelectPo: (code: string) => void
}) {
  const pos = useMemo(() => aggregatePOs(results, allPOs), [results, allPOs])
  const effectivePo = selectedPo || pos[0]?.po_code || ""
  const active = pos.find((p) => p.po_code === effectivePo)

  const pieData = useMemo(
    () => (active?.contributions ?? []).map((c, i) => ({
      name: c.course_code,
      value: Math.round(c.pct * 10) / 10,
      fill: PIE_COLORS[i % PIE_COLORS.length],
    })),
    [active]
  )

  if (pos.length === 0) return null

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2 flex-wrap">
          <div>
            <CardTitle className="text-lg">Which Courses Earned You This PO</CardTitle>
            <CardDescription className="mt-0.5">
              {(active?.contributions.length ?? 0) > 1
                ? `${effectivePo} was attained across ${active?.contributions.length} courses — each slice is that course's share`
                : `${effectivePo} attainment`}
            </CardDescription>
          </div>
          <select
            value={effectivePo}
            onChange={(e) => onSelectPo(e.target.value)}
            className="h-8 rounded-lg border border-input bg-transparent px-2.5 text-xs font-medium outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
          >
            {pos.map((p) => (
              <option key={p.po_code} value={p.po_code}>{p.po_code}</option>
            ))}
          </select>
        </div>
      </CardHeader>
      <CardContent>
        {pieData.length === 0 ? (
          <p className="text-sm text-muted-foreground py-8 text-center">No attainment data yet for {effectivePo}.</p>
        ) : (
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={pieData}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius="80%"
                  label={(d) => `${d.name}: ${d.value}%`}
                >
                  {pieData.map((entry) => <Cell key={entry.name} fill={entry.fill} />)}
                </Pie>
                <Tooltip formatter={(value, _name, item) => [`${value}%`, item.payload.name]} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

// ── Per-course card ───────────────────────────────────────────────────────────

function CourseCard({ course }: { course: CourseResult }) {
  const sortedCOs = [...(course.co_results ?? [])].sort((a, b) =>
    (a.co_code ?? "").localeCompare(b.co_code ?? "", undefined, { numeric: true })
  )
  const sortedPOs = [...(course.po_results ?? [])].sort((a, b) =>
    (a.po_code ?? "").localeCompare(b.po_code ?? "", undefined, { numeric: true })
  )

  return (
    <Card>
      <CardHeader className="pb-3 border-b">
        <CardTitle className="text-base leading-snug">{course.course_title}</CardTitle>
        <p className="text-xs text-muted-foreground mt-0.5">{course.course_code} · {course.term_name}</p>
      </CardHeader>
      <CardContent className="pt-4 space-y-5">
        {sortedCOs.length > 0 && (
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">
              Course Outcomes
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
                    <span className={cn("text-xs", co.is_threshold_met ? "text-green-600" : "text-destructive")}>
                      {co.is_threshold_met ? "✓" : "✗"}
                    </span>
                  </div>
                  <p className={cn("text-sm font-semibold mt-0.5", co.is_threshold_met ? "text-green-700" : "text-destructive")}>
                    {co.attainment_percentage.toFixed(1)}%
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        {sortedPOs.length > 0 && (
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">
              Program Outcomes
            </p>
            <div className="space-y-2">
              {sortedPOs.map((po) => (
                <OutcomeBar
                  key={po.po_code}
                  code={po.po_code ?? ""}
                  pct={po.attainment_percentage}
                  threshold={po.threshold}
                  met={po.is_threshold_met}
                />
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export default function PublicResultPage() {
  const [uid, setUid] = useState("")
  const [loading, setLoading] = useState(false)
  const [downloading, setDownloading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<PublicResults | null>(null)
  const [selectedPo, setSelectedPo] = useState("")

  async function lookup(e?: React.FormEvent) {
    e?.preventDefault()
    const trimmed = uid.trim()
    if (!trimmed) return
    setLoading(true)
    setError(null)
    setData(null)
    setSelectedPo("")
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/v1/public/student-results?uid=${encodeURIComponent(trimmed)}`
      )
      if (res.status === 404) {
        setError("We couldn't find a student with that ID. Check the number and try again.")
        return
      }
      if (!res.ok) {
        setError("Something went wrong on our end. Please try again.")
        return
      }
      setData((await res.json()) as PublicResults)
    } catch {
      setError("Couldn't reach the server. Try again in a moment.")
    } finally {
      setLoading(false)
    }
  }

  async function downloadReport() {
    if (!data) return
    setDownloading(true)
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/v1/public/student-results/pdf?uid=${encodeURIComponent(data.student_id_number)}`
      )
      if (!res.ok) {
        setError("Couldn't generate the report. Please try again.")
        return
      }
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = `${data.student_id_number}_PO_Attainment_Report.pdf`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch {
      setError("Couldn't reach the server. Try again in a moment.")
    } finally {
      setDownloading(false)
    }
  }

  const allCos = data?.results.flatMap((c) => c.co_results) ?? []
  const metCos = allCos.filter((o) => o.is_threshold_met).length
  const attainmentRate = allCos.length ? Math.round((metCos / allCos.length) * 100) : 0

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b print:hidden">
        <div className="max-w-3xl mx-auto px-4 py-3 flex items-center justify-between">
          <Link href="/" className="font-bold text-lg tracking-tight">Obelytics</Link>
          <Link href="/" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors">
            <ArrowLeft className="h-4 w-4" /> Home
          </Link>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-10 space-y-6">
        <div className="print:hidden">
          <p className="text-xs font-semibold uppercase tracking-widest text-muted-foreground mb-2">Outcome-Based Result</p>
          <h1 className="text-3xl font-bold tracking-tight">Check your result</h1>
          <p className="mt-1.5 text-muted-foreground max-w-md">
            Enter your student ID to see your grades and how you attained each course and program outcome.
          </p>

          <form className="mt-6 flex gap-2 max-w-md" onSubmit={lookup}>
            <Input
              value={uid}
              onChange={(e) => setUid(e.target.value)}
              placeholder="2021-1-60-001"
              aria-label="Student ID"
              autoFocus
              className="h-10 font-mono"
            />
            <Button type="submit" disabled={loading || !uid.trim()} className="h-10 px-4">
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowRight className="h-4 w-4" />}
              View result
            </Button>
          </form>
          {error && <p className="mt-3 text-sm text-destructive">{error}</p>}
        </div>

        {data && (
          <>
            <Card>
              <CardContent className="py-5 flex items-center gap-4 flex-wrap">
                <div className="w-12 h-12 rounded-full bg-primary text-primary-foreground grid place-items-center font-bold shrink-0">
                  {initials(data.full_name)}
                </div>
                <div>
                  <p className="font-bold leading-tight">{data.full_name}</p>
                  <p className="text-xs text-muted-foreground font-mono mt-0.5">ID {data.student_id_number}</p>
                </div>
                {data.results.length > 0 && (
                  <div className="ml-auto flex items-center gap-6">
                    <div>
                      <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Courses</p>
                      <p className="text-xl font-bold tabular-nums">{data.results.length}</p>
                    </div>
                    <div>
                      <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Outcomes met</p>
                      <p className="text-xl font-bold tabular-nums">{metCos}/{allCos.length}</p>
                    </div>
                    <div>
                      <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Attainment</p>
                      <p className="text-xl font-bold tabular-nums">{attainmentRate}%</p>
                    </div>
                    <Button variant="outline" size="sm" onClick={downloadReport} disabled={downloading}>
                      {downloading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Download className="h-3.5 w-3.5" />}
                      Download Report
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>

            {data.results.length === 0 ? (
              <Card>
                <CardContent className="py-12 text-center text-muted-foreground text-sm">
                  No published results yet. They&apos;ll appear here once your department publishes them.
                </CardContent>
              </Card>
            ) : (
              <>
                <POSummarySection results={data.results} allPOs={data.program_outcomes} selectedPo={selectedPo} onSelectPo={setSelectedPo} />
                <POContributionSection results={data.results} allPOs={data.program_outcomes} selectedPo={selectedPo} onSelectPo={setSelectedPo} />
                <div className="space-y-4">
                  {data.results.map((course) => (
                    <CourseCard key={`${course.course_code}-${course.term_name}`} course={course} />
                  ))}
                </div>
              </>
            )}
          </>
        )}
      </main>
    </div>
  )
}
