"use client"

import { useEffect } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { useQuery } from "@tanstack/react-query"
import {
  ArrowRight,
  BookCopy,
  BookOpen,
  CheckSquare,
  ClipboardCheck,
  Layers3,
  Target,
} from "lucide-react"
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { useAuthStore } from "@/lib/stores/auth-store"
import { usePermissions } from "@/hooks/use-permission"
import { isSectionTeacherView } from "@/lib/navigation"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"
import { CATEGORICAL_COLORS, SEQUENTIAL_PRIMARY, STATUS_GOOD } from "@/lib/result-colors"

type Curriculum = { id: string; name: string; status: string }
type Course = { id: string; course_type: string; status: string }
type ResultSubmission = { section_offering_id: string; course_id: string; status: string }
type ApprovalCounts = {
  result_publications: number
  total: number
}

const COURSE_TYPE_LABELS: Record<string, string> = {
  THEORY: "Theory",
  LAB: "Laboratory",
  THESIS_DEFENSE: "Thesis / Defense",
}

const RESULT_STATUS_LABELS: Record<string, string> = {
  DRAFT: "Draft",
  SUBMITTED: "Submitted",
  ML_APPROVED: "ML approved",
  PC_APPROVED: "PC approved",
  PUBLISHED: "Published",
}

const RESULT_STATUS_COLORS: Record<string, string> = {
  DRAFT: "#94a3b8",
  SUBMITTED: "#93c5fd",
  ML_APPROVED: "#60a5fa",
  PC_APPROVED: "#2563eb",
  PUBLISHED: STATUS_GOOD,
}

function asList<T>(data: unknown): T[] {
  return ((data as { items?: T[] } | null)?.items ?? (data as T[]) ?? [])
}

function countBy<T>(items: T[], key: (item: T) => string) {
  const counts = new Map<string, number>()
  items.forEach((item) => counts.set(key(item), (counts.get(key(item)) ?? 0) + 1))
  return counts
}

function MetricCard({
  label,
  value,
  detail,
  icon: Icon,
  href,
  loading,
}: {
  label: string
  value: number
  detail: string
  icon: typeof BookOpen
  href: string
  loading: boolean
}) {
  return (
    <Link href={href} className="group">
      <Card className="h-full transition-colors hover:border-primary/40">
        <CardContent className="flex items-start justify-between gap-4 p-5">
          <div>
            <p className="text-sm text-muted-foreground">{label}</p>
            {loading ? (
              <div className="mt-2 h-9 w-16 animate-pulse rounded bg-muted" />
            ) : (
              <p className="mt-1 text-3xl font-semibold tracking-tight">{value}</p>
            )}
            <p className="mt-1 text-xs text-muted-foreground">{detail}</p>
          </div>
          <div className="rounded-xl bg-primary/10 p-2.5 text-primary transition-transform group-hover:scale-105">
            <Icon className="size-5" />
          </div>
        </CardContent>
      </Card>
    </Link>
  )
}

function EmptyChart({ message }: { message: string }) {
  return (
    <div className="flex h-[280px] items-center justify-center rounded-lg border border-dashed">
      <p className="max-w-64 text-center text-sm text-muted-foreground">{message}</p>
    </div>
  )
}

