"use client"

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { toast } from "sonner"
import { Loader2 } from "lucide-react"
import Link from "next/link"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { StatusBadge } from "@/components/shared/status-badge"
import { PageHeader } from "@/components/shared/page-header"
import { PermissionGate } from "@/components/shared/permission-gate"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"
import { usePermission } from "@/hooks/use-permission"

type ModuleLeaderAssignment = { course_id: string }

type Course = {
  id: string
  code: string
  title: string
  credits: number
  course_category_id: string
  course_type: string
  theory_hours: number
  lab_hours: number
  description: string | null
  status: string
}

type CourseCategory = { id: string; name: string }

type BloomDomain = { id: string; name: string }

const COURSE_TYPE_LABELS: Record<string, string> = {
  THEORY: "Theory",
  LAB: "Lab",
  THEORY_LAB: "Theory + Lab",
  THESIS_DEFENSE: "Final Year Thesis Defense",
}

const schema = z.object({
  title: z.string().min(1, "Title is required").max(255),
  credits: z.number().int().min(0, "Credits cannot be negative").max(20),
  theory_hours: z.number().int().min(0),
  lab_hours: z.number().int().min(0),
  description: z.string().max(2000).optional(),
})
type FormValues = z.infer<typeof schema>

interface Props {
  id: string
}

