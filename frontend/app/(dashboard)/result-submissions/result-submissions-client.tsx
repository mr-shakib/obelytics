"use client"

import Link from "next/link"
import { useMemo, useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { BarChart3, BookOpen, ChevronRight, GraduationCap } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { PageHeader } from "@/components/shared/page-header"
import { ResultStatusBadge } from "@/components/shared/result-status-badge"
import { useHasAnyPermission } from "@/hooks/use-permission"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"
import { useAuthStore } from "@/lib/stores/auth-store"
import { colorForId } from "@/lib/result-colors"

// Courses/sections a section teacher hasn't finished with yet (not even
// submitted to their Module Leader) aren't a Program Coordinator's concern —
// their queue should only ever show what's actually been handed up to them.
const PC_VISIBLE_STATUSES = new Set(["ML_APPROVED", "PC_APPROVED", "PUBLISHED"])

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
  section_id: string
  section_name: string
  result_publication_id: string | null
  status: string
  submitted_at: string | null
  ml_rejection_comment: string | null
  student_count: number
}

const STATUS_OPTIONS: Record<string, string> = {
  ALL: "All statuses",
  DRAFT: "Not submitted",
  SUBMITTED: "Submitted",
  ML_APPROVED: "Approved (Module Leader)",
  PC_APPROVED: "Approved (Program Coordinator)",
  PUBLISHED: "Published",
}

// Determines the status label shown on a course card: the most "actionable"
// status present among its sections wins, so courses awaiting review stand
// out first.
const STATUS_PRIORITY = ["SUBMITTED", "ML_APPROVED", "PC_APPROVED", "DRAFT", "PUBLISHED"]

const SEASON_ORDER: Record<string, number> = { SPRING: 0, SUMMER: 1, FALL: 2 }

function courseAccentStatus(items: ResultSubmission[]): string {
  for (const status of STATUS_PRIORITY) {
    if (items.some((i) => i.status === status)) return status
  }
  return "DRAFT"
}

// Which semester each of a course's sections belongs to — a course can be
// offered to more than one batch/term at once, so this can't be flattened
// into a single count.
function groupByBatchTerm(items: ResultSubmission[]) {
  const map = new Map<
    string,
    { label: string; batch_id: string; batch_name: string; academic_term_id: string; items: ResultSubmission[] }
  >()
  for (const item of items) {
    const key = `${item.batch_id}__${item.academic_term_id}`
    const label = item.term_name
    const group = map.get(key)
    if (group) {
      group.items.push(item)
    } else {
      map.set(key, { label, batch_id: item.batch_id, batch_name: item.batch_name, academic_term_id: item.academic_term_id, items: [item] })
    }
  }
  return Array.from(map.values())
}

