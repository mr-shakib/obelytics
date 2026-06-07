"use client"

import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useForm, Controller } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { toast } from "sonner"
import { Plus, Loader2 } from "lucide-react"
import { useRouter } from "next/navigation"
import type { ColumnDef } from "@tanstack/react-table"
import { DataTable } from "@/components/shared/data-table"
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
  DialogTrigger,
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
import { truncate, formatDate } from "@/lib/utils"

type CourseOutcome = {
  id: string
  code: string
  statement: string
  bloom_level?: string
  status: string
  submitted_at?: string
}

type Curriculum = { id: string; name: string }
type Course = { id: string; name: string; code?: string }
type BloomDomain = { id: string; name: string }

const schema = z.object({
  curriculum_id: z.string().min(1, "Curriculum is required"),
  course_id: z.string().min(1, "Course is required"),
  code: z.string().min(1, "Code is required"),
  statement: z.string().min(20, "Statement must be at least 20 characters"),
  bloom_level_id: z.string().min(1, "Bloom level is required"),
})
type FormValues = z.infer<typeof schema>

const columns: ColumnDef<CourseOutcome>[] = [
  { accessorKey: "code", header: "Code" },
  {
    accessorKey: "statement",
    header: "Statement",
    cell: ({ row }) => (
      <span title={row.original.statement}>{truncate(row.original.statement, 80)}</span>
    ),
  },
  {
    accessorKey: "bloom_level",
    header: "Bloom Level",
    cell: ({ row }) =>
      row.original.bloom_level ?? <span className="text-muted-foreground">—</span>,
  },
  {
    accessorKey: "status",
    header: "Status",
    cell: ({ row }) => <StatusBadge status={row.original.status} />,
  },
  {
    accessorKey: "submitted_at",
    header: "Submitted",
    cell: ({ row }) =>
      row.original.submitted_at ? (
        formatDate(row.original.submitted_at)
      ) : (
        <span className="text-muted-foreground">—</span>
      ),
  },
]