export function CourseDetailClient({ id }: Props) {
  const qc = useQueryClient()
  const canEditCourse = usePermission("course.update")

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

  const { data: bloomDomains = [] } = useQuery({
    queryKey: queryKeys.refData.bloomDomains,
    queryFn: async () => {
      const { data } = await apiClient.GET("/ref-data/bloom-domains" as never)
      return ((data as unknown) as BloomDomain[]) ?? []
    },
  })

  const { data: courseBloomDomainIds = [] } = useQuery({
    queryKey: queryKeys.courseBloomDomains.byCourse(id),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/courses/${id}/bloom-domains` as never)
      return ((data as unknown) as string[]) ?? []
    },
  })

  const bloomDomainsMutation = useMutation({
    mutationFn: async (bloomDomainIds: string[]) => {
      await apiClient.PUT(`/courses/${id}/bloom-domains` as never, {
        body: { bloom_domain_ids: bloomDomainIds },
      } as never)
    },
    onSuccess: (_data, bloomDomainIds) => {
      qc.setQueryData(queryKeys.courseBloomDomains.byCourse(id), bloomDomainIds)
    },
    onError: () => toast.error("Failed to update Bloom domains"),
  })

  const toggleBloomDomain = (domainId: string, checked: boolean) => {
    const next = checked
      ? [...courseBloomDomainIds, domainId]
      : courseBloomDomainIds.filter((d) => d !== domainId)
    bloomDomainsMutation.mutate(next)
  }

  const isMyModule = myAssignments.some((a) => a.course_id === id)

  const courseCategoryById = Object.fromEntries(courseCategories.map((t) => [t.id, t]))

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting, isDirty },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    values: data
      ? {
          title: data.title,
          credits: data.credits,
          theory_hours: data.theory_hours,
          lab_hours: data.lab_hours,
          description: data.description ?? "",
        }
      : undefined,
  })

  const mutation = useMutation({
    mutationFn: async (values: FormValues) => {
      await apiClient.PATCH(`/courses/${id}` as never, {
        body: {
          title: values.title,
          credits: values.credits,
          theory_hours: values.theory_hours,
          lab_hours: values.lab_hours,
          description: values.description || undefined,
        },
      } as never)
    },
    onSuccess: () => {
      toast.success("Course updated")
      qc.invalidateQueries({ queryKey: queryKeys.courses.detail(id) })
      qc.invalidateQueries({ queryKey: queryKeys.courses.all })
    },
    onError: () => toast.error("Failed to update course"),
  })

  if (isLoading) return <div className="animate-pulse h-40 bg-muted rounded-md" />
  if (!data) return <p className="text-muted-foreground">Course not found.</p>

  const categoryName = courseCategoryById[data.course_category_id]?.name ?? "—"
  const courseTypeLabel = COURSE_TYPE_LABELS[data.course_type] ?? data.course_type

  return (
    <div className="space-y-6">
      <PageHeader
        title={`${data.code} — ${data.title}`}
        description={`${data.credits} credits · ${categoryName} · ${courseTypeLabel} · ${data.theory_hours} theory hrs · ${data.lab_hours} lab hrs`}
        actions={
          <div className="flex items-center gap-3">
            <StatusBadge status={data.status} />
            <Button variant="outline" size="sm" nativeButton={false} render={<Link href={`/course-outcomes?course_id=${id}`} />}>
              View COs
            </Button>
          </div>
        }
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6 max-w-3xl">
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
                  <Button variant="outline" size="sm" nativeButton={false} render={<Link href={`/mappings/co-po?course_id=${id}`} />}>
                    Manage CO-PO Mapping
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          {data.description && (
            <Card>
              <CardHeader><CardTitle>Description</CardTitle></CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground whitespace-pre-wrap">{data.description}</p>
              </CardContent>
            </Card>
          )}

          <PermissionGate permission="course.update">
            <Card>
              <CardHeader><CardTitle>Edit Details</CardTitle></CardHeader>
              <CardContent>
                <form onSubmit={handleSubmit((v) => mutation.mutate(v))} className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="title">Title</Label>
                    <Input id="title" {...register("title")} />
                    {errors.title && <p className="text-sm text-destructive">{errors.title.message}</p>}
                  </div>
                  <div className="grid grid-cols-3 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="credits">Credits</Label>
                      <Input id="credits" type="number" min={0} max={20} {...register("credits", { valueAsNumber: true })} />
                      {errors.credits && <p className="text-sm text-destructive">{errors.credits.message}</p>}
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="theory_hours">Theory Hours</Label>
                      <Input id="theory_hours" type="number" min={0} disabled={data.course_type === "LAB"} {...register("theory_hours", { valueAsNumber: true })} />
                      {errors.theory_hours && <p className="text-sm text-destructive">{errors.theory_hours.message}</p>}
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="lab_hours">Lab Hours</Label>
                      <Input id="lab_hours" type="number" min={0} disabled={data.course_type === "THEORY"} {...register("lab_hours", { valueAsNumber: true })} />
                      {errors.lab_hours && <p className="text-sm text-destructive">{errors.lab_hours.message}</p>}
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="description">Description</Label>
                    <Textarea id="description" rows={3} {...register("description")} />
                    {errors.description && <p className="text-sm text-destructive">{errors.description.message}</p>}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Code, course category, and course type are fixed after creation. Archive and recreate the course to change them.
                  </p>
                  <Button type="submit" disabled={!isDirty || isSubmitting || mutation.isPending}>
                    {(isSubmitting || mutation.isPending) && <Loader2 className="animate-spin" />}
                    Save Changes
                  </Button>
                </form>
              </CardContent>
            </Card>
          </PermissionGate>
        </div>

        <aside className="space-y-6">
          <Card>
            <CardHeader><CardTitle>Bloom&apos;s Taxonomy Domains</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              <p className="text-sm text-muted-foreground">
                Select the domains this course&apos;s outcomes should cover.
              </p>
              {bloomDomains.length === 0 ? (
                <p className="text-sm text-muted-foreground">No Bloom domains configured.</p>
              ) : (
                <div className="space-y-2">
                  {bloomDomains.map((domain) => (
                    <div key={domain.id} className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        id={`bloom-domain-${domain.id}`}
                        checked={courseBloomDomainIds.includes(domain.id)}
                        disabled={!canEditCourse || bloomDomainsMutation.isPending}
                        onChange={(e) => toggleBloomDomain(domain.id, e.target.checked)}
                        className="h-4 w-4 rounded border-border disabled:opacity-50 disabled:cursor-not-allowed"
                      />
                      <Label htmlFor={`bloom-domain-${domain.id}`} className="font-normal">
                        {domain.name}
                      </Label>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </aside>
      </div>
    </div>
  )
}
