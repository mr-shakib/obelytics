"use client"

import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useForm, Controller } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { toast } from "sonner"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { Loader2, ChevronDown, ChevronRight, BookOpen, Play, CheckCircle, Settings2, Plus, Upload, Users, Pencil, Trash2 } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { PageHeader } from "@/components/shared/page-header"
import { StatusBadge } from "@/components/shared/status-badge"
import { PermissionGate } from "@/components/shared/permission-gate"
import { usePermission } from "@/hooks/use-permission"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
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
import { useAuthStore } from "@/lib/stores/auth-store"
import { formatDate } from "@/lib/utils"

type Student = {
  id: string
  student_id_number: string
  full_name: string
  email: string | null
  batch_id: string
  status: string
}

const studentFormSchema = z.object({
  student_id_number: z.string().min(1, "Student ID is required"),
  full_name: z.string().min(1, "Name is required"),
  email: z.union([z.string().email("Enter a valid email"), z.literal("")]).optional(),
})
type StudentFormValues = z.infer<typeof studentFormSchema>

function BatchStudentsCard({ batchId }: { batchId: string }) {
  const qc = useQueryClient()
  const router = useRouter()
  const canManage = usePermission("assessment.configure")
  const [addOpen, setAddOpen] = useState(false)
  const [editStudent, setEditStudent] = useState<Student | null>(null)
  const [deleteStudent, setDeleteStudent] = useState<Student | null>(null)

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: queryKeys.students.list({ batch_id: batchId }) })
    qc.invalidateQueries({ queryKey: queryKeys.students.all })
  }

  const { data: students = [], isLoading } = useQuery({
    queryKey: queryKeys.students.list({ batch_id: batchId }),
    queryFn: async () => {
      const { data } = await apiClient.GET("/students" as never, {
        params: { query: { batch_id: batchId } },
      } as never)
      return ((data as unknown) as Student[]) ?? []
    },
  })

  // ── Add form ──
  const addForm = useForm<StudentFormValues>({ resolver: zodResolver(studentFormSchema) })
  const addMutation = useMutation({
    mutationFn: async (values: StudentFormValues) => {
      await apiClient.POST("/students" as never, {
        body: { student_id_number: values.student_id_number, full_name: values.full_name, email: values.email || null, batch_id: batchId },
      } as never)
    },
    onSuccess: () => { toast.success("Student added"); invalidate(); addForm.reset(); setAddOpen(false) },
    onError: () => toast.error("Failed to add student"),
  })

  // ── Edit form ──
  const editForm = useForm<StudentFormValues>({ resolver: zodResolver(studentFormSchema) })
  const editMutation = useMutation({
    mutationFn: async (values: StudentFormValues) => {
      await apiClient.PATCH(`/students/${editStudent!.id}` as never, {
        body: { student_id_number: values.student_id_number, full_name: values.full_name, email: values.email || null },
      } as never)
    },
    onSuccess: () => { toast.success("Student updated"); invalidate(); setEditStudent(null) },
    onError: () => toast.error("Failed to update student"),
  })

  // ── Delete ──
  const deleteMutation = useMutation({
    mutationFn: async () => {
      await apiClient.DELETE(`/students/${deleteStudent!.id}` as never, {} as never)
    },
    onSuccess: () => { toast.success("Student removed"); invalidate(); setDeleteStudent(null) },
    onError: () => toast.error("Failed to remove student"),
  })

  return (
    <>
    {/* Edit dialog */}
    <Dialog open={!!editStudent} onOpenChange={(v) => { if (!v) setEditStudent(null) }}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader><DialogTitle>Edit Student</DialogTitle></DialogHeader>
        <form id="edit-student-form" onSubmit={editForm.handleSubmit((v) => editMutation.mutate(v))} className="space-y-4 py-2">
          <div className="space-y-2">
            <Label htmlFor="es-id">Student ID</Label>
            <Input id="es-id" {...editForm.register("student_id_number")} />
            {editForm.formState.errors.student_id_number && <p className="text-sm text-destructive">{editForm.formState.errors.student_id_number.message}</p>}
          </div>
          <div className="space-y-2">
            <Label htmlFor="es-name">Full Name</Label>
            <Input id="es-name" {...editForm.register("full_name")} />
            {editForm.formState.errors.full_name && <p className="text-sm text-destructive">{editForm.formState.errors.full_name.message}</p>}
          </div>
          <div className="space-y-2">
            <Label htmlFor="es-email">Email (optional)</Label>
            <Input id="es-email" type="email" {...editForm.register("email")} />
            {editForm.formState.errors.email && <p className="text-sm text-destructive">{editForm.formState.errors.email.message}</p>}
          </div>
        </form>
        <DialogFooter>
          <Button variant="outline" onClick={() => setEditStudent(null)} disabled={editMutation.isPending}>Cancel</Button>
          <Button type="submit" form="edit-student-form" disabled={editMutation.isPending}>
            {editMutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
            Save
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    {/* Delete confirmation dialog */}
    <Dialog open={!!deleteStudent} onOpenChange={(v) => { if (!v) setDeleteStudent(null) }}>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader><DialogTitle>Remove Student</DialogTitle></DialogHeader>
        <p className="text-sm text-muted-foreground py-2">
          Remove <span className="font-medium text-foreground">{deleteStudent?.full_name}</span> ({deleteStudent?.student_id_number}) from this batch? This cannot be undone.
        </p>
        <DialogFooter>
          <Button variant="outline" onClick={() => setDeleteStudent(null)} disabled={deleteMutation.isPending}>Cancel</Button>
          <Button variant="destructive" onClick={() => deleteMutation.mutate()} disabled={deleteMutation.isPending}>
            {deleteMutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
            Remove
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span className="flex items-center gap-2">
            <Users className="h-4 w-4" />
            Students
            {students.length > 0 && (
              <Badge variant="secondary" className="text-xs">{students.length}</Badge>
            )}
          </span>
          <PermissionGate permission="assessment.configure">
            <div className="flex items-center gap-2">
              <Button size="sm" variant="outline" onClick={() => router.push(`/students/import?batch_id=${batchId}`)}>
                <Upload className="h-3.5 w-3.5" />
                Bulk Import
              </Button>
              <Dialog open={addOpen} onOpenChange={(v) => { setAddOpen(v); if (!v) addForm.reset() }}>
                <DialogTrigger render={<Button size="sm" />}>
                  <Plus className="h-3.5 w-3.5" />
                  Add Student
                </DialogTrigger>
                <DialogContent className="sm:max-w-md">
                  <DialogHeader><DialogTitle>Add Student to Batch</DialogTitle></DialogHeader>
                  <form id="add-batch-student-form" onSubmit={addForm.handleSubmit((v) => addMutation.mutate(v))} className="space-y-4 py-2">
                    <div className="space-y-2">
                      <Label htmlFor="bs-student-id">Student ID</Label>
                      <Input id="bs-student-id" {...addForm.register("student_id_number")} placeholder="221-15-1234" />
                      {addForm.formState.errors.student_id_number && <p className="text-sm text-destructive">{addForm.formState.errors.student_id_number.message}</p>}
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="bs-full-name">Full Name</Label>
                      <Input id="bs-full-name" {...addForm.register("full_name")} placeholder="Jane Doe" />
                      {addForm.formState.errors.full_name && <p className="text-sm text-destructive">{addForm.formState.errors.full_name.message}</p>}
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="bs-email">Email (optional)</Label>
                      <Input id="bs-email" type="email" {...addForm.register("email")} placeholder="jane@example.com" />
                      {addForm.formState.errors.email && <p className="text-sm text-destructive">{addForm.formState.errors.email.message}</p>}
                    </div>
                  </form>
                  <DialogFooter>
                    <Button variant="outline" onClick={() => setAddOpen(false)} disabled={addMutation.isPending}>Cancel</Button>
                    <Button type="submit" form="add-batch-student-form" disabled={addMutation.isPending}>
                      {addMutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
                      Add
                    </Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            </div>
          </PermissionGate>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-2">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="h-9 animate-pulse bg-muted rounded" />
            ))}
          </div>
        ) : students.length === 0 ? (
          <p className="text-sm text-muted-foreground py-2 text-center">
            No students in this batch yet.
          </p>
        ) : (
          <div className="overflow-auto max-h-[520px]">
            <table className="w-full text-sm table-fixed">
              <thead className="sticky top-0 bg-card z-10">
                <tr className="border-b border-border text-muted-foreground text-xs uppercase">
                  <th className="w-[26%] py-2 pr-2 text-left font-medium">ID</th>
                  <th className="w-[28%] py-2 pr-2 text-left font-medium">Name</th>
                  <th className="py-2 pr-2 text-left font-medium">Email</th>
                  {canManage && <th className="w-[52px] py-2 text-right font-medium" />}
                </tr>
              </thead>
              <tbody>
                {students.map((s) => (
                  <tr key={s.id} className="border-b border-border/50 last:border-0 hover:bg-muted/40 group">
                    <td className="py-2.5 pr-2 font-mono text-xs max-w-0">
                      <span className="block truncate">{s.student_id_number}</span>
                    </td>
                    <td className="py-2.5 pr-2 max-w-0">
                      <span className="block truncate">{s.full_name}</span>
                    </td>
                    <td className="py-2.5 pr-2 text-muted-foreground max-w-0">
                      <span className="block truncate">{s.email ?? "—"}</span>
                    </td>
                    {canManage && (
                      <td className="py-2.5 text-right">
                        <div className="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                          <button
                            type="button"
                            className="h-6 w-6 flex items-center justify-center rounded hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
                            onClick={() => { editForm.reset({ student_id_number: s.student_id_number, full_name: s.full_name, email: s.email ?? "" }); setEditStudent(s) }}
                          >
                            <Pencil className="h-3.5 w-3.5" />
                          </button>
                          <button
                            type="button"
                            className="h-6 w-6 flex items-center justify-center rounded hover:bg-destructive/10 text-muted-foreground hover:text-destructive transition-colors"
                            onClick={() => setDeleteStudent(s)}
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
    </>
  )
}

type SemesterCourse = {
  course_id: string
  code: string
  title: string
  credits: number
  theory_hours: number
  lab_hours: number
  is_elective: boolean
}

type SemesterPlanItem = {
  term_number: number
  academic_term_id: string
  name: string
  year: number
  season: string
  start_date: string
  end_date: string
  status: string
  total_credits: number
  courses: SemesterCourse[]
}

type Batch = {
  id: string
  name: string
  curriculum_id: string
  intake_year: number | null
  start_date: string | null
  term_system: string | null
  num_semesters: number | null
  status: string
}

type Curriculum = {
  id: string
  name: string
  code: string
}

const schema = z.object({
  name: z.string().min(1, "Name is required"),
  curriculum_id: z.string().min(1, "Curriculum is required"),
})
type FormValues = z.infer<typeof schema>

interface Props {
  id: string
}

const SEASON_ACCENT: Record<string, { border: string; label: string }> = {
  SPRING: { border: "border-l-green-400",  label: "bg-green-100 text-green-800" },
  SUMMER: { border: "border-l-yellow-400", label: "bg-yellow-100 text-yellow-800" },
  FALL:   { border: "border-l-orange-400", label: "bg-orange-100 text-orange-800" },
  WINTER: { border: "border-l-blue-400",   label: "bg-blue-100 text-blue-800" },
}

function SemesterRow({
  item,
  batchId,
  canManage,
  onStatusChange,
  changingId,
}: {
  item: SemesterPlanItem
  batchId: string
  canManage: boolean
  onStatusChange: (termId: string, status: "ACTIVE" | "COMPLETED") => void
  changingId: string | null
}) {
  const [open, setOpen] = useState(false)
  const accent = SEASON_ACCENT[item.season] ?? { border: "border-l-muted", label: "" }
  const busy = changingId === item.academic_term_id

  return (
    <div className={`border-l-4 rounded-r-lg border border-border ${accent.border} overflow-hidden`}>
      <div className="flex items-center justify-between px-4 py-3 hover:bg-muted/50 transition-colors">
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="flex items-center gap-3 flex-1 text-left"
        >
          {open ? (
            <ChevronDown className="h-4 w-4 text-muted-foreground shrink-0" />
          ) : (
            <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0" />
          )}
          <div>
            <span className="font-medium text-sm">Semester {item.term_number}</span>
            <span className="text-muted-foreground text-sm ml-2">·</span>
            <span className="text-sm ml-2">{item.name}</span>
          </div>
          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${accent.label}`}>
            {item.season}
          </span>
        </button>

        <div className="flex items-center gap-3 text-sm text-muted-foreground">
          <span className="hidden sm:block">{formatDate(item.start_date)} – {formatDate(item.end_date)}</span>
          <span className="flex items-center gap-1">
            <BookOpen className="h-3.5 w-3.5" />
            {item.courses.length}
          </span>
          <span className="font-semibold text-foreground">{item.total_credits} cr</span>
          <StatusBadge status={item.status} />

          {canManage && item.status === "UPCOMING" && (
            <Button
              size="sm"
              variant="outline"
              className="h-7 text-xs gap-1"
              disabled={busy}
              onClick={() => onStatusChange(item.academic_term_id, "ACTIVE")}
            >
              {busy ? <Loader2 className="h-3 w-3 animate-spin" /> : <Play className="h-3 w-3" />}
              Start
            </Button>
          )}
          {canManage && item.status === "ACTIVE" && (
            <Button
              size="sm"
              variant="outline"
              className="h-7 text-xs gap-1"
              disabled={busy}
              onClick={() => onStatusChange(item.academic_term_id, "COMPLETED")}
            >
              {busy ? <Loader2 className="h-3 w-3 animate-spin" /> : <CheckCircle className="h-3 w-3" />}
              Complete
            </Button>
          )}
          <Link
            href={`/batches/${batchId}/terms/${item.academic_term_id}`}
            className="inline-flex items-center gap-1 h-7 px-2 text-xs rounded-md border border-border hover:bg-muted transition-colors"
            onClick={(e) => e.stopPropagation()}
          >
            <Settings2 className="h-3 w-3" />
            Sections
          </Link>
        </div>
      </div>

      {open && (
        <div className="border-t border-border bg-muted/20">
          {item.courses.length === 0 ? (
            <p className="px-6 py-3 text-sm text-muted-foreground italic">
              No courses assigned to this semester in the curriculum.
            </p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-muted-foreground text-xs uppercase">
                  <th className="px-6 py-2 text-left font-medium">Code</th>
                  <th className="px-4 py-2 text-left font-medium">Title</th>
                  <th className="px-4 py-2 text-center font-medium">Credits</th>
                  <th className="px-4 py-2 text-center font-medium">Theory</th>
                  <th className="px-4 py-2 text-center font-medium">Lab</th>
                  <th className="px-4 py-2 text-left font-medium">Type</th>
                </tr>
              </thead>
              <tbody>
                {item.courses.map((c) => (
                  <tr key={c.course_id} className="border-b border-border/50 last:border-0 hover:bg-muted/40">
                    <td className="px-6 py-2.5 font-mono font-medium">{c.code}</td>
                    <td className="px-4 py-2.5">{c.title}</td>
                    <td className="px-4 py-2.5 text-center">{c.credits}</td>
                    <td className="px-4 py-2.5 text-center text-muted-foreground">{c.theory_hours}h</td>
                    <td className="px-4 py-2.5 text-center text-muted-foreground">{c.lab_hours}h</td>
                    <td className="px-4 py-2.5">
                      {c.is_elective ? (
                        <Badge variant="outline" className="text-xs">Elective</Badge>
                      ) : (
                        <Badge variant="secondary" className="text-xs">Core</Badge>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr className="bg-muted/30">
                  <td colSpan={2} className="px-6 py-2 text-xs text-muted-foreground">Total</td>
                  <td className="px-4 py-2 text-center font-semibold text-sm">{item.total_credits}</td>
                  <td colSpan={3} />
                </tr>
              </tfoot>
            </table>
          )}
        </div>
      )}
    </div>
  )
}

export function BatchDetailClient({ id }: Props) {
  const qc = useQueryClient()
  const router = useRouter()
  const canManage = usePermission("curriculum.update")
  const { manifest } = useAuthStore()
  const isSuperAdmin = manifest?.scope.is_global ?? false
  const [changingTermId, setChangingTermId] = useState<string | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.batches.detail(id),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/batches/${id}` as never)
      return (data as unknown) as Batch
    },
  })

  const { data: semesterPlan = [], isLoading: planLoading } = useQuery({
    queryKey: queryKeys.batches.semesterPlan(id),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/batches/${id}/semester-plan` as never)
      return ((data as unknown) as SemesterPlanItem[]) ?? []
    },
    enabled: !!data,
  })

  const { data: curricula = [] } = useQuery({
    queryKey: queryKeys.curricula.all,
    queryFn: async () => {
      const { data } = await apiClient.GET("/curricula" as never)
      return ((data as unknown) as Curriculum[]) ?? []
    },
  })

  const {
    register,
    handleSubmit,
    control,
    formState: { errors, isSubmitting, isDirty },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    values: data ? { name: data.name, curriculum_id: data.curriculum_id } : undefined,
  })

  const batchMutation = useMutation({
    mutationFn: async (values: FormValues) => {
      await apiClient.PATCH(`/batches/${id}` as never, { body: values } as never)
    },
    onSuccess: (_, values) => {
      toast.success(
        values.curriculum_id !== data?.curriculum_id
          ? "Batch updated — semester plan now reflects the new curriculum"
          : "Batch updated"
      )
      qc.invalidateQueries({ queryKey: queryKeys.batches.detail(id) })
      qc.invalidateQueries({ queryKey: queryKeys.batches.all })
      qc.invalidateQueries({ queryKey: queryKeys.batches.semesterPlan(id) })
    },
    onError: () => toast.error("Failed to update batch"),
  })

  const statusMutation = useMutation({
    mutationFn: async ({ termId, status }: { termId: string; status: string }) => {
      setChangingTermId(termId)
      await apiClient.PATCH(`/academic-terms/${termId}` as never, { body: { status } } as never)
    },
    onSuccess: (_, { status }) => {
      const label = status === "ACTIVE" ? "started" : "completed"
      toast.success(`Semester ${label}`)
      qc.invalidateQueries({ queryKey: queryKeys.batches.semesterPlan(id) })
      qc.invalidateQueries({ queryKey: queryKeys.academicTerms.all })
    },
    onError: () => toast.error("Failed to update semester status"),
    onSettled: () => setChangingTermId(null),
  })

  const deleteMutation = useMutation({
    mutationFn: async () => {
      await apiClient.DELETE(`/batches/${id}` as never)
    },
    onSuccess: () => {
      toast.success("Batch deleted")
      qc.invalidateQueries({ queryKey: queryKeys.batches.all })
      router.push("/batches")
    },
  })

  if (isLoading) return <div className="animate-pulse h-40 bg-muted rounded-md" />
  if (!data) return <p className="text-muted-foreground">Batch not found.</p>

  const totalCreditsAll = semesterPlan.reduce((s, t) => s + t.total_credits, 0)

  return (
    <div className="space-y-6">
      <PageHeader
        title={data.name}
        description={[
          data.term_system,
          data.num_semesters ? `${data.num_semesters} semesters` : null,
          data.start_date ? `from ${data.start_date.slice(0, 7)}` : null,
        ].filter(Boolean).join(" · ")}
        actions={
          <div className="flex items-center gap-2">
            <StatusBadge status={data.status} />
            {isSuperAdmin && (
              <Button
                variant="destructive"
                size="sm"
                disabled={deleteMutation.isPending}
                onClick={() => {
                  if (window.confirm(`Permanently delete "${data.name}"? This cannot be undone.`))
                    deleteMutation.mutate()
                }}
              >
                {deleteMutation.isPending ? <Loader2 className="animate-spin" /> : <Trash2 className="h-4 w-4" />}
                Delete
              </Button>
            )}
          </div>
        }
      />

      {/* Summary strip */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: "Term System",     value: data.term_system ?? "—" },
          { label: "Total Semesters", value: data.num_semesters ?? "—" },
          { label: "Total Credits",   value: totalCreditsAll || "—" },
        ].map(({ label, value }) => (
          <Card key={label} className="py-4">
            <CardContent className="text-center">
              <p className="text-2xl font-bold">{value}</p>
              <p className="text-xs text-muted-foreground mt-1">{label}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Main 2-column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">

        {/* Left — Semester plan */}
        <div>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>Semester Plan</span>
                <span className="text-sm font-normal text-muted-foreground">
                  Click a semester to see its courses
                </span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {planLoading ? (
                <div className="space-y-2">
                  {Array.from({ length: 4 }).map((_, i) => (
                    <div key={i} className="h-12 animate-pulse bg-muted rounded-lg" />
                  ))}
                </div>
              ) : semesterPlan.length === 0 ? (
                <p className="text-sm text-muted-foreground py-4 text-center">
                  No semester calendar generated yet.
                </p>
              ) : (
                semesterPlan.map((item) => (
                  <SemesterRow
                    key={item.term_number}
                    item={item}
                    batchId={id}
                    canManage={canManage}
                    onStatusChange={(termId, status) => statusMutation.mutate({ termId, status })}
                    changingId={changingTermId}
                  />
                ))
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right — Edit batch name + Students */}
        <div className="space-y-4">
          <PermissionGate permission="batch.create">
            <Card>
              <CardHeader><CardTitle>Edit Batch</CardTitle></CardHeader>
              <CardContent>
                <form onSubmit={handleSubmit((v) => batchMutation.mutate(v))} className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="name">Batch Name</Label>
                    <Input id="name" {...register("name")} />
                    {errors.name && <p className="text-sm text-destructive">{errors.name.message}</p>}
                  </div>
                  <div className="space-y-2">
                    <Label>Curriculum</Label>
                    <Controller
                      name="curriculum_id"
                      control={control}
                      render={({ field }) => (
                        <Select value={field.value ?? ""} onValueChange={field.onChange}>
                          <SelectTrigger className="w-full">
                            <SelectValue placeholder="Select curriculum">
                              {(value: string) => {
                                const c = curricula.find((c) => c.id === value)
                                return c ? c.name : value
                              }}
                            </SelectValue>
                          </SelectTrigger>
                          <SelectContent>
                            {curricula.map((c) => (
                              <SelectItem key={c.id} value={c.id}>
                                {c.name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      )}
                    />
                    {errors.curriculum_id && <p className="text-sm text-destructive">{errors.curriculum_id.message}</p>}
                    <p className="text-xs text-muted-foreground">
                      Switching curriculum updates the semester plan (terms/courses) to match the new curriculum.
                    </p>
                  </div>
                  <Button type="submit" disabled={!isDirty || isSubmitting || batchMutation.isPending}>
                    {(isSubmitting || batchMutation.isPending) && <Loader2 className="animate-spin" />}
                    Save Changes
                  </Button>
                </form>
              </CardContent>
            </Card>
          </PermissionGate>

          <BatchStudentsCard batchId={id} />
        </div>

      </div>
    </div>
  )
}
