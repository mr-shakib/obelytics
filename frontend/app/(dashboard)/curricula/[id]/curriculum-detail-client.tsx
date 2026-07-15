"use client"

import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { toast } from "sonner"
import { Loader2, Plus, Archive, Trash2 } from "lucide-react"
import { useRouter } from "next/navigation"
import type { ColumnDef } from "@tanstack/react-table"

import { PageHeader } from "@/components/shared/page-header"
import { DataTable } from "@/components/shared/data-table"
import { PermissionGate } from "@/components/shared/permission-gate"
import { ConfirmDialog } from "@/components/shared/confirm-dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
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

type Curriculum = {
  id: string
  program_id: string
  name: string
  effective_year: number
  version_number: number
  status: string
}

type Program = { id: string; title?: string; name?: string; acronym?: string }

function programLabel(p: Program) {
  const title = p.title ?? p.name ?? ""
  return p.acronym ? `${p.acronym} — ${title}` : title || p.id
}

type TermDefinition = {
  id: string
  term_number: number
  name: string
  total_credit_hours: number | null
}

type CourseSlot = {
  id: string
  curriculum_term_definition_id: string
  course_id: string
}

type Course = {
  id: string
  code: string
  title: string
  credits: number
}

const editSchema = z.object({
  name: z.string().min(1, "Name is required").max(255),
})
type EditValues = z.infer<typeof editSchema>

const addTermSchema = z.object({
  term_number: z.number().int().min(1).max(20),
  name: z.string().min(1, "Name is required").max(100),
  total_credit_hours: z.number().int().min(0).optional(),
})
type AddTermValues = z.infer<typeof addTermSchema>

const addCourseSlotSchema = z.object({
  curriculum_term_definition_id: z.string().min(1, "Semester is required"),
  course_id: z.string().min(1, "Course is required"),
})
type AddCourseSlotValues = z.infer<typeof addCourseSlotSchema>

interface Props {
  id: string
}

