"use client"

import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { toast } from "sonner"
import { Plus, Loader2 } from "lucide-react"
import { useRouter } from "next/navigation"
import type { ColumnDef } from "@tanstack/react-table"

import { PageHeader } from "@/components/shared/page-header"
import { DataTable } from "@/components/shared/data-table"
import { StatusBadge } from "@/components/shared/status-badge"
import { Badge } from "@/components/ui/badge"
import { PermissionGate } from "@/components/shared/permission-gate"
import { Button } from "@/components/ui/button"
import { BulkImportCoursesDialog } from "./bulk-import-courses-dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { MultiCombobox } from "@/components/ui/multi-combobox"
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
import { usePermission } from "@/hooks/use-permission"

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
  status: string
}

type CourseCategory = { id: string; name: string }

type ModuleLeaderAssignment = { course_id: string }

const COURSE_TYPE_LABELS: Record<string, string> = {
  THEORY: "Theory",
  LAB: "Lab",
  THEORY_LAB: "Theory + Lab",
  THESIS_DEFENSE: "Final Year Thesis Defense",
}

const schema = z.object({
  code: z.string().min(1, "Code is required").max(30),
  title: z.string().min(1, "Title is required").max(255),
  credits: z.number().int().min(0, "Credits cannot be negative").max(20),
  course_category_id: z.string().min(1, "Course category is required"),
  course_type: z.enum(["THEORY", "LAB", "THEORY_LAB", "THESIS_DEFENSE"], {
    error: "Course type is required",
  }),
  theory_hours: z.number().int().min(0),
  lab_hours: z.number().int().min(0),
  description: z.string().max(2000).optional(),
  prerequisite_course_ids: z.array(z.string()).optional(),
})
type FormValues = z.infer<typeof schema>

