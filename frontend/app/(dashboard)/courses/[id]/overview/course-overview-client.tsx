"use client"

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useForm, useFieldArray, Controller } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { toast } from "sonner"
import { Loader2, Plus, Trash2, ArrowUp, ArrowDown, X } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Combobox } from "@/components/ui/combobox"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { PermissionGate } from "@/components/shared/permission-gate"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"
import { usePermission } from "@/hooks/use-permission"
import type { Course, CourseObjective, BloomDomain, Prerequisite, CourseListItem, CourseCategory } from "../course-types"
import { COURSE_TYPE_LABELS } from "../course-types"

const schema = z.object({
  code: z.string().min(1, "Code is required").max(30),
  title: z.string().min(1, "Title is required").max(255),
  course_category_id: z.string().min(1, "Course category is required"),
  course_type: z.enum(["THEORY", "LAB", "THESIS_DEFENSE"]),
  credits: z.number().min(0, "Credits cannot be negative").max(20),
  theory_hours: z.number().min(0),
  lab_hours: z.number().min(0),
  description: z.string().max(2000).optional(),
  syllabus_content: z.string().max(5000).optional(),
})
type FormValues = z.infer<typeof schema>

const objectivesSchema = z.object({
  items: z.array(z.object({ statement: z.string().min(1, "Cannot be empty").max(500) })),
})
type ObjectivesFormValues = z.infer<typeof objectivesSchema>

interface Props {
  id: string
}

