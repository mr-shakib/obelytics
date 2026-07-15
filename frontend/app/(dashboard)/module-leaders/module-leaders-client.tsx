"use client"

import { useMemo, useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { Loader2, UserCog, X, BookOpen } from "lucide-react"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select"
import { Combobox } from "@/components/ui/combobox"
import { PageHeader } from "@/components/shared/page-header"
import { usePermission } from "@/hooks/use-permission"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"

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
  status: string
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
  code: string
  title: string
  credits: number
  is_elective: boolean
  offerings: OfferingInfo[]
}

type ModuleLeaderAssignment = {
  id: string
  organization_id: string
  batch_id: string
  academic_term_id: string
  course_id: string
  user_id: string
  assigned_at: string
  removed_at: string | null
}

type User = {
  id: string
  full_name: string
  employee_id?: string | null
  faculty_type: string | null
  status: string
}

function userDisplayLabel(user: User) {
  return user.employee_id ? `${user.employee_id} - ${user.full_name}` : user.full_name
}

// ── Assign control ────────────────────────────────────────────────────────────

function AssignModuleLeader({
  facultyUsers,
  onAssign,
  pending,
}: {
  facultyUsers: User[]
  onAssign: (userId: string) => void
  pending: boolean
}) {
  const [userId, setUserId] = useState<string>("")
  const options = useMemo(
    () => facultyUsers.map((u) => ({ value: u.id, label: userDisplayLabel(u) })),
    [facultyUsers]
  )

  return (
    <div className="flex items-center gap-2">
      <Combobox
        options={options}
        value={userId}
        onValueChange={setUserId}
        placeholder="Select faculty…"
        searchPlaceholder="Search faculty…"
        emptyText="No faculty found."
        className="[&_[cmdk-item]]:whitespace-nowrap"
        triggerClassName="h-8 w-64 text-xs"
      />
      <Button
        size="sm"
        className="h-8 text-xs"
        disabled={!userId || pending}
        onClick={() => userId && onAssign(userId)}
      >
        {pending && <Loader2 className="h-3 w-3 animate-spin" />}
        Assign
      </Button>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export function ModuleLeadersClient() {
  const qc = useQueryClient()
  const canManage = usePermission("faculty_assignment.create")

  const [batchId, setBatchId] = useState<string>("")
  const [termId, setTermId] = useState<string>("")

  const { data: batches = [], isLoading: loadingBatches } = useQuery({
    queryKey: queryKeys.batches.all,
    queryFn: async () => {
      const { data } = await apiClient.GET("/batches" as never)
      return ((data as unknown) as Batch[]) ?? []
    },
  })

  const selectedBatch = batches.find((b) => b.id === batchId)
  // Only semesters that have been started (ACTIVE or COMPLETED) are offered —
  // module leaders are not assigned for semesters that haven't begun.
  const terms = useMemo(
    () => (selectedBatch?.term_calendar ?? []).filter((t) => t.status !== "UPCOMING"),
    [selectedBatch]
  )

  const batchItems = useMemo(
    () => Object.fromEntries(batches.map((b) => [b.id, b.name])),
    [batches]
  )
  const termItems = useMemo(
    () => Object.fromEntries(
      terms.map((t) => [t.academic_term_id, `Semester ${t.term_number} — ${t.name}`])
    ),
    [terms]
  )

  const { data: courses = [], isLoading: loadingCourses } = useQuery({
    queryKey: queryKeys.batches.termOfferings(batchId, termId),
    queryFn: async () => {
      const { data } = await apiClient.GET(
        `/batches/${batchId}/terms/${termId}/offerings` as never
      )
      return ((data as unknown) as OfferingCourse[]) ?? []
    },
    enabled: !!batchId && !!termId,
  })

  const { data: users = [] } = useQuery({
    queryKey: queryKeys.users.list(),
    queryFn: async () => {
      const { data } = await apiClient.GET("/users" as never)
      return ((data as unknown) as User[]) ?? []
    },
  })

  const facultyUsers = useMemo(
    () => users.filter((u) => u.faculty_type && u.status === "ACTIVE"),
    [users]
  )
  const userMap = useMemo(
    () => Object.fromEntries(users.map((u) => [u.id, userDisplayLabel(u)])),
    [users]
  )

  const { data: assignments = [], isLoading: loadingAssignments } = useQuery({
    queryKey: queryKeys.moduleLeaderAssignments.byBatchTerm(batchId, termId),
    queryFn: async () => {
      const { data } = await apiClient.GET("/module-leader-assignments" as never, {
        params: { query: { batch_id: batchId, academic_term_id: termId } },
      } as never)
      return ((data as unknown) as ModuleLeaderAssignment[]) ?? []
    },
    enabled: !!batchId && !!termId,
  })

  const assignmentByCourse = useMemo(
    () => Object.fromEntries(assignments.map((a) => [a.course_id, a])),
    [assignments]
  )

  const invalidateAssignments = () =>
    qc.invalidateQueries({ queryKey: queryKeys.moduleLeaderAssignments.byBatchTerm(batchId, termId) })

  const [pendingCourse, setPendingCourse] = useState<string | null>(null)

  const assignMutation = useMutation({
    mutationFn: async ({ course, userId }: { course: OfferingCourse; userId: string }) => {
      setPendingCourse(course.course_id)
      await apiClient.POST("/module-leader-assignments" as never, {
        body: {
          batch_id: batchId,
          academic_term_id: termId,
          course_id: course.course_id,
          user_id: userId,
        },
      } as never)
    },
    onSuccess: () => {
      toast.success("Module leader assigned")
      invalidateAssignments()
    },
    onError: () => toast.error("Failed to assign module leader"),
    onSettled: () => setPendingCourse(null),
  })

  const removeMutation = useMutation({
    mutationFn: async ({ course, assignmentId }: { course: OfferingCourse; assignmentId: string }) => {
      setPendingCourse(course.course_id)
      await apiClient.DELETE(`/module-leader-assignments/${assignmentId}` as never)
    },
    onSuccess: () => {
      toast.success("Module leader removed")
      invalidateAssignments()
    },
    onError: () => toast.error("Failed to remove module leader"),
    onSettled: () => setPendingCourse(null),
  })

  return (
    <div className="max-w-5xl space-y-6">
      <PageHeader
        title="Module Leaders"
        description="Assign a module leader to each course offered to a batch in a given semester."
      />

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <Select
          items={batchItems}
          value={batchId}
          onValueChange={(v) => {
            if (v == null) return
            setBatchId(v as string)
            setTermId("")
          }}
        >
          <SelectTrigger className="w-64">
            <SelectValue placeholder={loadingBatches ? "Loading…" : "Select batch"} />
          </SelectTrigger>
          <SelectContent>
            {batches.map((b) => (
              <SelectItem key={b.id} value={b.id}>{b.name}</SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select
          items={termItems}
          value={termId}
          onValueChange={(v) => v != null && setTermId(v as string)}
          disabled={!batchId}
        >
          <SelectTrigger className="w-64">
            <SelectValue placeholder="Select semester" />
          </SelectTrigger>
          <SelectContent>
            {terms.map((t) => (
              <SelectItem key={t.academic_term_id} value={t.academic_term_id}>
                Semester {t.term_number} — {t.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {batchId && terms.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            No semester of this batch has been started yet. Start a semester from
            the batch page to assign module leaders for its courses.
          </CardContent>
        </Card>
      ) : !batchId || !termId ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            Select a batch and semester to view its courses.
          </CardContent>
        </Card>
      ) : loadingCourses || loadingAssignments ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-20 animate-pulse bg-muted rounded-lg" />
          ))}
        </div>
      ) : courses.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            No courses assigned to this semester in the curriculum.
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {courses.map((course) => {
            const ml = assignmentByCourse[course.course_id]
            const isPending = pendingCourse === course.course_id

            return (
              <Card key={course.course_id}>
                <CardHeader className="pb-2">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <BookOpen className="h-4 w-4 text-muted-foreground shrink-0" />
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-sm font-semibold">{course.code}</span>
                        <span className="text-sm font-medium">{course.title}</span>
                        {course.is_elective ? (
                          <Badge variant="outline" className="text-xs">Elective</Badge>
                        ) : (
                          <Badge variant="secondary" className="text-xs">Core</Badge>
                        )}
                      </div>
                    </div>

                    {ml ? (
                      <div className="flex items-center gap-2">
                        <Badge variant="outline" className="gap-1.5 text-xs font-normal">
                          <UserCog className="h-3 w-3" />
                          <span className="max-w-64 truncate whitespace-nowrap">
                            {userMap[ml.user_id] ?? "Unknown user"}
                          </span>
                        </Badge>
                        {canManage && (
                          <button
                            type="button"
                            className="text-muted-foreground hover:text-destructive transition-colors"
                            disabled={isPending}
                            title="Remove module leader"
                            onClick={() => removeMutation.mutate({ course, assignmentId: ml.id })}
                          >
                            {isPending ? (
                              <Loader2 className="h-3.5 w-3.5 animate-spin" />
                            ) : (
                              <X className="h-3.5 w-3.5" />
                            )}
                          </button>
                        )}
                      </div>
                    ) : canManage ? (
                      <AssignModuleLeader
                        facultyUsers={facultyUsers}
                        pending={isPending && assignMutation.isPending}
                        onAssign={(userId) => assignMutation.mutate({ course, userId })}
                      />
                    ) : (
                      <span className="text-xs text-muted-foreground">Not assigned</span>
                    )}
                  </div>
                </CardHeader>

                {course.offerings.length > 0 && (
                  <CardContent>
                    <div className="flex flex-wrap gap-2">
                      {course.offerings.map((o) => (
                        <Badge key={o.id} variant="outline" className="text-xs font-normal">
                          Section {o.section_name}
                        </Badge>
                      ))}
                    </div>
                  </CardContent>
                )}
              </Card>
            )
          })}
        </div>
      )}
    </div>
  )
}
