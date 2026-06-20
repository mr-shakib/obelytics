"use client"

import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { AlertTriangle, Loader2, Plus, Trash2, UserCog, X } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Combobox } from "@/components/ui/combobox"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { StatusBadge } from "@/components/shared/status-badge"
import { PageHeader } from "@/components/shared/page-header"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"
import type { ModuleLeaderAssignment } from "../course-types"

// ── Types ──────────────────────────────────────────────────────────────────────

type TermCalendarEntry = {
  term_number: number
  academic_term_id: string
  name: string
  year: number
  season: string
  status: string
}

type Batch = {
  id: string
  name: string
  term_calendar: TermCalendarEntry[]
}

type OfferingInfo = {
  id: string
  section_id: string
  section_name: string
  capacity: number | null
  status: string
}

type OfferingCourse = {
  course_id: string
  offerings: OfferingInfo[]
}

type FacultyAssignment = {
  id: string
  section_offering_id: string
  user_id: string
  role_in_course: string
  assigned_at: string
  removed_at: string | null
}

type FacultyRosterEntry = {
  id: string
  full_name: string
  faculty_type: string | null
}

type SectionDependents = {
  enrolled_students: number
  assessments: number
  marksheet_questions: number
  student_marks: number
  result_publications: number
  course_end_reports: number
  co_attainment_results: number
  po_attainment_results: number
  faculty_assignments: number
  total: number
  has_dependents: boolean
}

const DEPENDENT_LABELS: { key: keyof SectionDependents; label: string }[] = [
  { key: "enrolled_students", label: "enrolled student(s)" },
  { key: "assessments", label: "assessment(s)" },
  { key: "marksheet_questions", label: "marksheet question(s)" },
  { key: "student_marks", label: "recorded mark(s)" },
  { key: "result_publications", label: "result publication(s)" },
  { key: "course_end_reports", label: "course end report(s)" },
  { key: "co_attainment_results", label: "CO attainment result(s)" },
  { key: "po_attainment_results", label: "PO attainment result(s)" },
  { key: "faculty_assignments", label: "faculty assignment(s)" },
]

const NEXT_SECTION_LABEL = (count: number) => String.fromCharCode(65 + count) // A, B, C…

// ── Delete section (with cascade confirmation) ─────────────────────────────────

