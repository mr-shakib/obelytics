"use client"

import { useState, useEffect } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useForm, Controller } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { toast } from "sonner"
import { Plus, Loader2, Pencil, Trash2 } from "lucide-react"
import { PageHeader } from "@/components/shared/page-header"
import { StatusBadge } from "@/components/shared/status-badge"
import { PermissionGate } from "@/components/shared/permission-gate"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"
import { truncate } from "@/lib/utils"

// ── Types ─────────────────────────────────────────────────────────────────────

type Curriculum = { id: string; name: string; code: string; program_id: string }
type TermDef    = { id: string; term_number: number; name: string }
type CourseSlot = { id: string; curriculum_term_definition_id: string; course_id: string; is_elective: boolean }
type Course     = { id: string; code: string; title: string }
type BloomLevel = { id: string; code: string; name: string; bloom_domain_id: string; order_index: number }
type CourseOutcome = {
  id: string
  code: string
  statement: string
  bloom_level_id: string | null
  status: string
}

// ── Form schema ───────────────────────────────────────────────────────────────

const coSchema = z.object({
  code:           z.string().min(1, "Code is required").max(20),
  statement:      z.string().min(10, "At least 10 characters"),
  bloom_level_id: z.string().optional(),
})
type COFormValues = z.infer<typeof coSchema>

// ── CO row ────────────────────────────────────────────────────────────────────

function CORow({
  co,
  bloomName,
  onEdit,
  onDelete,
  canEdit,
}: {
  co: CourseOutcome
  bloomName: string
  onEdit: (co: CourseOutcome) => void
  onDelete: (id: string) => void
  canEdit: boolean
}) {
  const deletable = co.status === "DRAFT"

  return (
    <div className="flex items-start justify-between gap-4 px-4 py-3 border-b border-border last:border-0 hover:bg-muted/30 transition-colors group">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-mono font-semibold text-sm">{co.code}</span>
          <StatusBadge status={co.status} />
          {bloomName && (
            <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded-full">
              {bloomName}
            </span>
          )}
        </div>
        <p className="mt-1 text-sm text-muted-foreground leading-relaxed" title={co.statement}>
          {truncate(co.statement, 120)}
        </p>
      </div>
      {canEdit && (
        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
          <Button
            size="sm"
            variant="ghost"
            className="h-7 w-7 p-0"
            onClick={() => onEdit(co)}
            title="Edit"
          >
            <Pencil className="h-3.5 w-3.5" />
          </Button>
          <Button
            size="sm"
            variant="ghost"
            className="h-7 w-7 p-0 text-destructive hover:text-destructive"
            onClick={() => onDelete(co.id)}
            disabled={!deletable}
            title={deletable ? "Delete" : "Cannot delete — not a draft"}
          >
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
        </div>
      )}
    </div>
  )
}

// ── Add / Edit dialog ─────────────────────────────────────────────────────────

