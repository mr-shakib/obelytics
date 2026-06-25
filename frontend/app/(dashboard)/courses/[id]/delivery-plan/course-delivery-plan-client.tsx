"use client"

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useForm, useFieldArray, Controller } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { toast } from "sonner"
import { Loader2, Plus, Trash2, ArrowUp, ArrowDown } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { OutcomeCheckboxPopover } from "@/components/shared/outcome-checkbox-popover"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"
import { usePermission } from "@/hooks/use-permission"
import { useResolveCourseLocation } from "@/hooks/use-course-location"
import type { LessonPlanItem, CourseOutcome, ProgramOutcome, CurriculumDetail } from "../course-types"

type Program = { id: string; po_version_id?: string | null }

async function fetchProgramOutcomes(programId: string, poVersionId?: string | null) {
  const { data } = await apiClient.GET(`/program-outcomes?program_id=${programId}` as never)
  const programPos = ((data as unknown) as ProgramOutcome[]) ?? []
  if (programPos.length > 0 || !poVersionId) return programPos

  const { data: versionData } = await apiClient.GET(
    `/program-outcomes?po_version_id=${poVersionId}` as never
  )
  return ((versionData as unknown) as ProgramOutcome[]) ?? []
}

const lessonPlanItemSchema = z.object({
  week_number: z.number().int().min(1, "Required").max(52),
  lesson_label: z.string().max(100).optional(),
  topic: z.string().min(1, "Topic is required"),
  tla: z.string().optional(),
  assessment_strategy: z.string().optional(),
  co_ids: z.array(z.string()),
  po_ids: z.array(z.string()),
})
const lessonPlanSchema = z.object({
  items: z.array(lessonPlanItemSchema),
})
type LessonPlanFormValues = z.infer<typeof lessonPlanSchema>
type LessonPlanItemValues = z.infer<typeof lessonPlanItemSchema>

interface Props {
  id: string
}