export function CourseOverviewClient({ id }: Props) {
  const qc = useQueryClient()
  const canEditCourse = usePermission("course.update")

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.courses.detail(id),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/courses/${id}` as never)
      return (data as unknown) as Course
    },
  })

  const { data: bloomDomains = [] } = useQuery({
    queryKey: queryKeys.refData.bloomDomains,
    queryFn: async () => {
      const { data } = await apiClient.GET("/ref-data/bloom-domains" as never)
      return ((data as unknown) as BloomDomain[]) ?? []
    },
  })

  const { data: courseCategories = [] } = useQuery({
    queryKey: queryKeys.courseCategories.all,
    queryFn: async () => {
      const { data } = await apiClient.GET("/ref-data/course-categories" as never)
      return ((data as unknown) as CourseCategory[]) ?? []
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

  const {
    register,
    handleSubmit,
    control,
    watch,
    setValue,
    formState: { errors, isSubmitting, isDirty },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    values: data
      ? {
          code: data.code,
          title: data.title,
          course_category_id: data.course_category_id,
          course_type: data.course_type as FormValues["course_type"],
          credits: data.credits,
          theory_hours: data.theory_hours,
          lab_hours: data.lab_hours,
          description: data.description ?? "",
          syllabus_content: data.syllabus_content ?? "",
        }
      : undefined,
  })

  const watchedCourseType = watch("course_type")

  const mutation = useMutation({
    mutationFn: async (values: FormValues) => {
      await apiClient.PATCH(`/courses/${id}` as never, {
        body: {
          code: values.code,
          title: values.title,
          course_category_id: values.course_category_id,
          course_type: values.course_type,
          credits: values.credits,
          theory_hours: values.theory_hours,
          lab_hours: values.lab_hours,
          description: values.description || undefined,
          syllabus_content: values.syllabus_content || undefined,
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

  // ── Course Objectives ──────────────────────────────────────────────────────

  const { data: objectives = [] } = useQuery({
    queryKey: queryKeys.courseObjectives.byCourse(id),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/courses/${id}/objectives` as never)
      return ((data as unknown) as CourseObjective[]) ?? []
    },
  })

  const objectivesForm = useForm<ObjectivesFormValues>({
    resolver: zodResolver(objectivesSchema),
    values: { items: objectives.map((o) => ({ statement: o.statement })) },
  })
  const objectivesFieldArray = useFieldArray({ control: objectivesForm.control, name: "items" })

  const objectivesMutation = useMutation({
    mutationFn: async (statements: string[]) => {
      const { data } = await apiClient.PUT(`/courses/${id}/objectives` as never, {
        body: { statements },
      } as never)
      return ((data as unknown) as CourseObjective[]) ?? []
    },
    onSuccess: (next) => {
      qc.setQueryData(queryKeys.courseObjectives.byCourse(id), next)
      toast.success("Objectives updated")
    },
    onError: () => toast.error("Failed to update objectives"),
  })

  const onSubmitObjectives = objectivesForm.handleSubmit((values) => {
    objectivesMutation.mutate(values.items.map((i) => i.statement.trim()))
  })

  // ── Prerequisites ─────────────────────────────────────────────────────────

  const { data: prerequisites = [] } = useQuery({
    queryKey: queryKeys.coursePrerequisites.byCourse(id),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/courses/${id}/prerequisites` as never)
      return ((data as unknown) as Prerequisite[]) ?? []
    },
  })

  const { data: allCourses = [] } = useQuery({
    queryKey: queryKeys.courses.all,
    queryFn: async () => {
      const { data } = await apiClient.GET("/courses" as never)
      return ((data as unknown) as CourseListItem[]) ?? []
    },
  })
  const courseById = Object.fromEntries(allCourses.map((c) => [c.id, c]))

  const addPrerequisiteMutation = useMutation({
    mutationFn: async (prerequisiteCourseId: string) => {
      const { data } = await apiClient.POST(`/courses/${id}/prerequisites` as never, {
        body: { prerequisite_course_id: prerequisiteCourseId },
      } as never)
      return (data as unknown) as Prerequisite
    },
    onSuccess: (created) => {
      qc.setQueryData(
        queryKeys.coursePrerequisites.byCourse(id),
        (prev: Prerequisite[] = []) => [...prev, created]
      )
    },
    onError: () => toast.error("Failed to add prerequisite — it may create a circular dependency"),
  })

  const removePrerequisiteMutation = useMutation({
    mutationFn: async (prereqId: string) => {
      await apiClient.DELETE(`/courses/${id}/prerequisites/${prereqId}` as never)
      return prereqId
    },
    onSuccess: (prereqId) => {
      qc.setQueryData(
        queryKeys.coursePrerequisites.byCourse(id),
        (prev: Prerequisite[] = []) => prev.filter((p) => p.id !== prereqId)
      )
    },
    onError: () => toast.error("Failed to remove prerequisite"),
  })

  const prerequisiteCourseIds = new Set(prerequisites.map((p) => p.prerequisite_course_id))
  const availablePrerequisiteOptions = allCourses
    .filter((c) => c.id !== id && !prerequisiteCourseIds.has(c.id))
    .map((c) => ({ value: c.id, label: `${c.code} — ${c.title}` }))

  if (isLoading) return <div className="animate-pulse h-40 bg-muted rounded-md" />
  if (!data) return <p className="text-muted-foreground">Course not found.</p>

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div className="lg:col-span-2 space-y-6 max-w-3xl">
        <PermissionGate permission="course.update">
          <Card>
            <CardHeader><CardTitle>Edit Details</CardTitle></CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit((v) => mutation.mutate(v))} className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="code">Code</Label>
                    <Input id="code" {...register("code")} />
                    {errors.code && <p className="text-sm text-destructive">{errors.code.message}</p>}
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="title">Title</Label>
                    <Input id="title" {...register("title")} />
                    {errors.title && <p className="text-sm text-destructive">{errors.title.message}</p>}
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Course Category</Label>
                    <Controller
                      name="course_category_id"
                      control={control}
                      render={({ field }) => (
                        <Select value={field.value ?? ""} onValueChange={field.onChange}>
                          <SelectTrigger className="w-full">
                            <SelectValue placeholder="Select category">
                              {(value: string) => courseCategories.find((c) => c.id === value)?.name ?? value}
                            </SelectValue>
                          </SelectTrigger>
                          <SelectContent>
                            {courseCategories.map((c) => (
                              <SelectItem key={c.id} value={c.id}>
                                {c.name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      )}
                    />
                    {errors.course_category_id && <p className="text-sm text-destructive">{errors.course_category_id.message}</p>}
                  </div>
                  <div className="space-y-2">
                    <Label>Course Type</Label>
                    <Controller
                      name="course_type"
                      control={control}
                      render={({ field }) => (
                        <Select
                          value={field.value ?? ""}
                          onValueChange={(v) => {
                            field.onChange(v)
                            if (v === "THEORY") setValue("lab_hours", 0, { shouldValidate: true, shouldDirty: true })
                            else if (v === "LAB") setValue("theory_hours", 0, { shouldValidate: true, shouldDirty: true })
                          }}
                        >
                          <SelectTrigger className="w-full">
                            <SelectValue placeholder="Select course type">
                              {(value: string) => COURSE_TYPE_LABELS[value] ?? value}
                            </SelectValue>
                          </SelectTrigger>
                          <SelectContent>
                            {Object.entries(COURSE_TYPE_LABELS).map(([value, label]) => (
                              <SelectItem key={value} value={value}>
                                {label}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      )}
                    />
                    {errors.course_type && <p className="text-sm text-destructive">{errors.course_type.message}</p>}
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="credits">Credits</Label>
                    <Input id="credits" type="number" min={0} max={20} step="0.25" {...register("credits", { valueAsNumber: true })} />
                    {errors.credits && <p className="text-sm text-destructive">{errors.credits.message}</p>}
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="theory_hours">Theory Hours</Label>
                    <Input id="theory_hours" type="number" min={0} step="0.25" disabled={watchedCourseType === "LAB"} {...register("theory_hours", { valueAsNumber: true })} />
                    {errors.theory_hours && <p className="text-sm text-destructive">{errors.theory_hours.message}</p>}
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="lab_hours">Lab Hours</Label>
                    <Input id="lab_hours" type="number" min={0} step="0.25" disabled={watchedCourseType === "THEORY"} {...register("lab_hours", { valueAsNumber: true })} />
                    {errors.lab_hours && <p className="text-sm text-destructive">{errors.lab_hours.message}</p>}
                  </div>
                </div>
                <Button type="submit" disabled={!isDirty || isSubmitting || mutation.isPending}>
                  {(isSubmitting || mutation.isPending) && <Loader2 className="animate-spin" />}
                  Save Changes
                </Button>
              </form>
            </CardContent>
          </Card>
        </PermissionGate>

        <Card>
          <CardHeader><CardTitle>Course Description / Rationale</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            {canEditCourse ? (
              <>
                <Textarea rows={3} placeholder="Describe the course rationale…" {...register("description")} />
                {errors.description && <p className="text-sm text-destructive">{errors.description.message}</p>}
                <Button
                  type="button"
                  size="sm"
                  onClick={handleSubmit((v) => mutation.mutate(v))}
                  disabled={!isDirty || isSubmitting || mutation.isPending}
                >
                  {(isSubmitting || mutation.isPending) && <Loader2 className="animate-spin" />}
                  Save
                </Button>
              </>
            ) : data.description ? (
              <p className="text-sm text-muted-foreground whitespace-pre-wrap">{data.description}</p>
            ) : (
              <p className="text-sm text-muted-foreground">No description added yet.</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Course Content (from Syllabus)</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            {canEditCourse ? (
              <>
                <Textarea rows={5} placeholder="Course content / syllabus topics…" {...register("syllabus_content")} />
                {errors.syllabus_content && <p className="text-sm text-destructive">{errors.syllabus_content.message}</p>}
                <Button
                  type="button"
                  size="sm"
                  onClick={handleSubmit((v) => mutation.mutate(v))}
                  disabled={!isDirty || isSubmitting || mutation.isPending}
                >
                  {(isSubmitting || mutation.isPending) && <Loader2 className="animate-spin" />}
                  Save
                </Button>
              </>
            ) : data.syllabus_content ? (
              <p className="text-sm text-muted-foreground whitespace-pre-wrap">{data.syllabus_content}</p>
            ) : (
              <p className="text-sm text-muted-foreground">No course content added yet.</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Course Objectives</CardTitle></CardHeader>
          <CardContent>
            {canEditCourse ? (
              <form onSubmit={onSubmitObjectives} className="space-y-3">
                {objectivesFieldArray.fields.length === 0 && (
                  <p className="text-sm text-muted-foreground">No objectives added yet.</p>
                )}
                {objectivesFieldArray.fields.map((field, index) => (
                  <div key={field.id} className="flex items-start gap-2">
                    <span className="mt-2 text-sm text-muted-foreground w-5 shrink-0">{index + 1}.</span>
                    <div className="flex-1 space-y-1">
                      <Input {...objectivesForm.register(`items.${index}.statement`)} />
                      {objectivesForm.formState.errors.items?.[index]?.statement && (
                        <p className="text-sm text-destructive">
                          {objectivesForm.formState.errors.items[index]?.statement?.message}
                        </p>
                      )}
                    </div>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      disabled={index === 0}
                      onClick={() => objectivesFieldArray.move(index, index - 1)}
                    >
                      <ArrowUp />
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      disabled={index === objectivesFieldArray.fields.length - 1}
                      onClick={() => objectivesFieldArray.move(index, index + 1)}
                    >
                      <ArrowDown />
                    </Button>
                    <Button type="button" variant="ghost" size="icon" onClick={() => objectivesFieldArray.remove(index)}>
                      <Trash2 />
                    </Button>
                  </div>
                ))}
                <div className="flex items-center gap-2">
                  <Button type="button" variant="outline" size="sm" onClick={() => objectivesFieldArray.append({ statement: "" })}>
                    <Plus />
                    Add objective
                  </Button>
                  <Button
                    type="submit"
                    size="sm"
                    disabled={!objectivesForm.formState.isDirty || objectivesMutation.isPending}
                  >
                    {objectivesMutation.isPending && <Loader2 className="animate-spin" />}
                    Save Objectives
                  </Button>
                </div>
              </form>
            ) : objectives.length === 0 ? (
              <p className="text-sm text-muted-foreground">No objectives added yet.</p>
            ) : (
              <ol className="list-decimal list-inside space-y-1 text-sm text-muted-foreground">
                {objectives.map((o) => (
                  <li key={o.id}>{o.statement}</li>
                ))}
              </ol>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Prerequisites</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            {prerequisites.length === 0 ? (
              <p className="text-sm text-muted-foreground">No prerequisites set.</p>
            ) : (
              <div className="space-y-2">
                {prerequisites.map((prereq) => {
                  const course = courseById[prereq.prerequisite_course_id]
                  return (
                    <div key={prereq.id} className="flex items-center justify-between gap-2 rounded-md border border-border px-3 py-2">
                      <span className="text-sm">
                        {course ? `${course.code} — ${course.title}` : prereq.prerequisite_course_id}
                      </span>
                      <PermissionGate permission="course.update">
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          disabled={removePrerequisiteMutation.isPending}
                          onClick={() => removePrerequisiteMutation.mutate(prereq.id)}
                        >
                          <X />
                        </Button>
                      </PermissionGate>
                    </div>
                  )
                })}
              </div>
            )}
            <PermissionGate permission="course.update">
              <Combobox
                options={availablePrerequisiteOptions}
                value=""
                onValueChange={(courseId) => addPrerequisiteMutation.mutate(courseId)}
                placeholder="Add prerequisite…"
                searchPlaceholder="Search courses…"
                emptyText="No more courses available."
                triggerClassName="w-72"
                disabled={addPrerequisiteMutation.isPending}
              />
            </PermissionGate>
          </CardContent>
        </Card>
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
  )
}
