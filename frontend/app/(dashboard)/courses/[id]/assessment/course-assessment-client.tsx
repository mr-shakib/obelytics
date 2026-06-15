"use client"

import { useState, type FormEvent } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { toast } from "sonner"
import { Loader2, Lock, Plus } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Combobox } from "@/components/ui/combobox"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { PermissionGate } from "@/components/shared/permission-gate"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"
import { usePermission } from "@/hooks/use-permission"
import { useResolveCourseLocation } from "@/hooks/use-course-location"
import type {
  BloomDomain,
  BloomLevel,
  AssessmentType,
  CourseAssessmentTool,
  CourseCOMark,
  CourseBloomMark,
} from "../course-types"

const TOTAL_COL = "TOTAL"
const marksGridSchema = z.object({
  cells: z.record(z.string(), z.coerce.number().min(0, "Min 0").max(999, "Max 999")),
})

interface Props {
  id: string
}

export function CourseAssessmentClient({ id }: Props) {
  const qc = useQueryClient()
  const canEditCourse = usePermission("course.update")

  const courseLocation = useResolveCourseLocation(id)
  const curriculumId = courseLocation?.curriculumId

  const { data: bloomDomains = [] } = useQuery({
    queryKey: queryKeys.refData.bloomDomains,
    queryFn: async () => {
      const { data } = await apiClient.GET("/ref-data/bloom-domains" as never)
      return ((data as unknown) as BloomDomain[]) ?? []
    },
  })

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

  // ── Assessment Pattern (total marks + CIE/SEE Bloom breakdown) ────────────

  const { data: bloomLevels = [] } = useQuery({
    queryKey: queryKeys.refData.bloomLevels,
    queryFn: async () => {
      const { data } = await apiClient.GET("/ref-data/bloom-levels" as never)
      return ((data as unknown) as BloomLevel[]) ?? []
    },
  })

  const cognitiveDomainId = bloomDomains.find((d) => d.name.toLowerCase() === "cognitive")?.id
  const cognitiveBloomLevels = bloomLevels
    .filter((l) => l.bloom_domain_id === cognitiveDomainId)
    .sort((a, b) => a.order_index - b.order_index)

  const { data: courseCOMarks = [] } = useQuery({
    queryKey: queryKeys.courseAssessmentPattern.byCourse(id, curriculumId ?? ""),
    queryFn: async () => {
      const { data } = await apiClient.GET(
        `/courses/${id}/assessment-pattern?curriculum_id=${curriculumId}` as never
      )
      return ((data as unknown) as CourseCOMark[]) ?? []
    },
    enabled: !!curriculumId,
  })

  const { data: courseBloomMarks = [] } = useQuery({
    queryKey: queryKeys.courseBloomMarks.byCourse(id, curriculumId ?? ""),
    queryFn: async () => {
      const { data } = await apiClient.GET(
        `/courses/${id}/bloom-marks?curriculum_id=${curriculumId}` as never
      )
      return ((data as unknown) as CourseBloomMark[]) ?? []
    },
    enabled: !!curriculumId,
  })

  const coMarkCellKey = (assessmentTypeId: string, coId: string) => `${assessmentTypeId}::${coId}`
  const bloomMarkCellKey = (assessmentTypeId: string, bloomLevelId: string) => `${assessmentTypeId}::${bloomLevelId}`

  const coMarkByKey = Object.fromEntries(
    courseCOMarks.map((m) => [coMarkCellKey(m.assessment_type_id, m.course_outcome_id ?? TOTAL_COL), Number(m.marks)])
  )
  const bloomMarkByKey = Object.fromEntries(
    courseBloomMarks.map((m) => [bloomMarkCellKey(m.assessment_type_id, m.bloom_level_id), Number(m.marks)])
  )

  const coMarksDefaults: Record<string, number> = {}
  for (const tool of assessmentTools) {
    const totalKey = coMarkCellKey(tool.assessment_type_id, TOTAL_COL)
    coMarksDefaults[totalKey] = coMarkByKey[totalKey] ?? 0
  }

  const bloomMarksDefaults: Record<string, number> = {}
  for (const tool of assessmentTools) {
    for (const level of cognitiveBloomLevels) {
      const key = bloomMarkCellKey(tool.assessment_type_id, level.id)
      bloomMarksDefaults[key] = bloomMarkByKey[key] ?? 0
    }
  }

  const coMarksForm = useForm({
    resolver: zodResolver(marksGridSchema),
    values: { cells: coMarksDefaults },
  })

  const bloomMarksForm = useForm({
    resolver: zodResolver(marksGridSchema),
    values: { cells: bloomMarksDefaults },
  })

  const coMarksMutation = useMutation({
    mutationFn: async (cells: Record<string, number>) => {
      const marks = Object.entries(cells)
        .filter(([, value]) => value > 0)
        .map(([key, value]) => {
          const [assessmentTypeId, coKey] = key.split("::")
          return {
            assessment_type_id: assessmentTypeId,
            course_outcome_id: coKey === TOTAL_COL ? null : coKey,
            marks: value,
          }
        })
      const { data } = await apiClient.PUT(
        `/courses/${id}/assessment-pattern?curriculum_id=${curriculumId}` as never,
        { body: { marks } } as never
      )
      return ((data as unknown) as CourseCOMark[]) ?? []
    },
    onSuccess: (next) => {
      qc.setQueryData(queryKeys.courseAssessmentPattern.byCourse(id, curriculumId ?? ""), next)
      toast.success("Assessment pattern updated")
    },
    onError: () => toast.error("Failed to update assessment pattern"),
  })

  const bloomMarksMutation = useMutation({
    mutationFn: async (cells: Record<string, number>) => {
      const marks = Object.entries(cells)
        .filter(([, value]) => value > 0)
        .map(([key, value]) => {
          const [assessmentTypeId, bloomLevelId] = key.split("::")
          const tool = assessmentTools.find((t) => t.assessment_type_id === assessmentTypeId)
          return {
            assessment_type_id: assessmentTypeId,
            bloom_level_id: bloomLevelId,
            component: tool?.is_sessional ? "CIE" : "SEE",
            marks: value,
          }
        })
      const { data } = await apiClient.PUT(
        `/courses/${id}/bloom-marks?curriculum_id=${curriculumId}` as never,
        { body: { marks } } as never
      )
      return ((data as unknown) as CourseBloomMark[]) ?? []
    },
    onSuccess: (next) => {
      qc.setQueryData(queryKeys.courseBloomMarks.byCourse(id, curriculumId ?? ""), next)
      toast.success("Bloom marks breakdown updated")
    },
    onError: () => toast.error("Failed to update Bloom marks breakdown"),
  })

  const onSubmitCoMarks = coMarksForm.handleSubmit((values) => {
    coMarksMutation.mutate(values.cells)
  })

  const onSubmitBloomMarks = bloomMarksForm.handleSubmit((values) => {
    bloomMarksMutation.mutate(values.cells)
  })

  const coMarksGrandTotal = assessmentTools.reduce((sum, tool) => {
    const v = coMarksForm.watch(`cells.${coMarkCellKey(tool.assessment_type_id, TOTAL_COL)}`)
    return sum + (Number.isFinite(Number(v)) ? Number(v) : 0)
  }, 0)

  const bloomCells = bloomMarksForm.watch("cells") ?? {}
  let cieTotal = 0
  let seeTotal = 0
  for (const tool of assessmentTools) {
    for (const level of cognitiveBloomLevels) {
      const v = Number(bloomCells[bloomMarkCellKey(tool.assessment_type_id, level.id)] ?? 0)
      if (tool.is_sessional) cieTotal += v
      else seeTotal += v
    }
  }

  return (
    <div className="space-y-6">
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
        <CardHeader><CardTitle>Total Marks per Assessment Tool</CardTitle></CardHeader>
        <CardContent>
          {!curriculumId ? (
            <p className="text-sm text-muted-foreground">
              This course is not part of any curriculum yet.
            </p>
          ) : assessmentTools.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              Configure assessment tools above before defining total marks.
            </p>
          ) : canEditCourse ? (
            <form onSubmit={onSubmitCoMarks} className="space-y-4">
              <p className="text-sm text-muted-foreground">
                Define the full marks for each assessment tool (e.g. Mid, Final). The CO-wise
                breakdown of these marks is configured by section teachers when entering marks,
                and the Bloom-wise breakdown below should add up to these totals.
              </p>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="min-w-40">Assessment Type</TableHead>
                      <TableHead className="w-24 text-center">Component</TableHead>
                      <TableHead className="w-28 text-center">Total Marks</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {assessmentTools.map((tool) => (
                      <TableRow key={tool.id}>
                        <TableCell className="align-top">{tool.assessment_type_name}</TableCell>
                        <TableCell className="align-top text-center">
                          <Badge variant="outline">{tool.is_sessional ? "CIE" : "SEE"}</Badge>
                        </TableCell>
                        <TableCell className="align-top">
                          <Input
                            type="number"
                            min={0}
                            max={999}
                            step="0.01"
                            className="w-28"
                            {...coMarksForm.register(`cells.${coMarkCellKey(tool.assessment_type_id, TOTAL_COL)}`)}
                          />
                        </TableCell>
                      </TableRow>
                    ))}
                    <TableRow>
                      <TableCell className="font-medium" colSpan={2}>Grand total</TableCell>
                      <TableCell>
                        <Badge variant={coMarksGrandTotal === 100 ? "default" : "destructive"}>
                          {coMarksGrandTotal} / 100
                        </Badge>
                      </TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </div>
              <Button
                type="submit"
                size="sm"
                disabled={!coMarksForm.formState.isDirty || coMarksMutation.isPending}
              >
                {coMarksMutation.isPending && <Loader2 className="animate-spin" />}
                Save Assessment Pattern
              </Button>
            </form>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Assessment Type</TableHead>
                    <TableHead className="text-center">Component</TableHead>
                    <TableHead className="text-center">Total Marks</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {assessmentTools.map((tool) => (
                    <TableRow key={tool.id}>
                      <TableCell>{tool.assessment_type_name}</TableCell>
                      <TableCell className="text-center">
                        <Badge variant="outline">{tool.is_sessional ? "CIE" : "SEE"}</Badge>
                      </TableCell>
                      <TableCell className="text-center">
                        {coMarkByKey[coMarkCellKey(tool.assessment_type_id, TOTAL_COL)] ?? 0}
                      </TableCell>
                    </TableRow>
                  ))}
                  <TableRow>
                    <TableCell className="font-medium" colSpan={2}>Grand total</TableCell>
                    <TableCell className="text-center">
                      <Badge variant={coMarksGrandTotal === 100 ? "default" : "destructive"}>
                        {coMarksGrandTotal} / 100
                      </Badge>
                    </TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>CIE/SEE Bloom-wise Marks Breakdown</CardTitle></CardHeader>
        <CardContent>
          {!curriculumId ? (
            <p className="text-sm text-muted-foreground">
              This course is not part of any curriculum yet.
            </p>
          ) : assessmentTools.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              Configure assessment tools above before defining the Bloom-level breakdown.
            </p>
          ) : cognitiveBloomLevels.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No Cognitive domain Bloom levels are configured.
            </p>
          ) : canEditCourse ? (
            <form onSubmit={onSubmitBloomMarks} className="space-y-4">
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="min-w-40">Assessment Type</TableHead>
                      <TableHead className="w-20 text-center">Component</TableHead>
                      {cognitiveBloomLevels.map((level) => (
                        <TableHead key={level.id} className="w-20 text-center" title={level.name}>
                          {level.code}
                        </TableHead>
                      ))}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {assessmentTools.map((tool) => (
                      <TableRow key={tool.id}>
                        <TableCell className="align-top">{tool.assessment_type_name}</TableCell>
                        <TableCell className="align-top text-center">
                          <Badge variant="outline">{tool.is_sessional ? "CIE" : "SEE"}</Badge>
                        </TableCell>
                        {cognitiveBloomLevels.map((level) => (
                          <TableCell key={level.id} className="align-top">
                            <Input
                              type="number"
                              min={0}
                              max={999}
                              step="0.01"
                              className="w-20"
                              {...bloomMarksForm.register(`cells.${bloomMarkCellKey(tool.assessment_type_id, level.id)}`)}
                            />
                          </TableCell>
                        ))}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="outline">CIE total: {cieTotal}</Badge>
                <Badge variant="outline">SEE total: {seeTotal}</Badge>
                <Badge variant={cieTotal + seeTotal === 100 ? "default" : "destructive"}>
                  Grand total: {cieTotal + seeTotal} / 100
                </Badge>
              </div>
              <Button
                type="submit"
                size="sm"
                disabled={!bloomMarksForm.formState.isDirty || bloomMarksMutation.isPending}
              >
                {bloomMarksMutation.isPending && <Loader2 className="animate-spin" />}
                Save Bloom Breakdown
              </Button>
            </form>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Assessment Type</TableHead>
                    <TableHead className="text-center">Component</TableHead>
                    {cognitiveBloomLevels.map((level) => (
                      <TableHead key={level.id} className="text-center" title={level.name}>
                        {level.code}
                      </TableHead>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {assessmentTools.map((tool) => (
                    <TableRow key={tool.id}>
                      <TableCell>{tool.assessment_type_name}</TableCell>
                      <TableCell className="text-center">
                        <Badge variant="outline">{tool.is_sessional ? "CIE" : "SEE"}</Badge>
                      </TableCell>
                      {cognitiveBloomLevels.map((level) => (
                        <TableCell key={level.id} className="text-center">
                          {bloomMarkByKey[bloomMarkCellKey(tool.assessment_type_id, level.id)] ?? 0}
                        </TableCell>
                      ))}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