export function CourseOutcomesClient() {
  const [open, setOpen] = useState(false)
  const [selectedCurriculumId, setSelectedCurriculumId] = useState<string>("")
  const [selectedCourseId, setSelectedCourseId] = useState<string>("")
  const router = useRouter()
  const qc = useQueryClient()

  const { data: curricula } = useQuery({
    queryKey: queryKeys.curricula.list(),
    queryFn: async () => {
      const { data } = await apiClient.GET("/curricula" as never)
      return ((data as unknown) as { items?: Curriculum[] })?.items ?? ((data as unknown) as Curriculum[]) ?? []
    },
  })

  const { data: courses } = useQuery({
    queryKey: queryKeys.courses.list({ curriculum_id: selectedCurriculumId }),
    queryFn: async () => {
      const url = selectedCurriculumId
        ? (`/courses?curriculum_id=${selectedCurriculumId}` as never)
        : ("/courses" as never)
      const { data } = await apiClient.GET(url)
      return ((data as unknown) as { items?: Course[] })?.items ?? ((data as unknown) as Course[]) ?? []
    },
    enabled: true,
  })

  const { data: bloomDomains } = useQuery({
    queryKey: queryKeys.refData.bloomDomains,
    queryFn: async () => {
      const { data } = await apiClient.GET("/ref-data/bloom-domains" as never)
      return ((data as unknown) as { items?: BloomDomain[] })?.items ?? ((data as unknown) as BloomDomain[]) ?? []
    },
  })

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.courseOutcomes.list(selectedCurriculumId || undefined, selectedCourseId || undefined),
    queryFn: async () => {
      const params = new URLSearchParams()
      if (selectedCurriculumId) params.set("curriculum_id", selectedCurriculumId)
      if (selectedCourseId) params.set("course_id", selectedCourseId)
      const qs = params.toString()
      const url = qs ? (`/course-outcomes?${qs}` as never) : ("/course-outcomes" as never)
      const { data } = await apiClient.GET(url)
      return ((data as unknown) as { items?: CourseOutcome[] })?.items ?? ((data as unknown) as CourseOutcome[]) ?? []
    },
  })

  const {
    register,
    handleSubmit,
    control,
    reset,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      curriculum_id: selectedCurriculumId,
      course_id: selectedCourseId,
    },
  })

  const formCurriculumId = watch("curriculum_id")

  const { data: formCourses } = useQuery({
    queryKey: queryKeys.courses.list({ curriculum_id: formCurriculumId }),
    queryFn: async () => {
      const url = formCurriculumId
        ? (`/courses?curriculum_id=${formCurriculumId}` as never)
        : ("/courses" as never)
      const { data } = await apiClient.GET(url)
      return ((data as unknown) as { items?: Course[] })?.items ?? ((data as unknown) as Course[]) ?? []
    },
    enabled: !!formCurriculumId,
  })

  // Auto-suggest next CO code based on existing items
  const existingCount = data?.length ?? 0
  const suggestedCode = `CO${existingCount + 1}`

  const mutation = useMutation({
    mutationFn: async (values: FormValues) => {
      await apiClient.POST("/course-outcomes" as never, { body: values } as never)
    },
    onSuccess: () => {
      toast.success("Course Outcome created")
      qc.invalidateQueries({ queryKey: queryKeys.courseOutcomes.all })
      reset()
      setOpen(false)
    },
    onError: () => toast.error("Failed to create Course Outcome"),
  })

  return (
    <div>
      <PageHeader
        title="Course Outcomes"
        description="Manage course-level learning outcomes."
        actions={
          <PermissionGate permission="co.create">
            <Dialog open={open} onOpenChange={setOpen}>
              <DialogTrigger
                render={
                  <Button>
                    <Plus />
                    New CO
                  </Button>
                }
              />
              <DialogContent className="sm:max-w-lg">
                <DialogHeader>
                  <DialogTitle>Create Course Outcome</DialogTitle>
                </DialogHeader>
                <form
                  id="create-co-form"
                  onSubmit={handleSubmit((v) => mutation.mutate(v))}
                  className="space-y-4 py-2"
                >
                  <div className="space-y-2">
                    <Label>Curriculum</Label>
                    <Controller
                      name="curriculum_id"
                      control={control}
                      defaultValue={selectedCurriculumId}
                      render={({ field }) => (
                        <Select value={field.value ?? ""} onValueChange={field.onChange}>
                          <SelectTrigger className="w-full">
                            <SelectValue placeholder="Select curriculum" />
                          </SelectTrigger>
                          <SelectContent>
                            {(curricula ?? []).map((c) => (
                              <SelectItem key={c.id} value={c.id}>
                                {c.name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      )}
                    />
                    {errors.curriculum_id && (
                      <p className="text-sm text-destructive">{errors.curriculum_id.message}</p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label>Course</Label>
                    <Controller
                      name="course_id"
                      control={control}
                      defaultValue={selectedCourseId}
                      render={({ field }) => (
                        <Select value={field.value ?? ""} onValueChange={field.onChange}>
                          <SelectTrigger className="w-full">
                            <SelectValue placeholder="Select course" />
                          </SelectTrigger>
                          <SelectContent>
                            {(formCourses ?? []).map((c) => (
                              <SelectItem key={c.id} value={c.id}>
                                {c.code ? `${c.code} — ` : ""}{c.name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      )}
                    />
                    {errors.course_id && (
                      <p className="text-sm text-destructive">{errors.course_id.message}</p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="co-code">Code</Label>
                    <Input
                      id="co-code"
                      {...register("code")}
                      placeholder={suggestedCode}
                    />
                    {errors.code && (
                      <p className="text-sm text-destructive">{errors.code.message}</p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="co-statement">Statement</Label>
                    <Textarea
                      id="co-statement"
                      {...register("statement")}
                      placeholder="Describe the course outcome (min 20 characters)..."
                      rows={4}
                    />
                    {errors.statement && (
                      <p className="text-sm text-destructive">{errors.statement.message}</p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label>Bloom Level</Label>
                    <Controller
                      name="bloom_level_id"
                      control={control}
                      render={({ field }) => (
                        <Select value={field.value ?? ""} onValueChange={field.onChange}>
                          <SelectTrigger className="w-full">
                            <SelectValue placeholder="Select bloom level" />
                          </SelectTrigger>
                          <SelectContent>
                            {(bloomDomains ?? []).map((b) => (
                              <SelectItem key={b.id} value={b.id}>
                                {b.name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      )}
                    />
                    {errors.bloom_level_id && (
                      <p className="text-sm text-destructive">{errors.bloom_level_id.message}</p>
                    )}
                  </div>
                </form>
                <DialogFooter showCloseButton>
                  <Button
                    type="submit"
                    form="create-co-form"
                    disabled={isSubmitting || mutation.isPending}
                  >
                    {(isSubmitting || mutation.isPending) && (
                      <Loader2 className="animate-spin" />
                    )}
                    Create
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </PermissionGate>
        }
      />

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-4">
        <div className="w-56">
          <Select
            value={selectedCurriculumId}
            onValueChange={(val) => {
              setSelectedCurriculumId(val ?? "")
              setSelectedCourseId("")
            }}
          >
            <SelectTrigger>
              <SelectValue placeholder="All curricula" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">All curricula</SelectItem>
              {(curricula ?? []).map((c) => (
                <SelectItem key={c.id} value={c.id}>
                  {c.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="w-56">
          <Select
            value={selectedCourseId}
            onValueChange={(v) => setSelectedCourseId(v ?? "")}
            disabled={!selectedCurriculumId}
          >
            <SelectTrigger>
              <SelectValue placeholder="All courses" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">All courses</SelectItem>
              {(courses ?? []).map((c) => (
                <SelectItem key={c.id} value={c.id}>
                  {c.code ? `${c.code} — ` : ""}{c.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <DataTable
        columns={columns}
        data={data ?? []}
        loading={isLoading}
        onRowClick={(row) => router.push(`/course-outcomes/${row.id}`)}
        emptyMessage="No course outcomes found."
      />
    </div>
  )
}