function DeleteSectionDialog({
  offering,
  batchId,
  termId,
}: {
  offering: OfferingInfo
  batchId: string
  termId: string
}) {
  const qc = useQueryClient()
  const [open, setOpen] = useState(false)
  // null while no data has data; "summary" → first warning, "final" → last confirm
  const [stage, setStage] = useState<"summary" | "final">("summary")

  const { data: dependents, isLoading } = useQuery({
    queryKey: queryKeys.sectionOfferings.dependents(offering.id),
    queryFn: async () => {
      const { data } = await apiClient.GET(
        `/section-offerings/${offering.id}/dependents` as never
      )
      return (data as unknown) as SectionDependents
    },
    enabled: open,
  })

  const deleteMutation = useMutation({
    mutationFn: async (cascade: boolean) => {
      await apiClient.DELETE(`/section-offerings/${offering.id}` as never, {
        params: { query: { cascade } },
      } as never)
    },
    onSuccess: () => {
      toast.success("Section removed")
      setOpen(false)
      qc.invalidateQueries({ queryKey: queryKeys.batches.termOfferings(batchId, termId) })
    },
    onError: (err: unknown) => {
      const msg = (err as { detail?: string })?.detail
      toast.error(msg ?? "Failed to remove section")
    },
  })

  const openDialog = () => {
    setStage("summary")
    setOpen(true)
  }

  const lines = dependents
    ? DEPENDENT_LABELS.filter(({ key }) => (dependents[key] as number) > 0).map(
        ({ key, label }) => `${dependents[key]} ${label}`
      )
    : []

  return (
    <>
      <button
        type="button"
        className="text-muted-foreground hover:text-destructive transition-colors"
        disabled={deleteMutation.isPending}
        title="Remove section"
        onClick={openDialog}
      >
        {deleteMutation.isPending ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
        ) : (
          <Trash2 className="h-3.5 w-3.5" />
        )}
      </button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          {isLoading ? (
            <div className="flex items-center gap-2 py-6 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Checking for related data…
            </div>
          ) : !dependents?.has_dependents ? (
            // No dependent data — single confirmation
            <>
              <DialogHeader>
                <DialogTitle>Remove Section {offering.section_name}?</DialogTitle>
                <DialogDescription>
                  This section has no related data. This action cannot be undone.
                </DialogDescription>
              </DialogHeader>
              <DialogFooter>
                <Button variant="outline" onClick={() => setOpen(false)}>
                  Cancel
                </Button>
                <Button
                  variant="destructive"
                  disabled={deleteMutation.isPending}
                  onClick={() => deleteMutation.mutate(false)}
                >
                  {deleteMutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
                  Remove section
                </Button>
              </DialogFooter>
            </>
          ) : stage === "summary" ? (
            // Has data — first warning listing what will be deleted
            <>
              <DialogHeader>
                <DialogTitle className="flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 text-destructive" />
                  Section {offering.section_name} has related data
                </DialogTitle>
                <DialogDescription>
                  Deleting this section will also permanently delete the following:
                </DialogDescription>
              </DialogHeader>
              <ul className="list-disc space-y-1 pl-5 text-sm">
                {lines.map((line) => (
                  <li key={line}>{line}</li>
                ))}
              </ul>
              <DialogFooter>
                <Button variant="outline" onClick={() => setOpen(false)}>
                  Cancel
                </Button>
                <Button variant="destructive" onClick={() => setStage("final")}>
                  Continue
                </Button>
              </DialogFooter>
            </>
          ) : (
            // Final confirmation
            <>
              <DialogHeader>
                <DialogTitle className="flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 text-destructive" />
                  Are you absolutely sure?
                </DialogTitle>
                <DialogDescription>
                  This will permanently delete Section {offering.section_name} and all{" "}
                  {dependents.total} related record(s), including any student marks and
                  results. This cannot be undone.
                </DialogDescription>
              </DialogHeader>
              <DialogFooter>
                <Button variant="outline" onClick={() => setStage("summary")}>
                  Go back
                </Button>
                <Button
                  variant="destructive"
                  disabled={deleteMutation.isPending}
                  onClick={() => deleteMutation.mutate(true)}
                >
                  {deleteMutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
                  Delete everything
                </Button>
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>
    </>
  )
}

// ── Add section control ───────────────────────────────────────────────────────

function AddSectionInline({
  existingCount,
  pending,
  onAdd,
}: {
  existingCount: number
  pending: boolean
  onAdd: (name: string) => void
}) {
  const [open, setOpen] = useState(false)
  const [name, setName] = useState("")
  const suggested = NEXT_SECTION_LABEL(existingCount)

  const submit = () => {
    const label = (name.trim() || suggested).toUpperCase()
    if (!label) return
    onAdd(label)
    setName("")
    setOpen(false)
  }

  if (!open) {
    return (
      <Button size="sm" variant="outline" className="h-7 text-xs gap-1" onClick={() => setOpen(true)}>
        <Plus className="h-3 w-3" />
        Add Section
      </Button>
    )
  }

  return (
    <div className="flex items-center gap-2">
      <Input
        autoFocus
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder={suggested}
        className="h-7 w-20 text-xs"
        maxLength={20}
        onKeyDown={(e) => {
          if (e.key === "Enter") submit()
          if (e.key === "Escape") setOpen(false)
        }}
      />
      <Button size="sm" className="h-7 text-xs" disabled={pending} onClick={submit}>
        {pending && <Loader2 className="h-3 w-3 animate-spin" />}
        Add
      </Button>
      <Button size="sm" variant="ghost" className="h-7 text-xs" onClick={() => setOpen(false)}>
        Cancel
      </Button>
    </div>
  )
}

// ── Assign section teacher control ──────────────────────────────────────────────

function AssignSectionTeacher({
  facultyUsers,
  pending,
  onAssign,
}: {
  facultyUsers: FacultyRosterEntry[]
  pending: boolean
  onAssign: (userId: string) => void
}) {
  const [userId, setUserId] = useState("")
  const options = facultyUsers.map((u) => ({ value: u.id, label: u.full_name }))

  return (
    <div className="flex items-center gap-2">
      <Combobox
        options={options}
        value={userId}
        onValueChange={setUserId}
        placeholder="Select teacher…"
        searchPlaceholder="Search faculty…"
        emptyText="No faculty found."
        triggerClassName="h-7 w-48 text-xs"
      />
      <Button
        size="sm"
        className="h-7 text-xs"
        disabled={!userId || pending}
        onClick={() => userId && onAssign(userId)}
      >
        {pending && <Loader2 className="h-3 w-3 animate-spin" />}
        Assign
      </Button>
    </div>
  )
}

// ── Section offering row ─────────────────────────────────────────────────────

function SectionOfferingRow({
  offering,
  batchId,
  termId,
  facultyUsers,
  userMap,
}: {
  offering: OfferingInfo
  batchId: string
  termId: string
  facultyUsers: FacultyRosterEntry[]
  userMap: Record<string, string>
}) {
  const qc = useQueryClient()
  const [pending, setPending] = useState(false)

  const { data: assignments = [], isLoading } = useQuery({
    queryKey: queryKeys.facultyAssignments.byOffering(offering.id),
    queryFn: async () => {
      const { data } = await apiClient.GET("/faculty-assignments" as never, {
        params: { query: { offering_id: offering.id } },
      } as never)
      return ((data as unknown) as FacultyAssignment[]) ?? []
    },
  })

  const teacher = assignments.find((a) => a.role_in_course === "SECTION_TEACHER")

  const invalidateAssignments = () =>
    qc.invalidateQueries({ queryKey: queryKeys.facultyAssignments.byOffering(offering.id) })

  const assignMutation = useMutation({
    mutationFn: async (userId: string) => {
      setPending(true)
      await apiClient.POST("/faculty-assignments" as never, {
        body: {
          section_offering_id: offering.id,
          user_id: userId,
          role_in_course: "SECTION_TEACHER",
        },
      } as never)
    },
    onSuccess: () => {
      toast.success("Section teacher assigned")
      invalidateAssignments()
    },
    onError: () => toast.error("Failed to assign section teacher"),
    onSettled: () => setPending(false),
  })

  const removeMutation = useMutation({
    mutationFn: async (assignmentId: string) => {
      setPending(true)
      await apiClient.DELETE(`/faculty-assignments/${assignmentId}` as never)
    },
    onSuccess: () => {
      toast.success("Section teacher removed")
      invalidateAssignments()
    },
    onError: () => toast.error("Failed to remove section teacher"),
    onSettled: () => setPending(false),
  })

  return (
    <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border bg-muted/30 px-3 py-2">
      <div className="flex items-center gap-2 text-sm">
        <span className="font-semibold">Section {offering.section_name}</span>
        {offering.capacity != null && (
          <span className="text-xs text-muted-foreground">cap {offering.capacity}</span>
        )}
        <StatusBadge status={offering.status} />
      </div>

      <div className="flex items-center gap-2">
        {isLoading ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground" />
        ) : teacher ? (
          <div className="flex items-center gap-1.5">
            <Badge variant="outline" className="gap-1.5 text-xs font-normal">
              <UserCog className="h-3 w-3" />
              {userMap[teacher.user_id] ?? "Unknown user"}
            </Badge>
            <button
              type="button"
              className="text-muted-foreground hover:text-destructive transition-colors"
              disabled={pending}
              title="Remove section teacher"
              onClick={() => removeMutation.mutate(teacher.id)}
            >
              {pending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <X className="h-3.5 w-3.5" />}
            </button>
          </div>
        ) : (
          <AssignSectionTeacher
            facultyUsers={facultyUsers}
            pending={pending}
            onAssign={(userId) => assignMutation.mutate(userId)}
          />
        )}

        <DeleteSectionDialog offering={offering} batchId={batchId} termId={termId} />
      </div>
    </div>
  )
}

// ── Per batch/semester group ─────────────────────────────────────────────────

function TermSectionGroup({
  courseId,
  batchId,
  batchName,
  term,
  facultyUsers,
  userMap,
}: {
  courseId: string
  batchId: string
  batchName: string
  term: TermCalendarEntry
  facultyUsers: FacultyRosterEntry[]
  userMap: Record<string, string>
}) {
  const qc = useQueryClient()

  const { data: courses = [], isLoading } = useQuery({
    queryKey: queryKeys.batches.termOfferings(batchId, term.academic_term_id),
    queryFn: async () => {
      const { data } = await apiClient.GET(
        `/batches/${batchId}/terms/${term.academic_term_id}/offerings` as never
      )
      return ((data as unknown) as OfferingCourse[]) ?? []
    },
  })

  const offerings = courses.find((c) => c.course_id === courseId)?.offerings ?? []

  const addMutation = useMutation({
    mutationFn: async (sectionName: string) => {
      await apiClient.POST(`/batches/${batchId}/terms/${term.academic_term_id}/offerings` as never, {
        body: { course_id: courseId, section_name: sectionName },
      } as never)
    },
    onSuccess: () => {
      toast.success("Section added")
      qc.invalidateQueries({ queryKey: queryKeys.batches.termOfferings(batchId, term.academic_term_id) })
    },
    onError: (err: unknown) => {
      const msg = (err as { detail?: string })?.detail
      toast.error(msg ?? "Failed to add section")
    },
  })

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <CardTitle className="text-sm font-medium">
            {batchName} — Semester {term.term_number} ({term.name})
          </CardTitle>
          <AddSectionInline
            existingCount={offerings.length}
            pending={addMutation.isPending}
            onAdd={(name) => addMutation.mutate(name)}
          />
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="h-12 animate-pulse bg-muted rounded-md" />
        ) : offerings.length === 0 ? (
          <p className="text-xs text-muted-foreground italic">
            No sections created yet. Use &quot;Add Section&quot; to create one.
          </p>
        ) : (
          <div className="space-y-2">
            {offerings.map((o) => (
              <SectionOfferingRow
                key={o.id}
                offering={o}
                batchId={batchId}
                termId={term.academic_term_id}
                facultyUsers={facultyUsers}
                userMap={userMap}
              />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

interface Props {
  courseId: string
}

export function CourseSectionsClient({ courseId }: Props) {
  const {
    data: myAssignments = [],
    isLoading: loadingAssignments,
    isError: assignmentsErrored,
    refetch: refetchAssignments,
  } = useQuery({
    queryKey: queryKeys.moduleLeaderAssignments.mine,
    queryFn: async () => {
      const { data } = await apiClient.GET("/module-leader-assignments/mine" as never)
      return ((data as unknown) as ModuleLeaderAssignment[]) ?? []
    },
  })

  const {
    data: batches = [],
    isLoading: loadingBatches,
    isError: batchesErrored,
    refetch: refetchBatches,
  } = useQuery({
    queryKey: queryKeys.batches.all,
    queryFn: async () => {
      const { data } = await apiClient.GET("/batches" as never)
      return ((data as unknown) as Batch[]) ?? []
    },
  })

  const { data: facultyUsers = [] } = useQuery({
    queryKey: queryKeys.users.facultyRoster,
    queryFn: async () => {
      const { data } = await apiClient.GET("/users/faculty-roster" as never)
      return ((data as unknown) as FacultyRosterEntry[]) ?? []
    },
  })

  const userMap = Object.fromEntries(facultyUsers.map((u) => [u.id, u.full_name]))

  const groups = myAssignments
    .filter((a) => a.course_id === courseId)
    .map((a) => {
      const batch = batches.find((b) => b.id === a.batch_id)
      const term = batch?.term_calendar.find((t) => t.academic_term_id === a.academic_term_id)
      if (!batch || !term) return null
      return { batch, term }
    })
    .filter((g): g is { batch: Batch; term: TermCalendarEntry } => g !== null)

  const isLoading = loadingAssignments || loadingBatches
  const hasError = assignmentsErrored || batchesErrored

  return (
    <div className="max-w-3xl space-y-6">
      <PageHeader
        title="Sections"
        description="Create section offerings for this course and assign a section teacher to each."
      />

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 2 }).map((_, i) => (
            <div key={i} className="h-24 animate-pulse bg-muted rounded-lg" />
          ))}
        </div>
      ) : hasError ? (
        <Card>
          <CardContent className="py-12 text-center space-y-3">
            <p className="text-sm text-muted-foreground">
              Couldn&apos;t load your module leader assignments. Please try again.
            </p>
            <Button
              size="sm"
              variant="outline"
              onClick={() => {
                refetchAssignments()
                refetchBatches()
              }}
            >
              Retry
            </Button>
          </CardContent>
        </Card>
      ) : groups.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            You are not the module leader for this course in any batch/semester.
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {groups.map(({ batch, term }) => (
            <TermSectionGroup
              key={`${batch.id}-${term.academic_term_id}`}
              courseId={courseId}
              batchId={batch.id}
              batchName={batch.name}
              term={term}
              facultyUsers={facultyUsers}
              userMap={userMap}
            />
          ))}
        </div>
      )}
    </div>
  )
}