export function CoursesClient() {
  const [open, setOpen] = useState(false)
  const [selCategoryId, setSelCategoryId] = useState("")
  const [selCourseType, setSelCourseType] = useState("")
  const [selPrereqIds, setSelPrereqIds] = useState<string[]>([])
  const qc = useQueryClient()
  const router = useRouter()

  const canManageCourses = usePermission("course.create")

  const { data: allCourses = [], isLoading } = useQuery({
    queryKey: queryKeys.courses.all,
    queryFn: async () => {
      const { data } = await apiClient.GET("/courses" as never)
      return ((data as unknown) as Course[]) ?? []
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

  const myModuleLeaderCourseIds = new Set(myAssignments.map((a) => a.course_id))

  // Module Leaders (and other non-managing roles with assignments) only see
  // the courses they've been assigned to lead.
  const courses =
    !canManageCourses && myModuleLeaderCourseIds.size > 0
      ? allCourses.filter((c) => myModuleLeaderCourseIds.has(c.id))
      : allCourses

  const courseCategoryById = Object.fromEntries(courseCategories.map((t) => [t.id, t]))

  const [newCategoryOpen, setNewCategoryOpen] = useState(false)
  const [newCategoryName, setNewCategoryName] = useState("")

  const createCategoryMutation = useMutation({
    mutationFn: async (name: string) => {
      const { data } = await apiClient.POST("/ref-data/course-categories" as never, { body: { name } } as never)
      return (data as unknown) as CourseCategory
    },
    onSuccess: (created) => {
      toast.success("Course category created")
      qc.invalidateQueries({ queryKey: queryKeys.courseCategories.all })
      setSelCategoryId(created.id)
      setValue("course_category_id", created.id, { shouldValidate: true })
      setNewCategoryName("")
      setNewCategoryOpen(false)
    },
    onError: () => toast.error("Failed to create course category"),
  })

  const columns: ColumnDef<Course>[] = [
    { accessorKey: "code", header: "Code" },
    {
      accessorKey: "title",
      header: "Title",
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <span>{row.original.title}</span>
          {canManageCourses && myModuleLeaderCourseIds.has(row.original.id) && (
            <Badge variant="secondary">Module Leader</Badge>
          )}
        </div>
      ),
    },
    { accessorKey: "credits", header: "Credits" },
    {
      id: "course_category",
      header: "Category",
      cell: ({ row }) => courseCategoryById[row.original.course_category_id]?.name ?? "—",
    },
    {
      accessorKey: "course_type",
      header: "Type",
      cell: ({ row }) => COURSE_TYPE_LABELS[row.original.course_type] ?? row.original.course_type,
    },
    { accessorKey: "theory_hours", header: "Theory Hrs" },
    { accessorKey: "lab_hours", header: "Lab Hrs" },
    {
      accessorKey: "status",
      header: "Status",
      cell: ({ row }) => <StatusBadge status={row.original.status} />,
    },
  ]

  const {
    register,
    handleSubmit,
    setValue,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { code: "", title: "", credits: 0, theory_hours: 0, lab_hours: 0, description: "" },
  })

  const mutation = useMutation({
    mutationFn: async (values: FormValues) => {
      const { data } = await apiClient.POST("/courses" as never, {
        body: {
          code: values.code,
          title: values.title,
          credits: values.credits,
          course_category_id: values.course_category_id,
          course_type: values.course_type,
          theory_hours: values.theory_hours,
          lab_hours: values.lab_hours,
          description: values.description || undefined,
        },
      } as never)
      const created = (data as unknown) as { id: string }
      if (created?.id && values.prerequisite_course_ids?.length) {
        await Promise.all(
          values.prerequisite_course_ids.map((prereqId) =>
            apiClient.POST(`/courses/${created.id}/prerequisites` as never, {
              body: { prerequisite_course_id: prereqId },
            } as never)
          )
        )
      }
    },
    onSuccess: () => {
      toast.success("Course created")
      qc.invalidateQueries({ queryKey: queryKeys.courses.all })
      setOpen(false)
      setSelCategoryId("")
      setSelCourseType("")
      setSelPrereqIds([])
      reset()
    },
    onError: () => toast.error("Failed to create course"),
  })

  return (
    <div>
      <PageHeader
        title="Courses"
        description="Manage the course catalogue."
        actions={
          <PermissionGate permission="course.create">
            <BulkImportCoursesDialog />
            <Dialog
              open={open}
              onOpenChange={(v) => {
                setOpen(v)
                if (!v) {
                  setSelCategoryId("")
                  setSelCourseType("")
                  setSelPrereqIds([])
                  setNewCategoryOpen(false)
                  setNewCategoryName("")
                  reset()
                }
              }}
            >
              <DialogTrigger render={<Button />}>
                <Plus className="h-4 w-4" />
                New Course
              </DialogTrigger>
              <DialogContent className="sm:max-w-lg">
                <DialogHeader>
                  <DialogTitle>Create Course</DialogTitle>
                </DialogHeader>
                <form
                  id="create-course-form"
                  onSubmit={handleSubmit((v) => mutation.mutate(v))}
                  className="space-y-4 py-2"
                >
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="code">Code</Label>
                      <Input id="code" {...register("code")} placeholder="e.g. CS101" />
                      {errors.code && (
                        <p className="text-sm text-destructive">{errors.code.message}</p>
                      )}
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="credits">Credits</Label>
                      <Input
                        id="credits"
                        type="number"
                        min={0}
                        max={20}
                        {...register("credits", { valueAsNumber: true })}
                      />
                      {errors.credits && (
                        <p className="text-sm text-destructive">{errors.credits.message}</p>
                      )}
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="title">Title</Label>
                    <Input id="title" {...register("title")} placeholder="e.g. Introduction to Programming" />
                    {errors.title && (
                      <p className="text-sm text-destructive">{errors.title.message}</p>
                    )}
                  </div>
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <Label>Course Category</Label>
                      <PermissionGate permission="config.manage">
                        <button
                          type="button"
                          className="text-xs font-medium text-primary hover:underline"
                          onClick={() => {
                            setNewCategoryOpen((v) => !v)
                            setNewCategoryName("")
                          }}
                        >
                          {newCategoryOpen ? "Cancel" : "+ New category"}
                        </button>
                      </PermissionGate>
                    </div>
                    {newCategoryOpen && (
                      <div className="flex gap-2 rounded-lg border bg-muted/30 p-2">
                        <Input
                          className="flex-1"
                          placeholder="e.g. Core, Elective, Lab"
                          value={newCategoryName}
                          onChange={(e) => setNewCategoryName(e.target.value)}
                        />
                        <Button
                          type="button"
                          size="sm"
                          disabled={!newCategoryName.trim() || createCategoryMutation.isPending}
                          onClick={() => createCategoryMutation.mutate(newCategoryName.trim())}
                        >
                          {createCategoryMutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
                          Add
                        </Button>
                      </div>
                    )}
                    <Select
                      value={selCategoryId}
                      onValueChange={(v) => {
                        if (v == null) return
                        setSelCategoryId(v as string)
                        setValue("course_category_id", v as string, { shouldValidate: true })
                      }}
                    >
                      <SelectTrigger className="w-full">
                        <SelectValue placeholder="Select category">
                          {selCategoryId ? courseCategoryById[selCategoryId]?.name : undefined}
                        </SelectValue>
                      </SelectTrigger>
                      <SelectContent>
                        {courseCategories.map((t) => (
                          <SelectItem key={t.id} value={t.id}>
                            {t.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {errors.course_category_id && (
                      <p className="text-sm text-destructive">{errors.course_category_id.message}</p>
                    )}
                  </div>
                  <div className="space-y-2">
                    <Label>Course Type</Label>
                    <Select
                      value={selCourseType}
                      onValueChange={(v) => {
                        if (v == null) return
                        setSelCourseType(v as string)
                        setValue("course_type", v as FormValues["course_type"], { shouldValidate: true })
                        if (v === "THEORY") {
                          setValue("lab_hours", 0, { shouldValidate: true })
                        } else if (v === "LAB") {
                          setValue("theory_hours", 0, { shouldValidate: true })
                        }
                      }}
                    >
                      <SelectTrigger className="w-full">
                        <SelectValue placeholder="Select course type">
                          {selCourseType ? COURSE_TYPE_LABELS[selCourseType] : undefined}
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
                    {errors.course_type && (
                      <p className="text-sm text-destructive">{errors.course_type.message}</p>
                    )}
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="theory_hours">Theory Hours</Label>
                      <Input
                        id="theory_hours"
                        type="number"
                        min={0}
                        disabled={selCourseType === "LAB"}
                        {...register("theory_hours", { valueAsNumber: true })}
                      />
                      {errors.theory_hours && (
                        <p className="text-sm text-destructive">{errors.theory_hours.message}</p>
                      )}
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="lab_hours">Lab Hours</Label>
                      <Input
                        id="lab_hours"
                        type="number"
                        min={0}
                        disabled={selCourseType === "THEORY"}
                        {...register("lab_hours", { valueAsNumber: true })}
                      />
                      {errors.lab_hours && (
                        <p className="text-sm text-destructive">{errors.lab_hours.message}</p>
                      )}
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label>Prerequisites <span className="text-muted-foreground font-normal">(optional)</span></Label>
                    <MultiCombobox
                      options={allCourses
                        .filter((c) => c.status === "ACTIVE")
                        .map((c) => ({ value: c.id, label: `${c.code} — ${c.title}` }))}
                      values={selPrereqIds}
                      onValuesChange={(next) => {
                        setSelPrereqIds(next)
                        setValue("prerequisite_course_ids", next)
                      }}
                      placeholder="Select prerequisites…"
                      searchPlaceholder="Search courses…"
                      emptyText="No courses found."
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="description">Description</Label>
                    <Textarea
                      id="description"
                      rows={3}
                      {...register("description")}
                      placeholder="Brief overview of the course content (optional)"
                    />
                    {errors.description && (
                      <p className="text-sm text-destructive">{errors.description.message}</p>
                    )}
                  </div>
                </form>
                <DialogFooter>
                  <Button
                    variant="outline"
                    onClick={() => setOpen(false)}
                    disabled={isSubmitting || mutation.isPending}
                  >
                    Cancel
                  </Button>
                  <Button
                    type="submit"
                    form="create-course-form"
                    disabled={isSubmitting || mutation.isPending}
                  >
                    {(isSubmitting || mutation.isPending) && (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    )}
                    Create
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </PermissionGate>
        }
      />
      <DataTable
        columns={columns}
        data={courses}
        loading={isLoading}
        onRowClick={(row) => router.push(`/courses/${row.id}`)}
        emptyMessage={
          !canManageCourses && myAssignments.length === 0
            ? "You haven't been assigned as Module Leader for any course yet."
            : "No courses found."
        }
      />
    </div>
  )
}
