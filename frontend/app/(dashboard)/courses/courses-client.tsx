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

type Course = {
  id: string
  code: string
  title: string
  credits: number
  course_type_id: string
  theory_hours: number
  lab_hours: number
  description: string | null
  status: string
}

type CourseType = { id: string; name: string }

const schema = z.object({
  code: z.string().min(1, "Code is required").max(30),
  title: z.string().min(1, "Title is required").max(255),
  credits: z.number().int().min(0, "Credits cannot be negative").max(20),
  course_type_id: z.string().min(1, "Course type is required"),
  theory_hours: z.number().int().min(0),
  lab_hours: z.number().int().min(0),
  description: z.string().max(2000).optional(),
})
type FormValues = z.infer<typeof schema>

export function CoursesClient() {
  const [open, setOpen] = useState(false)
  const [selTypeId, setSelTypeId] = useState("")
  const qc = useQueryClient()
  const router = useRouter()

  const { data: courses = [], isLoading } = useQuery({
    queryKey: queryKeys.courses.all,
    queryFn: async () => {
      const { data } = await apiClient.GET("/courses" as never)
      return ((data as unknown) as Course[]) ?? []
    },
  })

  const { data: courseTypes = [] } = useQuery({
    queryKey: queryKeys.courseTypes.all,
    queryFn: async () => {
      const { data } = await apiClient.GET("/ref-data/course-types" as never)
      return ((data as unknown) as CourseType[]) ?? []
    },
  })

  const courseTypeById = Object.fromEntries(courseTypes.map((t) => [t.id, t]))

  const [newTypeOpen, setNewTypeOpen] = useState(false)
  const [newTypeName, setNewTypeName] = useState("")

  const createTypeMutation = useMutation({
    mutationFn: async (name: string) => {
      const { data } = await apiClient.POST("/ref-data/course-types" as never, { body: { name } } as never)
      return (data as unknown) as CourseType
    },
    onSuccess: (created) => {
      toast.success("Course type created")
      qc.invalidateQueries({ queryKey: queryKeys.courseTypes.all })
      setSelTypeId(created.id)
      setValue("course_type_id", created.id, { shouldValidate: true })
      setNewTypeName("")
      setNewTypeOpen(false)
    },
    onError: () => toast.error("Failed to create course type"),
  })

  const columns: ColumnDef<Course>[] = [
    { accessorKey: "code", header: "Code" },
    { accessorKey: "title", header: "Title" },
    { accessorKey: "credits", header: "Credits" },
    {
      id: "course_type",
      header: "Type",
      cell: ({ row }) => courseTypeById[row.original.course_type_id]?.name ?? "—",
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
    defaultValues: { theory_hours: 0, lab_hours: 0 },
  })

  const mutation = useMutation({
    mutationFn: async (values: FormValues) => {
      await apiClient.POST("/courses" as never, {
        body: {
          code: values.code,
          title: values.title,
          credits: values.credits,
          course_type_id: values.course_type_id,
          theory_hours: values.theory_hours,
          lab_hours: values.lab_hours,
          description: values.description || undefined,
        },
      } as never)
    },
    onSuccess: () => {
      toast.success("Course created")
      qc.invalidateQueries({ queryKey: queryKeys.courses.all })
      setOpen(false)
      setSelTypeId("")
      reset({ theory_hours: 0, lab_hours: 0 })
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
            <Dialog
              open={open}
              onOpenChange={(v) => {
                setOpen(v)
                if (!v) {
                  setSelTypeId("")
                  setNewTypeOpen(false)
                  setNewTypeName("")
                  reset({ theory_hours: 0, lab_hours: 0 })
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
                      <Label>Course Type</Label>
                      <PermissionGate permission="config.manage">
                        <button
                          type="button"
                          className="text-xs font-medium text-primary hover:underline"
                          onClick={() => {
                            setNewTypeOpen((v) => !v)
                            setNewTypeName("")
                          }}
                        >
                          {newTypeOpen ? "Cancel" : "+ New type"}
                        </button>
                      </PermissionGate>
                    </div>
                    {newTypeOpen && (
                      <div className="flex gap-2 rounded-lg border bg-muted/30 p-2">
                        <Input
                          className="flex-1"
                          placeholder="e.g. Core, Elective, Lab"
                          value={newTypeName}
                          onChange={(e) => setNewTypeName(e.target.value)}
                        />
                        <Button
                          type="button"
                          size="sm"
                          disabled={!newTypeName.trim() || createTypeMutation.isPending}
                          onClick={() => createTypeMutation.mutate(newTypeName.trim())}
                        >
                          {createTypeMutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
                          Add
                        </Button>
                      </div>
                    )}
                    <Select
                      value={selTypeId}
                      onValueChange={(v) => {
                        if (v == null) return
                        setSelTypeId(v as string)
                        setValue("course_type_id", v as string, { shouldValidate: true })
                      }}
                    >
                      <SelectTrigger className="w-full">
                        <SelectValue placeholder="Select type">
                          {selTypeId ? courseTypeById[selTypeId]?.name : undefined}
                        </SelectValue>
                      </SelectTrigger>
                      <SelectContent>
                        {courseTypes.map((t) => (
                          <SelectItem key={t.id} value={t.id}>
                            {t.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {errors.course_type_id && (
                      <p className="text-sm text-destructive">{errors.course_type_id.message}</p>
                    )}
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="theory_hours">Theory Hours</Label>
                      <Input
                        id="theory_hours"
                        type="number"
                        min={0}
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
                        {...register("lab_hours", { valueAsNumber: true })}
                      />
                      {errors.lab_hours && (
                        <p className="text-sm text-destructive">{errors.lab_hours.message}</p>
                      )}
                    </div>
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
        emptyMessage="No courses found."
      />
    </div>
  )
}
