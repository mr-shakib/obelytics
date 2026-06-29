"use client"

import { useState } from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { useQuery } from "@tanstack/react-query"
import { toast } from "sonner"
import {
  ArrowLeft,
  LayoutDashboard,
  CalendarDays,
  ClipboardList,
  Target,
  BookOpen,
  Download,
  Loader2,
  Users,
  CheckCircle2,
  Circle,
  type LucideIcon,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog"
import { StatusBadge } from "@/components/shared/status-badge"
import { PageHeader } from "@/components/shared/page-header"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"
import { useResolveCourseLocation } from "@/hooks/use-course-location"
import { COURSE_TYPE_LABELS, type Course, type CourseCategory, type CourseAssessmentTool, type ModuleLeaderAssignment } from "./course-types"

const SECTIONS: { slug: string; label: string; icon: LucideIcon }[] = [
  { slug: "overview", label: "Overview", icon: LayoutDashboard },
  { slug: "mappings", label: "Outcomes & Mappings", icon: Target },
  { slug: "delivery-plan", label: "Delivery Plan", icon: CalendarDays },
  { slug: "assessment", label: "Assessment", icon: ClipboardList },
  { slug: "materials", label: "Learning Materials", icon: BookOpen },
  { slug: "sections", label: "Sections", icon: Users },
]
const REQUIRED_DELIVERY_PLAN_WEEKS = 14

interface Props {
  id: string
  children: React.ReactNode
}

export function CourseWorkspaceShell({ id, children }: Props) {
  const pathname = usePathname()
  const courseLocation = useResolveCourseLocation(id)
  const [showOutlineDialog, setShowOutlineDialog] = useState(false)
  const [excludedToolIds, setExcludedToolIds] = useState<Set<string>>(new Set())
  const [isDownloading, setIsDownloading] = useState(false)

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.courses.detail(id),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/courses/${id}` as never)
      return (data as unknown) as Course
    },
  })

  const { data: courseCategories = [] } = useQuery({
    queryKey: queryKeys.courseCategories.all,
    queryFn: async () => {
      const { data } = await apiClient.GET("/ref-data/course-categories" as never)
      return ((data as unknown) as CourseCategory[]) ?? []
    },
  })

  const { data: myAssignments = [] } = useQuery({
    queryKey: queryKeys.moduleLeaderAssignments.mine,
    queryFn: async () => {
      const { data } = await apiClient.GET("/module-leader-assignments/mine" as never)
      return ((data as unknown) as ModuleLeaderAssignment[]) ?? []
    },
  })

  const curriculumId = courseLocation?.curriculumId

  const { data: courseOutcomes = [] } = useQuery({
    queryKey: queryKeys.courseOutcomes.list(curriculumId, id),
    queryFn: async () => {
      const { data } = await apiClient.GET(
        `/course-outcomes?curriculum_id=${curriculumId}&course_id=${id}` as never
      )
      return ((data as unknown) as { id: string }[]) ?? []
    },
    enabled: !!curriculumId,
  })

  const { data: objectives = [] } = useQuery({
    queryKey: queryKeys.courseObjectives.byCourse(id),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/courses/${id}/objectives` as never)
      return ((data as unknown) as { statement: string }[]) ?? []
    },
  })

  const { data: lessonPlan = [] } = useQuery({
    queryKey: queryKeys.courseLessonPlan.byCourse(id, curriculumId ?? ""),
    queryFn: async () => {
      const { data } = await apiClient.GET(
        `/courses/${id}/lesson-plan?curriculum_id=${curriculumId}` as never
      )
      return ((data as unknown) as { id: string; week_number: number }[]) ?? []
    },
    enabled: !!curriculumId,
  })

  const { data: mappingSet } = useQuery({
    queryKey: queryKeys.coPoMappings.byCourse(curriculumId ?? "", id),
    queryFn: async () => {
      try {
        const { data } = await apiClient.GET(
          `/mappings/co-po?curriculum_id=${curriculumId}&course_id=${id}` as never
        ) as { data: unknown }
        return ((data as unknown) as { id: string } | null) ?? null
      } catch {
        return null
      }
    },
    enabled: !!curriculumId,
    retry: false,
  })

  const { data: assessmentTools = [] } = useQuery({
    queryKey: queryKeys.courseAssessmentTools.byCourse(id, curriculumId ?? ""),
    queryFn: async () => {
      const { data } = await apiClient.GET(
        `/courses/${id}/assessment-tools?curriculum_id=${curriculumId}` as never
      )
      return ((data as unknown) as CourseAssessmentTool[]) ?? []
    },
    enabled: !!curriculumId,
  })

  // ── Completion tracking ─────────────────────────────────────────────────
  const assessmentToolsForCheck = assessmentTools.length > 0 ? assessmentTools : []
  const checks: { label: string; done: boolean }[] = []
  checks.push({ label: "Course description", done: !!data?.description })
  checks.push({ label: "Course objectives", done: objectives.length > 0 })
  checks.push({ label: "Course outcomes (COs)", done: courseOutcomes.length > 0 })
  checks.push({ label: "Assessment tools", done: assessmentToolsForCheck.length > 0 })
  checks.push({ label: "CO-PO mapping", done: !!mappingSet })
  const deliveryPlanWeeks = Array.from(new Set(lessonPlan.map((item) => item.week_number))).sort(
    (a, b) => a - b
  )
  const hasCompleteDeliveryPlan =
    deliveryPlanWeeks.length === REQUIRED_DELIVERY_PLAN_WEEKS &&
    deliveryPlanWeeks[0] === 1 &&
    deliveryPlanWeeks.at(-1) === REQUIRED_DELIVERY_PLAN_WEEKS
  checks.push({ label: "Delivery plan", done: hasCompleteDeliveryPlan })

  const completedCount = checks.filter((c) => c.done).length
  const completionPct = Math.round((completedCount / checks.length) * 100)
  const isComplete = completionPct === 100

  if (isLoading) return <div className="animate-pulse h-40 bg-muted rounded-md" />
  if (!data) return <p className="text-muted-foreground">Course not found.</p>

  const courseCategoryById = Object.fromEntries(courseCategories.map((t) => [t.id, t]))
  const categoryName = courseCategoryById[data.course_category_id]?.name ?? "—"
  const courseTypeLabel = COURSE_TYPE_LABELS[data.course_type] ?? data.course_type
  const isMyModule = myAssignments.some((a) => a.course_id === id)

  function openOutlineDialog() {
    setExcludedToolIds(new Set())
    setShowOutlineDialog(true)
  }

  function toggleTool(toolId: string, included: boolean) {
    setExcludedToolIds((prev) => {
      const next = new Set(prev)
      if (included) next.delete(toolId)
      else next.add(toolId)
      return next
    })
  }

  async function handleDownloadOutline() {
    if (!curriculumId || !data) return
    setIsDownloading(true)
    try {
      const excludedParam = [...excludedToolIds]
        .map((toolId) => `excluded_tool_ids=${toolId}`)
        .join("&")
      const url = `/courses/${id}/outline-pdf?curriculum_id=${curriculumId}${excludedParam ? `&${excludedParam}` : ""}`
      const { data: blob, error } = await apiClient.GET(url as never, { parseAs: "blob" } as never)
      if (error || !blob) {
        toast.error("Failed to generate course outline")
        return
      }
      const objectUrl = URL.createObjectURL(blob as Blob)
      const a = document.createElement("a")
      a.href = objectUrl
      a.download = `${data.code}_course_outline.pdf`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(objectUrl)
      setShowOutlineDialog(false)
    } catch {
      toast.error("Failed to generate course outline")
    } finally {
      setIsDownloading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <Link
          href="/courses"
          className="mb-2 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Courses
        </Link>
        <PageHeader
          title={`${data.code} — ${data.title}`}
          description={`${data.credits} credits · ${categoryName} · ${courseTypeLabel} · ${data.theory_hours} theory hrs · ${data.lab_hours} lab hrs`}
           actions={
            <div className="flex items-center gap-3">
              <StatusBadge status={data.status} />
              <Button
                variant="outline"
                size="sm"
                onClick={openOutlineDialog}
                disabled={!curriculumId || !isComplete}
                title={!curriculumId ? "Course is not part of any curriculum yet" : !isComplete ? `Course is ${completionPct}% complete — fill all required fields first` : undefined}
              >
                <Download />
                Download Course Outline
              </Button>
              <Button variant="outline" size="sm" nativeButton={false} render={<Link href={`/course-outcomes?course_id=${id}`} />}>
                View COs
              </Button>
            </div>
          }
        />
      </div>

      {curriculumId && (
        <Card className={cn(isComplete ? "border-green-200 bg-green-50/50 dark:border-green-900/40 dark:bg-green-950/10" : "border-amber-200 bg-amber-50/50 dark:border-amber-900/40 dark:bg-amber-950/10")}>
          <CardContent className="py-3">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm font-medium">
                Course Customization {isComplete ? "Complete" : `${completionPct}%`}
              </p>
              <span className="text-xs text-muted-foreground">{completedCount}/{checks.length} done</span>
            </div>
            <div className="h-2 w-full rounded-full bg-muted overflow-hidden mb-3">
              <div
                className={cn("h-full rounded-full transition-all", isComplete ? "bg-green-500" : "bg-amber-500")}
                style={{ width: `${completionPct}%` }}
              />
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-1.5">
              {checks.map((c) => (
                <div key={c.label} className="flex items-center gap-1.5 text-xs">
                  {c.done
                    ? <CheckCircle2 className="h-3.5 w-3.5 text-green-600 shrink-0" />
                    : <Circle className="h-3.5 w-3.5 text-muted-foreground/40 shrink-0" />
                  }
                  <span className={cn(c.done ? "text-muted-foreground" : "text-amber-700 dark:text-amber-400 font-medium")}>
                    {c.label}
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {isMyModule && (
        <Card className="border-primary/30 bg-primary/5">
          <CardContent className="flex flex-wrap items-center justify-between gap-4 py-4">
            <div>
              <p className="text-sm font-medium">You are the Module Leader for this course</p>
              <p className="text-sm text-muted-foreground">
                Design this course by managing its Course Outcomes and CO-PO mapping.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Button size="sm" nativeButton={false} render={<Link href={`/course-outcomes?course_id=${id}`} />}>
                Manage Course Outcomes
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      <Dialog open={showOutlineDialog} onOpenChange={setShowOutlineDialog}>
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle>Download Course Outline</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">
              Choose which assessment tools to include in the PDF. Excluded tools will not appear
              and the total marks will reflect only the included ones.
            </p>
            {assessmentTools.length === 0 ? (
              <p className="text-sm text-muted-foreground">No assessment tools configured.</p>
            ) : (
              <div className="space-y-2">
                {assessmentTools.map((tool) => {
                  const included = !excludedToolIds.has(tool.id)
                  return (
                    <label key={tool.id} className="flex cursor-pointer items-center gap-3">
                      <input
                        type="checkbox"
                        checked={included}
                        onChange={(e) => toggleTool(tool.id, e.target.checked)}
                        className="h-4 w-4 rounded border-border"
                      />
                      <span className="text-sm">{tool.assessment_type_name}</span>
                    </label>
                  )
                })}
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowOutlineDialog(false)}>
              Cancel
            </Button>
            <Button onClick={handleDownloadOutline} disabled={isDownloading}>
              {isDownloading && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
              <Download className="h-3.5 w-3.5" />
              Download PDF
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <div className="flex flex-col gap-6 lg:flex-row">
        <nav className="shrink-0 lg:w-56">
          <div className="flex gap-1 overflow-x-auto lg:flex-col lg:overflow-visible">
            {SECTIONS.map((section) => {
              const href = `/courses/${id}/${section.slug}`
              const active = pathname === href || pathname.startsWith(`${href}/`)
              const Icon = section.icon
              return (
                <Link
                  key={section.slug}
                  href={href}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "flex items-center gap-2.5 whitespace-nowrap rounded-lg px-3 py-2 text-sm transition-colors",
                    active
                      ? "bg-accent font-semibold text-foreground"
                      : "text-muted-foreground hover:bg-accent/50 hover:text-foreground"
                  )}
                >
                  <Icon className="h-4 w-4 shrink-0" />
                  {section.label}
                </Link>
              )
            })}
          </div>
        </nav>

        <div className="min-w-0 flex-1 space-y-6">{children}</div>
      </div>
    </div>
  )
}