export function CourseDeliveryPlanClient({ id }: Props) {
  const qc = useQueryClient()
  const canEditCourse = usePermission("course.update")

  const courseLocation = useResolveCourseLocation(id)
  const curriculumId = courseLocation?.curriculumId

  const { data: lessonPlanItems = [] } = useQuery({
    queryKey: queryKeys.courseLessonPlan.byCourse(id, curriculumId ?? ""),
    queryFn: async () => {
      const { data } = await apiClient.GET(
        `/courses/${id}/lesson-plan?curriculum_id=${curriculumId}` as never
      )
      return ((data as unknown) as LessonPlanItem[]) ?? []
    },
    enabled: !!curriculumId,
  })

  const { data: courseOutcomes = [] } = useQuery({
    queryKey: queryKeys.courseOutcomes.list(curriculumId, id),
    queryFn: async () => {
      const { data } = await apiClient.GET(
        `/course-outcomes?curriculum_id=${curriculumId}&course_id=${id}` as never
      )
      return ((data as unknown) as CourseOutcome[]) ?? []
    },
    enabled: !!curriculumId,
  })

  const { data: curriculumDetail } = useQuery({
    queryKey: queryKeys.curricula.detail(curriculumId ?? ""),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/curricula/${curriculumId}` as never)
      return (data as unknown) as CurriculumDetail
    },
    enabled: !!curriculumId,
  })
  const programId = curriculumDetail?.program_id

  const { data: program } = useQuery({
    queryKey: queryKeys.programs.detail(programId ?? ""),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/programs/${programId}` as never)
      return (data as unknown) as Program
    },
    enabled: !!programId,
  })

  const { data: programOutcomes = [] } = useQuery({
    queryKey: queryKeys.programOutcomes.list({
      program_id: programId,
      po_version_id: program?.po_version_id ?? undefined,
    }),
    queryFn: () => fetchProgramOutcomes(programId as string, program?.po_version_id),
    enabled: !!programId,
  })

  const courseOutcomeById = Object.fromEntries(courseOutcomes.map((co) => [co.id, co]))
  const programOutcomeById = Object.fromEntries(programOutcomes.map((po) => [po.id, po]))

  const toLessonPlanFormValues = (item: LessonPlanItem): LessonPlanItemValues => ({
    week_number: item.week_number,
    lesson_label: item.lesson_label ?? "",
    topic: item.topic,
    tla: item.tla ?? "",
    assessment_strategy: item.assessment_strategy ?? "",
    co_ids: item.co_ids,
    po_ids: item.po_ids,
  })

  const lessonPlanForm = useForm<LessonPlanFormValues>({
    resolver: zodResolver(lessonPlanSchema),
    values: { items: lessonPlanItems.map(toLessonPlanFormValues) },
  })
  const lessonPlanFieldArray = useFieldArray({ control: lessonPlanForm.control, name: "items" })

  const lessonPlanMutation = useMutation({
    mutationFn: async (items: LessonPlanItemValues[]) => {
      const { data } = await apiClient.PUT(
        `/courses/${id}/lesson-plan?curriculum_id=${curriculumId}` as never,
        {
          body: {
            items: items.map((item) => ({
              week_number: item.week_number,
              lesson_label: item.lesson_label || undefined,
              topic: item.topic.trim(),
              tla: item.tla?.trim() || undefined,
              assessment_strategy: item.assessment_strategy?.trim() || undefined,
              co_ids: item.co_ids,
              po_ids: item.po_ids,
            })),
          },
        } as never
      )
      return ((data as unknown) as LessonPlanItem[]) ?? []
    },
    onSuccess: (next) => {
      qc.setQueryData(queryKeys.courseLessonPlan.byCourse(id, curriculumId ?? ""), next)
      toast.success("Delivery plan updated")
    },
    onError: () => toast.error("Failed to update delivery plan"),
  })

  const onSubmitLessonPlan = lessonPlanForm.handleSubmit((values) => {
    lessonPlanMutation.mutate(values.items)
  })

  return (
    <Card>
      <CardHeader><CardTitle>Delivery Plan</CardTitle></CardHeader>
      <CardContent>
        {!curriculumId ? (
          <p className="text-sm text-muted-foreground">
            This course is not part of any curriculum yet.
          </p>
        ) : canEditCourse ? (
          <form onSubmit={onSubmitLessonPlan} className="space-y-4">
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-20">Week</TableHead>
                    <TableHead className="w-32">Lesson</TableHead>
                    <TableHead className="min-w-48">Topic</TableHead>
                    <TableHead className="min-w-48">T-L-A</TableHead>
                    <TableHead className="min-w-48">Assessment Strategy</TableHead>
                    <TableHead className="w-32">COs</TableHead>
                    <TableHead className="w-32">POs</TableHead>
                    <TableHead className="w-28" />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {lessonPlanFieldArray.fields.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={8} className="text-sm text-muted-foreground">
                        No delivery plan items added yet.
                      </TableCell>
                    </TableRow>
                  )}
                  {lessonPlanFieldArray.fields.map((field, index) => (
                    <TableRow key={field.id}>
                      <TableCell className="align-top">
                        <Input
                          type="number"
                          min={1}
                          max={52}
                          className="w-16"
                          {...lessonPlanForm.register(`items.${index}.week_number`, { valueAsNumber: true })}
                        />
                        {lessonPlanForm.formState.errors.items?.[index]?.week_number && (
                          <p className="text-xs text-destructive">
                            {lessonPlanForm.formState.errors.items[index]?.week_number?.message}
                          </p>
                        )}
                      </TableCell>
                      <TableCell className="align-top">
                        <Input
                          type="number"
                          min={1}
                          max={100}
                          className="w-20"
                          {...lessonPlanForm.register(`items.${index}.lesson_label`)}
                        />
                      </TableCell>
                      <TableCell className="align-top whitespace-normal">
                        <Textarea rows={2} className="min-w-48" {...lessonPlanForm.register(`items.${index}.topic`)} />
                        {lessonPlanForm.formState.errors.items?.[index]?.topic && (
                          <p className="text-xs text-destructive">
                            {lessonPlanForm.formState.errors.items[index]?.topic?.message}
                          </p>
                        )}
                      </TableCell>
                      <TableCell className="align-top whitespace-normal">
                        <Textarea rows={2} className="min-w-48" {...lessonPlanForm.register(`items.${index}.tla`)} />
                      </TableCell>
                      <TableCell className="align-top whitespace-normal">
                        <Textarea rows={2} className="min-w-48" {...lessonPlanForm.register(`items.${index}.assessment_strategy`)} />
                      </TableCell>
                      <TableCell className="align-top">
                        <Controller
                          control={lessonPlanForm.control}
                          name={`items.${index}.co_ids`}
                          render={({ field: coField }) => (
                            <OutcomeCheckboxPopover
                              options={courseOutcomes}
                              value={coField.value}
                              onChange={coField.onChange}
                              placeholder="Select COs"
                            />
                          )}
                        />
                      </TableCell>
                      <TableCell className="align-top">
                        <Controller
                          control={lessonPlanForm.control}
                          name={`items.${index}.po_ids`}
                          render={({ field: poField }) => (
                            <OutcomeCheckboxPopover
                              options={programOutcomes}
                              value={poField.value}
                              onChange={poField.onChange}
                              placeholder="Select POs"
                            />
                          )}
                        />
                      </TableCell>
                      <TableCell className="align-top">
                        <div className="flex items-center gap-1">
                          <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            disabled={index === 0}
                            onClick={() => lessonPlanFieldArray.move(index, index - 1)}
                          >
                            <ArrowUp />
                          </Button>
                          <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            disabled={index === lessonPlanFieldArray.fields.length - 1}
                            onClick={() => lessonPlanFieldArray.move(index, index + 1)}
                          >
                            <ArrowDown />
                          </Button>
                          <Button type="button" variant="ghost" size="icon" onClick={() => lessonPlanFieldArray.remove(index)}>
                            <Trash2 />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
            <div className="flex items-center gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() =>
                  lessonPlanFieldArray.append({
                    week_number: lessonPlanFieldArray.fields.length + 1,
                    lesson_label: "",
                    topic: "",
                    tla: "",
                    assessment_strategy: "",
                    co_ids: [],
                    po_ids: [],
                  })
                }
              >
                <Plus />
                Add week
              </Button>
              <Button
                type="submit"
                size="sm"
                disabled={!lessonPlanForm.formState.isDirty || lessonPlanMutation.isPending}
              >
                {lessonPlanMutation.isPending && <Loader2 className="animate-spin" />}
                Save Delivery Plan
              </Button>
            </div>
          </form>
        ) : lessonPlanItems.length === 0 ? (
          <p className="text-sm text-muted-foreground">No delivery plan added yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Week</TableHead>
                  <TableHead>Lesson</TableHead>
                  <TableHead>Topic</TableHead>
                  <TableHead>T-L-A</TableHead>
                  <TableHead>Assessment Strategy</TableHead>
                  <TableHead>COs</TableHead>
                  <TableHead>POs</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {lessonPlanItems.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell className="align-top">{item.week_number}</TableCell>
                    <TableCell className="align-top">{item.lesson_label || "—"}</TableCell>
                    <TableCell className="align-top whitespace-normal">{item.topic}</TableCell>
                    <TableCell className="align-top whitespace-normal">{item.tla || "—"}</TableCell>
                    <TableCell className="align-top whitespace-normal">{item.assessment_strategy || "—"}</TableCell>
                    <TableCell className="align-top whitespace-normal">
                      {item.co_ids.map((coId) => courseOutcomeById[coId]?.code).filter(Boolean).join(", ") || "—"}
                    </TableCell>
                    <TableCell className="align-top whitespace-normal">
                      {item.po_ids.map((poId) => programOutcomeById[poId]?.code).filter(Boolean).join(", ") || "—"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
