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
import { PermissionGate } from "@/components/shared/permission-gate"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
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
  course_type: string
  department_name: string
}

type Department = {
  id: string
  name: string
}

const COURSE_TYPES = ["CORE", "ELECTIVE", "LAB", "PROJECT"] as const

const schema = z.object({
  code: z.string().min(1, "Code is required"),
  title: z.string().min(1, "Title is required"),
  credits: z.number().int().positive("Credits must be positive"),
  course_type: z.enum(COURSE_TYPES),
  department_id: z.string().min(1, "Department is required"),
})
type FormValues = z.infer<typeof schema>

const columns: ColumnDef<Course>[] = [
  { accessorKey: "code", header: "Code" },
  { accessorKey: "title", header: "Title" },
  { accessorKey: "credits", header: "Credits" },
  { accessorKey: "course_type", header: "Type" },
  { accessorKey: "department_name", header: "Department" },
]

export function CoursesClient() {
  const [open, setOpen] = useState(false)
  const qc = useQueryClient()
  const router = useRouter()

  const { data: courses = [], isLoading } = useQuery({
    queryKey: queryKeys.courses.all,
    queryFn: async () => {
      const { data } = await apiClient.GET("/courses" as never)
      return ((data as unknown) as Course[]) ?? []
    },
  })

  const { data: departments = [] } = useQuery({
    queryKey: queryKeys.departments.all,
    queryFn: async () => {
      const { data } = await apiClient.GET("/departments" as never)
      return ((data as unknown) as Department[]) ?? []
    },
  })

  const {
    register,
    handleSubmit,
    setValue,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) })

  const mutation = useMutation({
    mutationFn: async (values: FormValues) => {
      await apiClient.POST("/courses" as never, { body: values } as never)
    },
    onSuccess: () => {
      toast.success("Course created")
      qc.invalidateQueries({ queryKey: queryKeys.courses.all })
      setOpen(false)
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
            <Dialog open={open} onOpenChange={setOpen}>
              <DialogTrigger render={<Button />}>
                <Plus className="h-4 w-4" />
                New Course
              </DialogTrigger>
              <DialogContent className="sm:max-w-md">
                <DialogHeader>
                  <DialogTitle>Create Course</DialogTitle>
                </DialogHeader>
                <form
                  id="create-course-form"
                  onSubmit={handleSubmit((v) => mutation.mutate(v))}
                  className="space-y-4 py-2"
                >
                  <div className="space-y-2">
                    <Label htmlFor="code">Code</Label>
                    <Input id="code" {...register("code")} placeholder="e.g. CS101" />
                    {errors.code && (
                      <p className="text-sm text-destructive">{errors.code.message}</p>
                    )}
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="title">Title</Label>
                    <Input id="title" {...register("title")} />
                    {errors.title && (
                      <p className="text-sm text-destructive">{errors.title.message}</p>
                    )}
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="credits">Credits</Label>
                    <Input id="credits" type="number" min={1} {...register("credits", { valueAsNumber: true })} />
                    {errors.credits && (
                      <p className="text-sm text-destructive">{errors.credits.message}</p>
                    )}
                  </div>
                  <div className="space-y-2">
                    <Label>Course Type</Label>
                    <Select onValueChange={(v) => v != null && setValue("course_type", v as FormValues["course_type"])}>
                      <SelectTrigger className="w-full">
                        <SelectValue placeholder="Select type" />
                      </SelectTrigger>
                      <SelectContent>
                        {COURSE_TYPES.map((t) => (
                          <SelectItem key={t} value={t}>
                            {t}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {errors.course_type && (
                      <p className="text-sm text-destructive">{errors.course_type.message}</p>
                    )}
                  </div>
                  <div className="space-y-2">
                    <Label>Department</Label>
                    <Select onValueChange={(v) => v != null && setValue("department_id", v as string)}>
                      <SelectTrigger className="w-full">
                        <SelectValue placeholder="Select department" />
                      </SelectTrigger>
                      <SelectContent>
                        {departments.map((d) => (
                          <SelectItem key={d.id} value={d.id}>
                            {d.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {errors.department_id && (
                      <p className="text-sm text-destructive">{errors.department_id.message}</p>
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