export function ResultSubmissionsClient() {
  const [status, setStatus] = useState("ALL")
  const [batchFilter, setBatchFilter] = useState("ALL")
  const isSuperAdmin = useAuthStore((s) => s.manifest?.scope.is_global ?? false)
  const hasPcPermission = useHasAnyPermission(["result.approve.pc"])
  // The Program Coordinator role is granted every permission (including the
  // Module Leader's), so a raw permission check can't tell "genuine ML"
  // apart from "PC who happens to also hold that permission." Anyone with
  // PC-level authority (short of a super admin doing full-org oversight)
  // gets the PC-scoped view: only courses the ML has actually submitted up,
  // and no ML-only actions.
  const isPcOnlyView = hasPcPermission && !isSuperAdmin

  const { data: submissions = [], isLoading } = useQuery({
    queryKey: queryKeys.results.submissions({ status }),
    queryFn: async () => {
      const { data } = await apiClient.GET("/results" as never, {
        params: { query: status === "ALL" ? {} : { status } },
      } as never)
      return ((data as unknown) as ResultSubmission[]) ?? []
    },
  })

  const batchOptions = useMemo(() => {
    const map = new Map<string, string>()
    for (const item of submissions) map.set(item.batch_id, item.batch_name)
    return Array.from(map.entries())
      .map(([id, name]) => ({ id, name }))
      .sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true, sensitivity: "base" }))
  }, [submissions])

  // Cards are grouped semester-first: each academic term gets its own colored
  // section, with the term's courses inside it. A course offered in two
  // semesters appears in both sections, each card showing only that
  // semester's sections.
  const termGroups = useMemo(() => {
    const filtered = batchFilter === "ALL" ? submissions : submissions.filter((i) => i.batch_id === batchFilter)

    type CourseGroup = { course_id: string; course_code: string; course_title: string; items: ResultSubmission[] }
    const terms = new Map<string, {
      academic_term_id: string
      term_name: string
      term_year: number
      term_season: string
      courses: Map<string, CourseGroup>
    }>()

    for (const item of filtered) {
      let term = terms.get(item.academic_term_id)
      if (!term) {
        term = {
          academic_term_id: item.academic_term_id,
          term_name: item.term_name,
          term_year: item.term_year,
          term_season: item.term_season,
          courses: new Map(),
        }
        terms.set(item.academic_term_id, term)
      }
      const course = term.courses.get(item.course_id)
      if (course) {
        course.items.push(item)
      } else {
        term.courses.set(item.course_id, {
          course_id: item.course_id,
          course_code: item.course_code,
          course_title: item.course_title,
          items: [item],
        })
      }
    }

    return Array.from(terms.values())
      .map((term) => {
        let courses = Array.from(term.courses.values())
        if (isPcOnlyView) {
          courses = courses.filter((g) => g.items.some((i) => PC_VISIBLE_STATUSES.has(i.status)))
        }
        return {
          ...term,
          courses: courses.map((g) => ({ ...g, batchTermGroups: groupByBatchTerm(g.items) })),
        }
      })
      .filter((term) => term.courses.length > 0)
      .sort(
        (a, b) =>
          b.term_year - a.term_year ||
          (SEASON_ORDER[b.term_season] ?? 0) - (SEASON_ORDER[a.term_season] ?? 0)
      )
  }, [submissions, isPcOnlyView, batchFilter])

  const pendingReviewCount = submissions.filter((s) =>
    isPcOnlyView ? s.status === "ML_APPROVED" : s.status === "SUBMITTED"
  ).length

  return (
    <div className="space-y-6">
      <PageHeader
        title="Result Submissions"
        description="Section result reports submitted by section teachers, grouped by semester."
      />

      <div className="flex flex-wrap items-center gap-3">
        <Select value={status} onValueChange={(v) => v != null && setStatus(v as string)}>
          <SelectTrigger className="w-64">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {Object.entries(STATUS_OPTIONS).map(([value, label]) => (
              <SelectItem key={value} value={value}>{label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={batchFilter} onValueChange={(v) => v != null && setBatchFilter(v as string)}>
          <SelectTrigger className="w-56">
            <SelectValue placeholder="All batches">
              {batchFilter === "ALL" ? "All batches" : batchOptions.find((b) => b.id === batchFilter)?.name}
            </SelectValue>
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="ALL">All batches</SelectItem>
            {batchOptions.map((b) => (
              <SelectItem key={b.id} value={b.id}>{b.name}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        {pendingReviewCount > 0 && (
          <Badge variant="secondary" className="bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-100">
            {pendingReviewCount} awaiting your review
          </Badge>
        )}
      </div>

      {isLoading && (
        <div className="grid gap-4 sm:grid-cols-2">
          {[...Array(4)].map((_, i) => <div key={i} className="h-24 bg-muted animate-pulse rounded-lg" />)}
        </div>
      )}

      {!isLoading && termGroups.length === 0 && (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            No section result submissions found.
          </CardContent>
        </Card>
      )}

      {termGroups.map((term) => {
        const termColor = colorForId(term.academic_term_id)
        const termTotal = term.courses.reduce((n, c) => n + c.items.length, 0)
        return (
          <section
            key={term.academic_term_id}
            className="rounded-xl border-2 p-4"
            style={{ borderColor: termColor, backgroundColor: `${termColor}08` }}
          >
            <div className="mb-4 flex flex-wrap items-center gap-2.5">
              <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ backgroundColor: termColor }} />
              <h2 className="text-sm font-semibold">
                {term.term_name}
              </h2>
              <span className="text-xs text-muted-foreground">
                {term.term_season} {term.term_year}
              </span>
              <span className="ml-auto text-xs text-muted-foreground">
                {term.courses.length} course{term.courses.length === 1 ? "" : "s"} · {termTotal} section{termTotal === 1 ? "" : "s"}
              </span>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
        {term.courses.map((course) => {
          const accent = courseAccentStatus(course.items)
          const total = course.items.length
          const submittedCount = course.items.filter((i) => i.status !== "DRAFT").length
          const notSubmittedCount = total - submittedCount
          const reviewCount = course.items.filter((i) => i.status === "SUBMITTED").length
          const firstItem = course.items[0]

          return (
            <Card
              key={course.course_id}
              className="h-full border-l-4 bg-card"
              style={{ borderLeftColor: colorForId(firstItem.batch_id) }}
            >
              <Link href={`/result-submissions/${course.course_id}?code=${encodeURIComponent(course.course_code)}&title=${encodeURIComponent(course.course_title)}`}>
                <CardHeader className="pb-2 transition-colors hover:bg-muted/40 rounded-t-xl">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-2">
                      <BookOpen className="h-4 w-4 text-muted-foreground shrink-0" />
                      <div>
                        <p className="font-mono text-sm font-semibold">{course.course_code}</p>
                        <p className="text-sm font-medium">{course.course_title}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <ResultStatusBadge status={accent} />
                      <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0" />
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="pt-0 pb-3 transition-colors hover:bg-muted/40">
                  <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                    <Badge variant="outline" className="text-xs font-normal">
                      {total} section{total === 1 ? "" : "s"}
                    </Badge>
                    <Badge variant="outline" className="text-xs font-normal">
                      {submittedCount} submitted
                    </Badge>
                    <Badge variant="outline" className="text-xs font-normal">
                      {notSubmittedCount} not submitted
                    </Badge>
                    {reviewCount > 0 && (
                      <Badge variant="outline" className="text-xs font-normal">
                        {reviewCount} awaiting review
                      </Badge>
                    )}
                  </div>

                  {/* Which batch/semester each of this course's sections belongs to —
                      a course can run across more than one at once. The colored dot
                      is a stable per-batch color, matching that batch wherever else
                      it shows up. */}
                  <div className="mt-2.5 space-y-1.5 border-t pt-2.5">
                    {course.batchTermGroups.map((g) => {
                      const gSubmitted = g.items.filter((i) => i.status !== "DRAFT").length
                      return (
                        <div key={`${g.batch_id}__${g.academic_term_id}`} className="flex items-center gap-2 text-xs">
                          <span
                            className="h-2 w-2 shrink-0 rounded-full"
                            style={{ backgroundColor: colorForId(g.batch_id) }}
                          />
                          <span className="font-medium text-foreground">{g.batch_name}</span>
                          <span className="text-muted-foreground">· {g.label}</span>
                          <span className="ml-auto shrink-0 text-muted-foreground">
                            {gSubmitted}/{g.items.length} submitted
                          </span>
                        </div>
                      )
                    })}
                  </div>
                </CardContent>
              </Link>
              <CardContent className="flex flex-wrap gap-2 pt-0">
                <Button
                  size="sm"
                  variant="outline"
                  nativeButton={false}
                  render={
                    <Link
                      href={`/result-submissions/${course.course_id}/dashboard?code=${encodeURIComponent(course.course_code)}&title=${encodeURIComponent(course.course_title)}`}
                    />
                  }
                >
                  <BarChart3 /> Course Dashboard
                </Button>
                {firstItem && (
                  <Button
                    size="sm"
                    variant="outline"
                    nativeButton={false}
                    render={
                      <Link
                        href={`/result-submissions/batches/${firstItem.batch_id}/dashboard?batch=${encodeURIComponent(firstItem.batch_name)}`}
                      />
                    }
                  >
                    <GraduationCap /> Batch PO Dashboard
                  </Button>
                )}
              </CardContent>
            </Card>
          )
        })}
            </div>
          </section>
        )
      })}
    </div>
  )
}
