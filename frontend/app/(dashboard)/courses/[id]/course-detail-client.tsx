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

type Course = {
  id: string
  code: string
  title: string
  credits: number
  course_type_id: string
  theory_hours: number
  lab_hours: number
  description: string | null
  status: string
}

type CourseType = { id: string; name: string }

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

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.courses.detail(id),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/courses/${id}` as never)
      return (data as unknown) as Course
    },
  })

  const { data: courseTypes = [] } = useQuery({
    queryKey: queryKeys.courseTypes.all,
    queryFn: async () => {
      const { data } = await apiClient.GET("/config/course-types" as never)
      return ((data as unknown) as CourseType[]) ?? []
    },
  })

  const courseTypeById = Object.fromEntries(courseTypes.map((t) => [t.id, t]))

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

  const typeName = courseTypeById[data.course_type_id]?.name ?? "—"

  return (
    <div className="max-w-3xl space-y-6">
      <PageHeader
        title={`${data.code} — ${data.title}`}
        description={`${data.credits} credits · ${typeName} · ${data.theory_hours} theory hrs · ${data.lab_hours} lab hrs`}
        actions={
          <div className="flex items-center gap-3">
            <StatusBadge status={data.status} />
            <Button variant="outline" size="sm" render={<Link href={`/course-outcomes?course_id=${id}`} />}>
              View COs
            </Button>
          </div>
        }
      />

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
                  <Input id="theory_hours" type="number" min={0} {...register("theory_hours", { valueAsNumber: true })} />
                  {errors.theory_hours && <p className="text-sm text-destructive">{errors.theory_hours.message}</p>}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="lab_hours">Lab Hours</Label>
                  <Input id="lab_hours" type="number" min={0} {...register("lab_hours", { valueAsNumber: true })} />
                  {errors.lab_hours && <p className="text-sm text-destructive">{errors.lab_hours.message}</p>}
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <Textarea id="description" rows={3} {...register("description")} />
                {errors.description && <p className="text-sm text-destructive">{errors.description.message}</p>}
              </div>
              <p className="text-xs text-muted-foreground">
                Code and course type are fixed after creation. Archive and recreate the course to change them.
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
  )
}