export default function OverviewPage() {
  const router = useRouter()
  const user = useAuthStore((state) => state.user)
  const isInitialized = useAuthStore((state) => state.isInitialized)
  const permissions = usePermissions()
  const canReadCurriculum = permissions.includes("curriculum.read")
  const canReadResults = ["result.approve.ml", "result.approve.pc", "result.publish"].some(
    (permission) => permissions.includes(permission)
  )
  const canReadApprovals = permissions.includes("approval.inbox.read")

  useEffect(() => {
    if (isInitialized && isSectionTeacherView(permissions)) router.replace("/my-sections")
  }, [isInitialized, permissions, router])

  const curriculaQuery = useQuery({
    queryKey: queryKeys.curricula.all,
    queryFn: async () => {
      const { data } = await apiClient.GET("/curricula" as never)
      return asList<Curriculum>(data)
    },
    enabled: canReadCurriculum,
  })

  const coursesQuery = useQuery({
    queryKey: queryKeys.courses.all,
    queryFn: async () => {
      const { data } = await apiClient.GET("/courses" as never)
      return asList<Course>(data)
    },
    enabled: canReadCurriculum,
  })

  const resultsQuery = useQuery({
    queryKey: queryKeys.results.submissions({ dashboard: true }),
    queryFn: async () => {
      const { data } = await apiClient.GET("/results" as never)
      return asList<ResultSubmission>(data)
    },
    enabled: canReadResults,
  })

  const approvalsQuery = useQuery({
    queryKey: [...queryKeys.approvals.inbox, "counts"],
    queryFn: async () => {
      const { data } = await apiClient.GET("/approval/inbox/counts" as never)
      return (data as unknown) as ApprovalCounts
    },
    enabled: canReadApprovals,
  })

  const curricula = curriculaQuery.data ?? []
  const courses = coursesQuery.data ?? []
  const results = resultsQuery.data ?? []
  const approvals = approvalsQuery.data
  const publishedResults = results.filter((result) => result.status === "PUBLISHED").length
  const activeCurricula = curricula.filter((item) =>
    ["ACTIVE", "PUBLISHED", "APPROVED"].includes(item.status)
  ).length

  const courseTypeCounts = countBy(courses, (course) => course.course_type || "OTHER")
  const courseTypeData = Array.from(courseTypeCounts, ([type, count]) => ({
    name: COURSE_TYPE_LABELS[type] ?? type.replaceAll("_", " "),
    count,
  }))

  const resultCounts = countBy(results, (result) => result.status)
  const resultStatusData = Object.keys(RESULT_STATUS_LABELS)
    .map((status) => ({
      status,
      name: RESULT_STATUS_LABELS[status],
      value: resultCounts.get(status) ?? 0,
    }))
    .filter((item) => item.value > 0)

  const approvalData = [
    { name: "Results", count: approvals?.result_publications ?? 0 },
  ]

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-primary">OBE workspace</p>
          <h1 className="mt-1 text-2xl font-bold tracking-tight">
            Welcome back{user?.first_name ? `, ${user.first_name}` : ""}
          </h1>
          <p className="mt-1 text-muted-foreground">
            A live view of curriculum delivery, results, and work requiring attention.
          </p>
        </div>
        {canReadApprovals && (
          <Button variant="outline" nativeButton={false} render={<Link href="/approvals" />}>
            Review approvals <ArrowRight />
          </Button>
        )}
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          label="Curricula"
          value={curricula.length}
          detail={`${activeCurricula} active or published`}
          icon={BookCopy}
          href="/curricula"
          loading={curriculaQuery.isLoading}
        />
        <MetricCard
          label="Courses"
          value={courses.length}
          detail={`${courseTypeData.length} delivery types`}
          icon={BookOpen}
          href="/courses"
          loading={coursesQuery.isLoading}
        />
        <MetricCard
          label="Result sections"
          value={results.length}
          detail={`${publishedResults} published`}
          icon={ClipboardCheck}
          href="/result-submissions"
          loading={resultsQuery.isLoading}
        />
        <MetricCard
          label="Pending approvals"
          value={approvals?.total ?? 0}
          detail="Items waiting for review"
          icon={CheckSquare}
          href="/approvals"
          loading={approvalsQuery.isLoading}
        />
      </div>

      <div className="grid gap-6 xl:grid-cols-5">
        <Card className="xl:col-span-3">
          <CardHeader className="flex-row items-center justify-between space-y-0">
            <div>
              <CardTitle>Result workflow</CardTitle>
              <p className="mt-1 text-sm text-muted-foreground">Sections at each publication stage</p>
            </div>
            <Layers3 className="size-5 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {resultsQuery.isLoading ? (
              <div className="h-[280px] animate-pulse rounded-lg bg-muted" />
            ) : resultStatusData.length === 0 ? (
              <EmptyChart message="Result submissions will appear here as sections enter the approval workflow." />
            ) : (
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={resultStatusData} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
                  <CartesianGrid vertical={false} strokeDasharray="3 3" />
                  <XAxis dataKey="name" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
                  <YAxis allowDecimals={false} tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
                  <Tooltip cursor={{ fill: "var(--muted)" }} formatter={(value) => [value, "Sections"]} />
                  <Bar dataKey="value" name="Sections" radius={[6, 6, 0, 0]}>
                    {resultStatusData.map((item) => (
                      <Cell key={item.status} fill={RESULT_STATUS_COLORS[item.status]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        <Card className="xl:col-span-2">
          <CardHeader>
            <CardTitle>Course portfolio</CardTitle>
            <p className="text-sm text-muted-foreground">Visible courses by delivery type</p>
          </CardHeader>
          <CardContent>
            {coursesQuery.isLoading ? (
              <div className="h-[280px] animate-pulse rounded-full bg-muted" />
            ) : courseTypeData.length === 0 ? (
              <EmptyChart message="Course types will be summarized after courses are added." />
            ) : (
              <div className="relative">
                <ResponsiveContainer width="100%" height={280}>
                  <PieChart>
                    <Pie
                      data={courseTypeData}
                      dataKey="count"
                      nameKey="name"
                      innerRadius={68}
                      outerRadius={105}
                      paddingAngle={3}
                    >
                      {courseTypeData.map((item, index) => (
                        <Cell key={item.name} fill={CATEGORICAL_COLORS[index]} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(value) => [value, "Courses"]} />
                  </PieChart>
                </ResponsiveContainer>
                <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
                  <span className="text-3xl font-semibold">{courses.length}</span>
                  <span className="text-xs text-muted-foreground">courses</span>
                </div>
                <div className="flex flex-wrap justify-center gap-x-4 gap-y-2">
                  {courseTypeData.map((item, index) => (
                    <div key={item.name} className="flex items-center gap-1.5 text-xs">
                      <span
                        className="size-2.5 rounded-full"
                        style={{ backgroundColor: CATEGORICAL_COLORS[index] }}
                      />
                      {item.name} ({item.count})
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader className="flex-row items-center justify-between space-y-0">
            <div>
              <CardTitle>Approval workload</CardTitle>
              <p className="mt-1 text-sm text-muted-foreground">Items currently waiting by type</p>
            </div>
            <CheckSquare className="size-5 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {approvalsQuery.isLoading ? (
              <div className="h-[220px] animate-pulse rounded-lg bg-muted" />
            ) : approvalData.every((item) => item.count === 0) ? (
              <EmptyChart message="You are all caught up—there are no pending approvals." />
            ) : (
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={approvalData} layout="vertical" margin={{ left: 16, right: 20 }}>
                  <CartesianGrid horizontal={false} strokeDasharray="3 3" />
                  <XAxis type="number" allowDecimals={false} axisLine={false} tickLine={false} />
                  <YAxis type="category" dataKey="name" width={112} tick={{ fontSize: 12 }} axisLine={false} tickLine={false} />
                  <Tooltip cursor={{ fill: "var(--muted)" }} formatter={(value) => [value, "Pending"]} />
                  <Bar dataKey="count" fill={SEQUENTIAL_PRIMARY} radius={[0, 6, 6, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Continue your work</CardTitle>
            <p className="text-sm text-muted-foreground">Common OBE management areas</p>
          </CardHeader>
          <CardContent className="grid gap-3 sm:grid-cols-2">
            {[
              { label: "Curriculum design", href: "/curricula", icon: BookCopy, detail: "Versions, terms and courses" },
              { label: "Course outcomes", href: "/course-outcomes", icon: Target, detail: "Define and review COs" },
              { label: "Result submissions", href: "/result-submissions", icon: ClipboardCheck, detail: "Review section results" },
              { label: "Approvals", href: "/approvals", icon: CheckSquare, detail: "Action pending work" },
            ].map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="group flex items-center gap-3 rounded-xl border p-4 transition-colors hover:border-primary/40 hover:bg-muted/40"
              >
                <div className="rounded-lg bg-muted p-2 text-primary"><item.icon className="size-4" /></div>
                <div className="min-w-0">
                  <p className="text-sm font-medium">{item.label}</p>
                  <p className="truncate text-xs text-muted-foreground">{item.detail}</p>
                </div>
                <ArrowRight className="ml-auto size-4 text-muted-foreground transition-transform group-hover:translate-x-0.5" />
              </Link>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