export function CurriculumDetailClient({ id }: Props) {
  const [addTermOpen, setAddTermOpen] = useState(false)
  const [addSlotOpen, setAddSlotOpen] = useState(false)
  const qc = useQueryClient()
  const router = useRouter()
  const { manifest } = useAuthStore()
  const isSuperAdmin = manifest?.scope.is_global ?? false

  const deleteMutation = useMutation({
    mutationFn: async () => {
      const { error, response } = await apiClient.DELETE(`/curricula/${id}` as never)
      if (response && !response.ok) {
        const detail = (error as { detail?: string } | undefined)?.detail
        throw new Error(detail ?? "Failed to delete curriculum")
      }
    },
    onSuccess: () => {
      toast.success("Curriculum deleted")
      qc.invalidateQueries({ queryKey: queryKeys.curricula.all })
      router.push("/curricula")
    },
    onError: (err: Error) => toast.error(err.message),
  })

  const { data: curriculum, isLoading } = useQuery({
    queryKey: queryKeys.curricula.detail(id),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/curricula/${id}` as never)
      return (data as unknown) as Curriculum
    },
  })

  const { data: programs = [] } = useQuery({
    queryKey: queryKeys.programs.all,
    queryFn: async () => {
      const { data } = await apiClient.GET("/programs" as never)
      return ((data as unknown) as Program[]) ?? []
    },
  })
  const programById = Object.fromEntries(programs.map((p) => [p.id, p]))

  const { data: terms = [], isLoading: termsLoading } = useQuery({
    queryKey: queryKeys.curricula.terms(id),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/curricula/${id}/terms` as never)
      return ((data as unknown) as TermDefinition[]) ?? []
    },
  })
  const termById = Object.fromEntries(terms.map((t) => [t.id, t]))
  const sortedTerms = [...terms].sort((a, b) => a.term_number - b.term_number)

  const { data: slots = [], isLoading: slotsLoading } = useQuery({
    queryKey: queryKeys.curricula.courseSlots(id),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/curricula/${id}/course-slots` as never)
      return ((data as unknown) as CourseSlot[]) ?? []
    },
  })

  const { data: allCourses = [] } = useQuery({
    queryKey: queryKeys.courses.all,
    queryFn: async () => {
      const { data } = await apiClient.GET("/courses" as never)
      return ((data as unknown) as Course[]) ?? []
    },
  })
  const courseById = Object.fromEntries(allCourses.map((c) => [c.id, c]))

  // A semester's credit hours come from the courses placed into it — sum them up
  // rather than relying on the (usually unset) `total_credit_hours` field.
  const creditsByTermId = slots.reduce<Record<string, number>>((acc, slot) => {
    const credits = courseById[slot.course_id]?.credits ?? 0
    acc[slot.curriculum_term_definition_id] = (acc[slot.curriculum_term_definition_id] ?? 0) + credits
    return acc
  }, {})

  const slotsByTermId = slots.reduce<Record<string, CourseSlot[]>>((acc, slot) => {
    const key = slot.curriculum_term_definition_id
    acc[key] = acc[key] ? [...acc[key], slot] : [slot]
    return acc
  }, {})

  const termColumns: ColumnDef<TermDefinition>[] = [
    { accessorKey: "term_number", header: "#" },
    { accessorKey: "name", header: "Name" },
    {
      accessorKey: "total_credit_hours",
      header: "Credit Hours",
      cell: ({ row }) => {
        const computed = creditsByTermId[row.original.id] ?? 0
        return computed > 0 ? computed : (row.original.total_credit_hours ?? "—")
      },
    },
  ]

  const slotColumns: ColumnDef<CourseSlot>[] = [
    {
      id: "code",
      header: "Code",
      cell: ({ row }) => courseById[row.original.course_id]?.code ?? "—",
    },
    {
      id: "title",
      header: "Title",
      cell: ({ row }) => courseById[row.original.course_id]?.title ?? "—",
    },
    {
      id: "credits",
      header: "Credits",
      cell: ({ row }) => courseById[row.original.course_id]?.credits ?? "—",
    },
  ]

  const editForm = useForm<EditValues>({
    resolver: zodResolver(editSchema),
    values: curriculum ? { name: curriculum.name } : undefined,
  })

  const editMutation = useMutation({
    mutationFn: async (values: EditValues) => {
      await apiClient.PATCH(`/curricula/${id}` as never, { body: values } as never)
    },
    onSuccess: () => {
      toast.success("Curriculum updated")
      qc.invalidateQueries({ queryKey: queryKeys.curricula.detail(id) })
      qc.invalidateQueries({ queryKey: queryKeys.curricula.all })
    },
    onError: () => toast.error("Failed to update curriculum"),
  })

  const [archiveOpen, setArchiveOpen] = useState(false)

  const archiveMutation = useMutation({
    mutationFn: async () => {
      await apiClient.POST(`/curricula/${id}/archive` as never, {} as never)
    },
    onSuccess: () => {
      toast.success("Curriculum archived")
      qc.invalidateQueries({ queryKey: queryKeys.curricula.detail(id) })
      qc.invalidateQueries({ queryKey: queryKeys.curricula.all })
      setArchiveOpen(false)
    },
    onError: () => toast.error("Failed to archive curriculum"),
  })

  const addTermForm = useForm<AddTermValues>({ resolver: zodResolver(addTermSchema) })

  const addTermMutation = useMutation({
    mutationFn: async (values: AddTermValues) => {
      await apiClient.POST(`/curricula/${id}/terms` as never, {
        body: [{
          term_number: values.term_number,
          name: values.name,
          total_credit_hours: values.total_credit_hours ?? null,
        }],
      } as never)
    },
    onSuccess: () => {
      toast.success("Semester added to curriculum")
      qc.invalidateQueries({ queryKey: queryKeys.curricula.terms(id) })
      setAddTermOpen(false)
      addTermForm.reset()
    },
    onError: () => toast.error("Failed to add semester"),
  })

  const [selTermId, setSelTermId] = useState("")
  const [selCourseId, setSelCourseId] = useState("")
  const addSlotForm = useForm<AddCourseSlotValues>({ resolver: zodResolver(addCourseSlotSchema) })

  const addSlotMutation = useMutation({
    mutationFn: async (values: AddCourseSlotValues) => {
      await apiClient.POST(`/curricula/${id}/course-slots` as never, {
        body: {
          curriculum_term_definition_id: values.curriculum_term_definition_id,
          course_id: values.course_id,
          is_elective: false,
        },
      } as never)
    },
    onSuccess: () => {
      toast.success("Course added to curriculum")
      qc.invalidateQueries({ queryKey: queryKeys.curricula.courseSlots(id) })
      setAddSlotOpen(false)
      setSelTermId("")
      setSelCourseId("")
      addSlotForm.reset()
    },
    onError: () => toast.error("Failed to add course"),
  })

  if (isLoading) {
    return <div className="animate-pulse h-40 bg-muted rounded-md" />
  }

  if (!curriculum) {
    return <p className="text-muted-foreground">Curriculum not found.</p>
  }

  const program = programById[curriculum.program_id]

  return (
    <div className="space-y-6">
      <PageHeader
        title={curriculum.name}
        description={`${program ? programLabel(program) : "—"} — v${curriculum.version_number}`}
        actions={
          <div className="flex items-center gap-3">
            {curriculum.status !== "ARCHIVED" && (
              <PermissionGate permission="curriculum.update">
                <Button variant="outline" size="sm" className="gap-2" onClick={() => setArchiveOpen(true)}>
                  <Archive className="h-4 w-4" />
                  Archive
                </Button>
              </PermissionGate>
            )}
            {isSuperAdmin && (
              <Button
                variant="destructive"
                size="sm"
                disabled={deleteMutation.isPending}
                onClick={() => {
                  if (window.confirm(`Permanently delete "${curriculum.name}"? This cannot be undone.`))
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

      <ConfirmDialog
        open={archiveOpen}
        onOpenChange={setArchiveOpen}
        title="Archive Curriculum"
        description="This will mark the curriculum as archived and hide it from the active list. Its batches, semesters, and courses remain intact and this can be reviewed later, but the curriculum can no longer be edited or have courses added. Continue?"
        confirmLabel="Archive"
        variant="destructive"
        loading={archiveMutation.isPending}
        onConfirm={() => archiveMutation.mutate()}
      />

      <div className="grid grid-cols-1 lg:grid-cols-[380px_1fr] gap-6 items-start">
        {/* LEFT — Curriculum details & semester structure */}
        <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Curriculum Details</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-muted-foreground">Program</p>
                <p className="font-medium">{program ? programLabel(program) : "—"}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Effective Year</p>
                <p className="font-medium">{curriculum.effective_year}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Version</p>
                <p className="font-medium">v{curriculum.version_number}</p>
              </div>
            </div>

            <PermissionGate permission="curriculum.update">
              <form
                id="edit-curriculum-form"
                onSubmit={editForm.handleSubmit((v) => editMutation.mutate(v))}
                className="space-y-4 border-t pt-4"
              >
                <p className="text-sm font-medium">Edit Curriculum</p>
                <div className="space-y-2">
                  <Label htmlFor="edit-name">Name</Label>
                  <Input id="edit-name" {...editForm.register("name")} />
                  {editForm.formState.errors.name && (
                    <p className="text-sm text-destructive">
                      {editForm.formState.errors.name.message}
                    </p>
                  )}
                </div>
                <Button
                  type="submit"
                  form="edit-curriculum-form"
                  disabled={editMutation.isPending}
                >
                  {editMutation.isPending && (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  )}
                  Save Changes
                </Button>
              </form>
            </PermissionGate>
          </CardContent>
        </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Semesters</CardTitle>
                <CardDescription>
                  {termsLoading
                    ? "Loading…"
                    : terms.length === 0
                      ? "No semesters defined yet."
                      : `This curriculum has ${terms.length} semester${terms.length === 1 ? "" : "s"} defined.`}
                </CardDescription>
              </div>
              <PermissionGate permission="curriculum.update">
                <Dialog open={addTermOpen} onOpenChange={setAddTermOpen}>
                  <DialogTrigger render={<Button size="sm" />}>
                    <Plus className="h-4 w-4" />
                    Add Semester
                  </DialogTrigger>
                  <DialogContent className="sm:max-w-md">
                    <DialogHeader>
                      <DialogTitle>Add Semester to Curriculum</DialogTitle>
                    </DialogHeader>
                    <form
                      id="add-term-form"
                      onSubmit={addTermForm.handleSubmit((v) => addTermMutation.mutate(v))}
                      className="space-y-4 py-2"
                    >
                      <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                          <Label htmlFor="term-number">Semester Number</Label>
                          <Input
                            id="term-number"
                            type="number"
                            min={1}
                            max={20}
                            placeholder="e.g. 1"
                            {...addTermForm.register("term_number", { valueAsNumber: true })}
                          />
                          {addTermForm.formState.errors.term_number && (
                            <p className="text-sm text-destructive">
                              {addTermForm.formState.errors.term_number.message}
                            </p>
                          )}
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="term-credit-hours">Total Credit Hours</Label>
                          <Input
                            id="term-credit-hours"
                            type="number"
                            min={0}
                            placeholder="Optional"
                            {...addTermForm.register("total_credit_hours", { valueAsNumber: true })}
                          />
                        </div>
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="term-name">Name</Label>
                        <Input
                          id="term-name"
                          placeholder="e.g. Semester 1"
                          {...addTermForm.register("name")}
                        />
                        {addTermForm.formState.errors.name && (
                          <p className="text-sm text-destructive">
                            {addTermForm.formState.errors.name.message}
                          </p>
                        )}
                      </div>
                    </form>
                    <DialogFooter>
                      <Button
                        variant="outline"
                        onClick={() => setAddTermOpen(false)}
                        disabled={addTermMutation.isPending}
                      >
                        Cancel
                      </Button>
                      <Button
                        type="submit"
                        form="add-term-form"
                        disabled={addTermMutation.isPending}
                      >
                        {addTermMutation.isPending && (
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        )}
                        Add Semester
                      </Button>
                    </DialogFooter>
                  </DialogContent>
                </Dialog>
              </PermissionGate>
            </CardHeader>
            <CardContent>
              <DataTable
                columns={termColumns}
                data={sortedTerms}
                loading={termsLoading}
                emptyMessage="No semesters defined for this curriculum yet."
              />
            </CardContent>
          </Card>
        </div>

        {/* RIGHT — Courses */}
        <div className="space-y-6">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Courses</CardTitle>
                <CardDescription>
                  {terms.length === 0
                    ? "Add at least one semester above before adding courses."
                    : "Place courses into this curriculum's semesters."}
                </CardDescription>
              </div>
              <PermissionGate permission="curriculum.update">
                <Dialog
                  open={addSlotOpen}
                  onOpenChange={(v) => {
                    setAddSlotOpen(v)
                    if (!v) {
                      setSelTermId("")
                      setSelCourseId("")
                      addSlotForm.reset()
                    }
                  }}
                >
                  <DialogTrigger render={<Button size="sm" disabled={terms.length === 0} />}>
                    <Plus className="h-4 w-4" />
                    Add Course
                  </DialogTrigger>
                  <DialogContent className="sm:max-w-md">
                    <DialogHeader>
                      <DialogTitle>Add Course to Curriculum</DialogTitle>
                    </DialogHeader>
                    <form
                      id="add-course-form"
                      onSubmit={addSlotForm.handleSubmit((v) => addSlotMutation.mutate(v))}
                      className="space-y-4 py-2"
                    >
                      <div className="space-y-2">
                        <Label>Semester</Label>
                        <Select
                          value={selTermId}
                          onValueChange={(v) => { if (v == null) return; setSelTermId(v as string); addSlotForm.setValue("curriculum_term_definition_id", v as string, { shouldValidate: true }) }}
                        >
                          <SelectTrigger className="w-full">
                            <SelectValue placeholder="Select semester">
                              {selTermId && termById[selTermId] ? `${termById[selTermId].term_number}. ${termById[selTermId].name}` : undefined}
                            </SelectValue>
                          </SelectTrigger>
                          <SelectContent>
                            {sortedTerms.map((t) => (
                              <SelectItem key={t.id} value={t.id}>
                                {t.term_number}. {t.name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        {addSlotForm.formState.errors.curriculum_term_definition_id && (
                          <p className="text-sm text-destructive">
                            {addSlotForm.formState.errors.curriculum_term_definition_id.message}
                          </p>
                        )}
                      </div>
                      <div className="space-y-2">
                        <Label>Course</Label>
                        <Select
                          value={selCourseId}
                          onValueChange={(v) => { if (v == null) return; setSelCourseId(v as string); addSlotForm.setValue("course_id", v as string, { shouldValidate: true }) }}
                        >
                          <SelectTrigger className="w-full">
                            <SelectValue placeholder="Select course">
                              {selCourseId && courseById[selCourseId] ? `${courseById[selCourseId].code} — ${courseById[selCourseId].title}` : undefined}
                            </SelectValue>
                          </SelectTrigger>
                          <SelectContent>
                            {allCourses.map((c) => (
                              <SelectItem key={c.id} value={c.id}>
                                {c.code} — {c.title}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        {addSlotForm.formState.errors.course_id && (
                          <p className="text-sm text-destructive">
                            {addSlotForm.formState.errors.course_id.message}
                          </p>
                        )}
                      </div>

                    </form>
                    <DialogFooter>
                      <Button
                        variant="outline"
                        onClick={() => setAddSlotOpen(false)}
                        disabled={addSlotMutation.isPending}
                      >
                        Cancel
                      </Button>
                      <Button
                        type="submit"
                        form="add-course-form"
                        disabled={addSlotMutation.isPending}
                      >
                        {addSlotMutation.isPending && (
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        )}
                        Add Course
                      </Button>
                    </DialogFooter>
                  </DialogContent>
                </Dialog>
              </PermissionGate>
            </CardHeader>
            <CardContent className="space-y-4">
              {terms.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  Define at least one semester above — courses are placed into a specific semester
                  when added, which links them to both this curriculum and that semester.
                </p>
              ) : slotsLoading ? (
                <div className="animate-pulse h-32 bg-muted rounded-md" />
              ) : slots.length === 0 ? (
                <p className="text-sm text-muted-foreground">No courses in this curriculum yet.</p>
              ) : (
                sortedTerms
                  .filter((term) => (slotsByTermId[term.id] ?? []).length > 0)
                  .map((term) => {
                    const termSlots = slotsByTermId[term.id] ?? []
                    const termCredits = creditsByTermId[term.id] ?? 0
                    return (
                      <Card key={term.id} className="border-muted shadow-none">
                        <CardHeader className="py-3">
                          <div className="flex items-center justify-between gap-4">
                            <CardTitle className="text-sm font-semibold">
                              {term.term_number}. {term.name}
                            </CardTitle>
                            <span className="text-xs text-muted-foreground whitespace-nowrap">
                              {termSlots.length} course{termSlots.length === 1 ? "" : "s"}
                              {termCredits > 0 ? ` · ${termCredits} credit hours` : ""}
                            </span>
                          </div>
                        </CardHeader>
                        <CardContent className="pt-0">
                          <DataTable columns={slotColumns} data={termSlots} />
                        </CardContent>
                      </Card>
                    )
                  })
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