function CODialog({
  open,
  onOpenChange,
  editing,
  bloomLevels,
  suggestedCode,
  onSubmit,
  isPending,
}: {
  open: boolean
  onOpenChange: (v: boolean) => void
  editing: CourseOutcome | null
  bloomLevels: BloomLevel[]
  suggestedCode: string
  onSubmit: (values: COFormValues) => void
  isPending: boolean
}) {
  const {
    register,
    handleSubmit,
    control,
    reset,
    formState: { errors },
  } = useForm<COFormValues>({ resolver: zodResolver(coSchema) })

  useEffect(() => {
    if (open) {
      reset(
        editing
          ? { code: editing.code, statement: editing.statement, bloom_level_id: editing.bloom_level_id ?? "" }
          : { code: suggestedCode, statement: "", bloom_level_id: "" }
      )
    }
  }, [open, editing, suggestedCode, reset])

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{editing ? "Edit Course Outcome" : "Add Course Outcome"}</DialogTitle>
        </DialogHeader>
        <form id="co-form" onSubmit={handleSubmit(onSubmit)} className="space-y-4 py-2">
          <div className="space-y-2">
            <Label htmlFor="co-code">Code</Label>
            <Input id="co-code" {...register("code")} placeholder={suggestedCode} />
            {errors.code && <p className="text-sm text-destructive">{errors.code.message}</p>}
          </div>

          <div className="space-y-2">
            <Label htmlFor="co-stmt">Statement</Label>
            <Textarea
              id="co-stmt"
              {...register("statement")}
              placeholder="Describe what students will be able to do..."
              rows={4}
            />
            {errors.statement && <p className="text-sm text-destructive">{errors.statement.message}</p>}
          </div>

          <div className="space-y-2">
            <Label>Bloom Level <span className="text-muted-foreground font-normal">(optional)</span></Label>
            <Controller
              name="bloom_level_id"
              control={control}
              render={({ field }) => (
                <Select value={field.value ?? ""} onValueChange={field.onChange}>
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Select bloom level">
                      {(v: string | null) => {
                        const bl = bloomLevels.find((b) => b.id === v)
                        return bl ? `${bl.code} — ${bl.name}` : null
                      }}
                    </SelectValue>
                  </SelectTrigger>
                  <SelectContent>
                    {bloomLevels.map((b) => (
                      <SelectItem key={b.id} value={b.id}>{b.code} — {b.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            />
          </div>
        </form>
        <DialogFooter showCloseButton>
          <Button type="submit" form="co-form" disabled={isPending}>
            {isPending && <Loader2 className="animate-spin" />}
            {editing ? "Save Changes" : "Add CO"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export function CourseOutcomesClient() {
  const qc = useQueryClient()

  const [curriculumId, setCurriculumId] = useState("")
  const [termDefId,    setTermDefId]    = useState("")
  const [courseId,     setCourseId]     = useState("")
  const [dialogOpen,   setDialogOpen]   = useState(false)
  const [editing,      setEditing]      = useState<CourseOutcome | null>(null)

  // ── Remote data ──────────────────────────────────────────────────────────

  const { data: curricula = [] } = useQuery({
    queryKey: queryKeys.curricula.all,
    queryFn: async () => {
      const { data } = await apiClient.GET("/curricula" as never)
      return ((data as unknown) as Curriculum[]) ?? []
    },
  })

  const { data: termDefs = [] } = useQuery({
    queryKey: queryKeys.curricula.terms(curriculumId),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/curricula/${curriculumId}/terms` as never)
      return ((data as unknown) as TermDef[]) ?? []
    },
    enabled: !!curriculumId,
  })

  const { data: courseSlots = [] } = useQuery({
    queryKey: queryKeys.curricula.courseSlots(curriculumId),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/curricula/${curriculumId}/course-slots` as never)
      return ((data as unknown) as CourseSlot[]) ?? []
    },
    enabled: !!curriculumId,
  })

  const { data: allCourses = [] } = useQuery({
    queryKey: queryKeys.courses.all,
    queryFn: async () => {
      const { data } = await apiClient.GET("/courses" as never)
      return ((data as unknown) as Course[]) ?? []
    },
  })

  const { data: bloomLevels = [] } = useQuery({
    queryKey: queryKeys.refData.bloomLevels,
    queryFn: async () => {
      const { data } = await apiClient.GET("/ref-data/bloom-levels" as never)
      return ((data as unknown) as BloomLevel[]) ?? []
    },
  })

  const { data: cos = [], isLoading: cosLoading } = useQuery({
    queryKey: queryKeys.courseOutcomes.list(curriculumId, courseId),
    queryFn: async () => {
      const { data } = await apiClient.GET(
        `/course-outcomes?curriculum_id=${curriculumId}&course_id=${courseId}` as never
      )
      return ((data as unknown) as CourseOutcome[]) ?? []
    },
    enabled: !!curriculumId && !!courseId,
  })

  // ── Derived ──────────────────────────────────────────────────────────────

  const courseIdsInTerm = termDefId
    ? courseSlots
        .filter((s) => s.curriculum_term_definition_id === termDefId)
        .map((s) => s.course_id)
    : []

  const coursesInTerm = allCourses.filter((c) => courseIdsInTerm.includes(c.id))

  const bloomMap = new Map(bloomLevels.map((b) => [b.id, `${b.code} — ${b.name}`]))
  const suggestedCode = `CO${cos.length + 1}`

  // ── Mutations ────────────────────────────────────────────────────────────

  const addMutation = useMutation({
    mutationFn: async (values: COFormValues) => {
      await apiClient.POST("/course-outcomes" as never, {
        body: { curriculum_id: curriculumId, course_id: courseId, ...values },
      } as never)
    },
    onSuccess: () => {
      toast.success("Course Outcome added")
      qc.invalidateQueries({ queryKey: queryKeys.courseOutcomes.list(curriculumId, courseId) })
      setDialogOpen(false)
      setEditing(null)
    },
    onError: () => toast.error("Failed to add CO"),
  })

  const editMutation = useMutation({
    mutationFn: async (values: COFormValues) => {
      await apiClient.PATCH(`/course-outcomes/${editing!.id}` as never, { body: values } as never)
    },
    onSuccess: () => {
      toast.success("Course Outcome updated")
      qc.invalidateQueries({ queryKey: queryKeys.courseOutcomes.list(curriculumId, courseId) })
      setDialogOpen(false)
      setEditing(null)
    },
    onError: () => toast.error("Failed to update CO"),
  })

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      await apiClient.DELETE(`/course-outcomes/${id}` as never)
    },
    onSuccess: () => {
      toast.success("Course Outcome deleted")
      qc.invalidateQueries({ queryKey: queryKeys.courseOutcomes.list(curriculumId, courseId) })
    },
    onError: () => toast.error("Cannot delete — only DRAFT outcomes can be removed"),
  })

  // ── Handlers ─────────────────────────────────────────────────────────────

  function openAdd() {
    setEditing(null)
    setDialogOpen(true)
  }

  function openEdit(co: CourseOutcome) {
    setEditing(co)
    setDialogOpen(true)
  }

  function handleChangeCurriculum(val: string | null) {
    setCurriculumId(val ?? "")
    setTermDefId("")
    setCourseId("")
  }

  function handleChangeTerm(val: string | null) {
    setTermDefId(val ?? "")
    setCourseId("")
  }

  const selectedCourse = allCourses.find((c) => c.id === courseId)

  return (
    <div>
      <PageHeader
        title="Course Outcomes"
        description="Select a curriculum, semester and course to manage its learning outcomes."
        actions={
          courseId && (
            <PermissionGate permission="co.create">
              <Button onClick={openAdd}>
                <Plus className="h-4 w-4" />
                Add CO
              </Button>
            </PermissionGate>
          )
        }
      />

      {/* Cascading selectors */}
      <div className="flex flex-wrap gap-3 mb-6">
        <div className="w-56">
          <Select value={curriculumId} onValueChange={handleChangeCurriculum}>
            <SelectTrigger>
              <SelectValue placeholder="1. Select curriculum">
                {(v: string | null) => v ? (curricula.find((c) => c.id === v)?.name ?? v) : null}
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              {curricula.map((c) => (
                <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="w-48">
          <Select value={termDefId} onValueChange={handleChangeTerm} disabled={!curriculumId}>
            <SelectTrigger>
              <SelectValue placeholder={curriculumId ? "2. Select semester" : "2. Curriculum first"}>
                {(v: string | null) => {
                  const t = termDefs.find((td) => td.id === v)
                  return t ? `Sem ${t.term_number} — ${t.name}` : null
                }}
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              {termDefs.map((t) => (
                <SelectItem key={t.id} value={t.id}>Sem {t.term_number} — {t.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="w-64">
          <Select value={courseId} onValueChange={(v) => setCourseId(v ?? "")} disabled={!termDefId}>
            <SelectTrigger>
              <SelectValue placeholder={termDefId ? "3. Select course" : "3. Semester first"}>
                {(v: string | null) => {
                  const c = coursesInTerm.find((co) => co.id === v)
                  return c ? `${c.code} — ${c.title}` : null
                }}
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              {coursesInTerm.length === 0 && (
                <SelectItem value="__none__" disabled>No courses in this semester</SelectItem>
              )}
              {coursesInTerm.map((c) => (
                <SelectItem key={c.id} value={c.id}>{c.code} — {c.title}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* CO list */}
      {!courseId && (
        <div className="border border-dashed border-border rounded-lg p-12 text-center text-sm text-muted-foreground">
          Select a curriculum, semester, and course to see its outcomes.
        </div>
      )}

      {courseId && (
        <div className="border border-border rounded-lg overflow-hidden">
          <div className="px-4 py-2.5 bg-muted/40 border-b border-border flex items-center justify-between">
            <span className="text-sm font-medium">
              {selectedCourse ? `${selectedCourse.code} — ${selectedCourse.title}` : ""}
            </span>
            <span className="text-xs text-muted-foreground">{cos.length} outcome{cos.length !== 1 ? "s" : ""}</span>
          </div>

          {cosLoading ? (
            <div className="p-8 text-center text-sm text-muted-foreground">Loading…</div>
          ) : cos.length === 0 ? (
            <div className="p-8 text-center text-sm text-muted-foreground">
              No outcomes yet.{" "}
              <PermissionGate permission="co.create">
                <button
                  type="button"
                  className="text-primary underline"
                  onClick={openAdd}
                >
                  Add the first CO.
                </button>
              </PermissionGate>
            </div>
          ) : (
            cos.map((co) => (
              <CORow
                key={co.id}
                co={co}
                bloomName={bloomMap.get(co.bloom_level_id ?? "") ?? ""}
                onEdit={openEdit}
                onDelete={(id) => deleteMutation.mutate(id)}
                canEdit={true}
              />
            ))
          )}
        </div>
      )}

      <CODialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        editing={editing}
        bloomLevels={bloomLevels}
        suggestedCode={suggestedCode}
        onSubmit={(v) => (editing ? editMutation : addMutation).mutate(v)}
        isPending={addMutation.isPending || editMutation.isPending}
      />
    </div>
  )
}
