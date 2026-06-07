"use client"

import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { toast } from "sonner"
import { Loader2, Plus } from "lucide-react"
import type { ColumnDef } from "@tanstack/react-table"

import { PageHeader } from "@/components/shared/page-header"
import { DataTable } from "@/components/shared/data-table"
import { StatusBadge } from "@/components/shared/status-badge"
import { PermissionGate } from "@/components/shared/permission-gate"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
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
import { formatDate } from "@/lib/utils"

type Curriculum = {
  id: string
  name: string
  version: string
  status: string
  program_name: string
  effective_from: string
  effective_to?: string
}

type CourseSlot = {
  id: string
  code: string
  title: string
  credits: number
  term: string
  type: string
}

type CourseOption = {
  id: string
  code: string
  title: string
}

const editSchema = z.object({
  name: z.string().min(1, "Name is required"),
  effective_from: z.string().min(1, "Required"),
  effective_to: z.string().optional(),
})
type EditValues = z.infer<typeof editSchema>

const addCourseSchema = z.object({
  course_id: z.string().min(1, "Course is required"),
  term: z.string().min(1, "Term is required"),
  type: z.string().min(1, "Type is required"),
})
type AddCourseValues = z.infer<typeof addCourseSchema>

const courseColumns: ColumnDef<CourseSlot>[] = [
  { accessorKey: "code", header: "Code" },
  { accessorKey: "title", header: "Title" },
  { accessorKey: "credits", header: "Credits" },
  { accessorKey: "term", header: "Term" },
  { accessorKey: "type", header: "Type" },
]

interface Props {
  id: string
}

export function CurriculumDetailClient({ id }: Props) {
  const [addCourseOpen, setAddCourseOpen] = useState(false)
  const qc = useQueryClient()

  const { data: curriculum, isLoading } = useQuery({
    queryKey: queryKeys.curricula.detail(id),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/curricula/${id}` as never)
      return (data as unknown) as Curriculum
    },
  })

  const { data: courses = [], isLoading: coursesLoading } = useQuery({
    queryKey: ["curricula", id, "courses"],
    queryFn: async () => {
      const { data } = await apiClient.GET(`/curricula/${id}/courses` as never)
      return ((data as unknown) as CourseSlot[]) ?? []
    },
  })

  const { data: allCourses = [] } = useQuery({
    queryKey: queryKeys.courses.all,
    queryFn: async () => {
      const { data } = await apiClient.GET("/courses" as never)
      return ((data as unknown) as CourseOption[]) ?? []
    },
  })

  const editForm = useForm<EditValues>({
    resolver: zodResolver(editSchema),
    values: curriculum
      ? {
          name: curriculum.name,
          effective_from: curriculum.effective_from?.slice(0, 10) ?? "",
          effective_to: curriculum.effective_to?.slice(0, 10) ?? "",
        }
      : undefined,
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

  const addCourseForm = useForm<AddCourseValues>({ resolver: zodResolver(addCourseSchema) })

  const addCourseMutation = useMutation({
    mutationFn: async (values: AddCourseValues) => {
      await apiClient.POST(`/curricula/${id}/courses` as never, { body: values } as never)
    },
    onSuccess: () => {
      toast.success("Course added to curriculum")
      qc.invalidateQueries({ queryKey: ["curricula", id, "courses"] })
      setAddCourseOpen(false)
      addCourseForm.reset()
    },
    onError: () => toast.error("Failed to add course"),
  })

  if (isLoading) {
    return <div className="animate-pulse h-40 bg-muted rounded-md" />
  }

  if (!curriculum) {
    return <p className="text-muted-foreground">Curriculum not found.</p>
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={curriculum.name}
        description={`${curriculum.program_name} — v${curriculum.version}`}
        actions={<StatusBadge status={curriculum.status} />}
      />

      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="courses">Courses</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Details</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4 mb-6 text-sm">
                <div>
                  <p className="text-muted-foreground">Program</p>
                  <p className="font-medium">{curriculum.program_name}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Version</p>
                  <p className="font-medium">{curriculum.version}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Effective From</p>
                  <p className="font-medium">{formatDate(curriculum.effective_from)}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Effective To</p>
                  <p className="font-medium">
                    {curriculum.effective_to ? formatDate(curriculum.effective_to) : "—"}
                  </p>
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
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="edit-effective-from">Effective From</Label>
                      <Input
                        id="edit-effective-from"
                        type="date"
                        {...editForm.register("effective_from")}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="edit-effective-to">Effective To</Label>
                      <Input
                        id="edit-effective-to"
                        type="date"
                        {...editForm.register("effective_to")}
                      />
                    </div>
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
        </TabsContent>

        <TabsContent value="courses" className="mt-4">
          <div className="space-y-4">
            <div className="flex justify-end">
              <PermissionGate permission="curriculum.update">
                <Dialog open={addCourseOpen} onOpenChange={setAddCourseOpen}>
                  <DialogTrigger render={<Button />}>
                    <Plus className="h-4 w-4" />
                    Add Course
                  </DialogTrigger>
                  <DialogContent className="sm:max-w-md">
                    <DialogHeader>
                      <DialogTitle>Add Course to Curriculum</DialogTitle>
                    </DialogHeader>
                    <form
                      id="add-course-form"
                      onSubmit={addCourseForm.handleSubmit((v) => addCourseMutation.mutate(v))}
                      className="space-y-4 py-2"
                    >
                      <div className="space-y-2">
                        <Label>Course</Label>
                        <Select
                          onValueChange={(v) => v != null && addCourseForm.setValue("course_id", v as string)}
                        >
                          <SelectTrigger className="w-full">
                            <SelectValue placeholder="Select course" />
                          </SelectTrigger>
                          <SelectContent>
                            {allCourses.map((c) => (
                              <SelectItem key={c.id} value={c.id}>
                                {c.code} — {c.title}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        {addCourseForm.formState.errors.course_id && (
                          <p className="text-sm text-destructive">
                            {addCourseForm.formState.errors.course_id.message}
                          </p>
                        )}
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="term">Term</Label>
                        <Input
                          id="term"
                          {...addCourseForm.register("term")}
                          placeholder="e.g. Semester 1"
                        />
                        {addCourseForm.formState.errors.term && (
                          <p className="text-sm text-destructive">
                            {addCourseForm.formState.errors.term.message}
                          </p>
                        )}
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="type">Type</Label>
                        <Input
                          id="type"
                          {...addCourseForm.register("type")}
                          placeholder="e.g. CORE"
                        />
                        {addCourseForm.formState.errors.type && (
                          <p className="text-sm text-destructive">
                            {addCourseForm.formState.errors.type.message}
                          </p>
                        )}
                      </div>
                    </form>
                    <DialogFooter>
                      <Button
                        variant="outline"
                        onClick={() => setAddCourseOpen(false)}
                        disabled={addCourseMutation.isPending}
                      >
                        Cancel
                      </Button>
                      <Button
                        type="submit"
                        form="add-course-form"
                        disabled={addCourseMutation.isPending}
                      >
                        {addCourseMutation.isPending && (
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        )}
                        Add Course
                      </Button>
                    </DialogFooter>
                  </DialogContent>
                </Dialog>
              </PermissionGate>
            </div>
            <DataTable
              columns={courseColumns}
              data={courses}
              loading={coursesLoading}
              emptyMessage="No courses in this curriculum."
            />
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}
