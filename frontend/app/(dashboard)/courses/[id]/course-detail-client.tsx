"use client"

import { useState, type FormEvent } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useForm, useFieldArray } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { toast } from "sonner"
import { Loader2, Lock, Plus, Trash2, ArrowUp, ArrowDown, X } from "lucide-react"
import Link from "next/link"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Badge } from "@/components/ui/badge"
import { Combobox } from "@/components/ui/combobox"
import { StatusBadge } from "@/components/shared/status-badge"
import { PageHeader } from "@/components/shared/page-header"
import { PermissionGate } from "@/components/shared/permission-gate"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"
import { usePermission } from "@/hooks/use-permission"
import { useResolveCourseLocation } from "@/hooks/use-course-location"

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
  syllabus_content: string | null
  status: string
}

type CourseCategory = { id: string; name: string }

type BloomDomain = { id: string; name: string }

type AssessmentType = { id: string; name: string; is_sessional: boolean }

type CourseAssessmentTool = {
  id: string
  assessment_type_id: string
  assessment_type_name: string
  is_sessional: boolean
  is_locked: boolean
}

type CourseObjective = { id: string; order_index: number; statement: string }

type Prerequisite = { id: string; course_id: string; prerequisite_course_id: string }

type CourseListItem = { id: string; code: string; title: string }

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

  const courseLocation = useResolveCourseLocation(id)
  const curriculumId = courseLocation?.curriculumId

  const { data: assessmentTypes = [] } = useQuery({
    queryKey: queryKeys.refData.assessmentTypes,
    queryFn: async () => {
      const { data } = await apiClient.GET("/ref-data/assessment-types" as never)
      return ((data as unknown) as AssessmentType[]) ?? []
    },
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

  const setToolsMutation = useMutation({
    mutationFn: async (assessmentTypeIds: string[]) => {
      const { data } = await apiClient.PUT(
        `/courses/${id}/assessment-tools?curriculum_id=${curriculumId}` as never,
        { body: { assessment_type_ids: assessmentTypeIds } } as never
      )
      return ((data as unknown) as CourseAssessmentTool[]) ?? []
    },
    onSuccess: (next) => {
      qc.setQueryData(queryKeys.courseAssessmentTools.byCourse(id, curriculumId ?? ""), next)
    },
    onError: () => toast.error("Failed to update assessment tools"),
  })

  const toggleAssessmentTool = (assessmentTypeId: string, checked: boolean) => {
    const currentIds = assessmentTools.map((t) => t.assessment_type_id)
    const next = checked
      ? [...currentIds, assessmentTypeId]
      : currentIds.filter((tid) => tid !== assessmentTypeId)
    setToolsMutation.mutate(next)
  }

  const addAssessmentTool = (assessmentTypeId: string) => {
    if (!assessmentTypeId) return
    const currentIds = assessmentTools.map((t) => t.assessment_type_id)
    if (currentIds.includes(assessmentTypeId)) return
    setToolsMutation.mutate([...currentIds, assessmentTypeId])
  }

  const [showNewToolForm, setShowNewToolForm] = useState(false)
  const [newToolName, setNewToolName] = useState("")

  const createToolTypeMutation = useMutation({
    mutationFn: async (name: string) => {
      const { data } = await apiClient.POST("/ref-data/assessment-types" as never, {
        body: { name, is_sessional: false },
      } as never)
      return (data as unknown) as AssessmentType
    },
    onSuccess: (newType) => {
      qc.invalidateQueries({ queryKey: queryKeys.refData.assessmentTypes })
      addAssessmentTool(newType.id)
      setNewToolName("")
      setShowNewToolForm(false)
    },
    onError: () => toast.error("Failed to create assessment tool type"),
  })

  const handleCreateNewTool = (e: FormEvent) => {
    e.preventDefault()
    const name = newToolName.trim()
    if (!name) return
    createToolTypeMutation.mutate(name)
  }

  const usedAssessmentTypeIds = new Set(assessmentTools.map((t) => t.assessment_type_id))
  const availableAssessmentTypeOptions = assessmentTypes
    .filter((t) => !usedAssessmentTypeIds.has(t.id))
    .map((t) => ({ value: t.id, label: t.is_sessional ? `${t.name} (Sessional)` : t.name }))

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
          syllabus_content: data.syllabus_content ?? "",
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

          {data.syllabus_content && (
            <Card>
              <CardHeader><CardTitle>Course Content</CardTitle></CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground whitespace-pre-wrap">{data.syllabus_content}</p>
              </CardContent>
            </Card>
          )}

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
            <CardHeader><CardTitle>Assessment Tools</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              {!curriculumId ? (
                <p className="text-sm text-muted-foreground">
                  This course is not part of any curriculum yet.
                </p>
              ) : (
                <>
                  <p className="text-sm text-muted-foreground">
                    Select the assessment tools used to evaluate this course.
                  </p>

                  <PermissionGate permission="course.update">
                    <div className="flex flex-wrap items-center gap-2">
                      <Combobox
                        options={availableAssessmentTypeOptions}
                        value=""
                        onValueChange={addAssessmentTool}
                        placeholder="Add assessment tool…"
                        searchPlaceholder="Search tools…"
                        emptyText="No more tools available."
                        triggerClassName="w-56"
                        disabled={setToolsMutation.isPending}
                      />
                      {showNewToolForm ? (
                        <form onSubmit={handleCreateNewTool} className="flex items-center gap-2">
                          <Input
                            value={newToolName}
                            onChange={(e) => setNewToolName(e.target.value)}
                            placeholder="New tool name"
                            className="h-9 w-44"
                            autoFocus
                          />
                          <Button
                            type="submit"
                            size="sm"
                            disabled={!newToolName.trim() || createToolTypeMutation.isPending}
                          >
                            {createToolTypeMutation.isPending && <Loader2 className="animate-spin" />}
                            Create
                          </Button>
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                              setShowNewToolForm(false)
                              setNewToolName("")
                            }}
                          >
                            Cancel
                          </Button>
                        </form>
                      ) : (
                        <Button type="button" variant="outline" size="sm" onClick={() => setShowNewToolForm(true)}>
                          <Plus />
                          Add new
                        </Button>
                      )}
                    </div>
                  </PermissionGate>

                  {assessmentTools.length === 0 ? (
                    <p className="text-sm text-muted-foreground">No assessment tools selected.</p>
                  ) : (
                    <div className="space-y-2">
                      {assessmentTools.map((tool) => (
                        <div key={tool.id} className="flex items-center gap-2">
                          <input
                            type="checkbox"
                            id={`assessment-tool-${tool.assessment_type_id}`}
                            checked
                            disabled={tool.is_locked || !canEditCourse || setToolsMutation.isPending}
                            onChange={(e) => toggleAssessmentTool(tool.assessment_type_id, e.target.checked)}
                            className="h-4 w-4 rounded border-border disabled:opacity-50 disabled:cursor-not-allowed"
                          />
                          <Label htmlFor={`assessment-tool-${tool.assessment_type_id}`} className="font-normal">
                            {tool.assessment_type_name}
                          </Label>
                          {tool.is_sessional && (
                            <Badge variant="secondary" className="font-normal">Sessional</Badge>
                          )}
                          {tool.is_locked && <Lock className="h-3 w-3 text-muted-foreground" />}
                        </div>
                      ))}
                    </div>
                  )}
                </>
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
                    <Label htmlFor="description">Description / Rationale</Label>
                    <Textarea id="description" rows={3} {...register("description")} />
                    {errors.description && <p className="text-sm text-destructive">{errors.description.message}</p>}
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="syllabus_content">Course Content (Syllabus)</Label>
                    <Textarea id="syllabus_content" rows={5} {...register("syllabus_content")} />
                    {errors.syllabus_content && <p className="text-sm text-destructive">{errors.syllabus_content.message}</p>}
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
