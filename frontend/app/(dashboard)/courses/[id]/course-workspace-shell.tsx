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
  { slug: "delivery-plan", label: "Delivery Plan", icon: CalendarDays },
  { slug: "assessment", label: "Assessment", icon: ClipboardList },
  { slug: "mappings", label: "Outcomes & Mappings", icon: Target },
  { slug: "materials", label: "Learning Materials", icon: BookOpen },
  { slug: "sections", label: "Sections", icon: Users },
]

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

  const { data: assessmentTools = [] } = useQuery({
    queryKey: queryKeys.courseAssessmentTools.byCourse(id, curriculumId ?? ""),
    queryFn: async () => {
      const { data } = await apiClient.GET(
        `/courses/${id}/assessment-tools?curriculum_id=${curriculumId}` as never
      )
      return ((data as unknown) as CourseAssessmentTool[]) ?? []
    },
    enabled: !!curriculumId && showOutlineDialog,
  })

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
                disabled={!curriculumId}
                title={!curriculumId ? "Course is not part of any curriculum yet" : undefined}
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
