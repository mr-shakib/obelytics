"use client"

import Link from "next/link"
import { useSearchParams } from "next/navigation"
import { useQuery } from "@tanstack/react-query"
import { ArrowLeft, GraduationCap } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"
import { PageHeader } from "@/components/shared/page-header"
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
  student_count: number
}

type AttainmentResponse = {
  pos: Array<{ po_code: string; students_above_threshold: number; total_students: number }>
}

interface Props {
  batchId: string
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

export function BatchPoDashboardClient({ batchId }: Props) {
  const searchParams = useSearchParams()
  const termId = searchParams.get("term_id")
  const batchName = searchParams.get("batch")
  const termLabel = searchParams.get("term")

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

  const isLoading = loadingSubmissions || loadingDetails
  const resolvedBatchName = batchName ?? submissions[0]?.batch_name ?? "Batch"
  const resolvedTermLabel = termLabel ?? (submissions[0] ? `${submissions[0].term_name} (${submissions[0].term_season} ${submissions[0].term_year})` : "")
  const totalCourses = new Set(submissions.map((s) => s.course_id)).size
  const totalSections = submissions.length

  return (
    <div className="space-y-6">
      <PageHeader
        title={`${resolvedBatchName} PO Dashboard`}
        description={termId ? `Batch-level PO attainment for ${resolvedTermLabel}.` : "Batch-level PO attainment across courses and semesters."}
        actions={
          <Button size="sm" variant="outline" nativeButton={false} render={<Link href="/result-submissions" />}>
            <ArrowLeft /> Result Submissions
          </Button>
        }
      />

      <div className="grid gap-4 sm:grid-cols-3">
        <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">Courses</p><p className="text-2xl font-semibold">{totalCourses}</p></CardContent></Card>
        <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">Sections</p><p className="text-2xl font-semibold">{totalSections}</p></CardContent></Card>
        <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">Scope</p><p className="text-sm font-medium">{termId ? resolvedTermLabel : "All visible semesters"}</p></CardContent></Card>
      </div>

      {isLoading && <div className="h-40 animate-pulse rounded-lg bg-muted" />}

      {!isLoading && dashboard && (
        <>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-sm"><GraduationCap className="h-4 w-4" />Overall PO Attainment</CardTitle>
            </CardHeader>
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
