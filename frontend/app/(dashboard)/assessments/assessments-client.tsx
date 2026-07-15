"use client"

import { useMemo, useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { toast } from "sonner"
import { Plus, Loader2 } from "lucide-react"
import { useRouter, useSearchParams } from "next/navigation"
import type { ColumnDef } from "@tanstack/react-table"

import { DataTable } from "@/components/shared/data-table"
import { PageHeader } from "@/components/shared/page-header"
import { StatusBadge } from "@/components/shared/status-badge"
import { PermissionGate } from "@/components/shared/permission-gate"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
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

type AssessmentType = {
  id: string
  name: string
}

type SectionOffering = {
  id: string
  course_id: string
  section_id: string
}

type Course = { id: string; code: string; title: string }
type Section = { id: string; name: string }

type Assessment = {
  id: string
  section_offering_id: string
  assessment_type_id: string
  name: string
  total_marks: number
  weightage_percent: number
  status: string
}

const schema = z.object({
  title: z.string().min(1, "Title is required"),
  assessment_type_id: z.string().min(1, "Assessment type is required"),
  total_marks: z.number().min(1, "Total marks must be at least 1"),
  weightage: z.number().min(0).max(100, "Weightage must be 0–100"),
  section_offering_id: z.string().min(1, "Section offering is required"),
})
type FormValues = z.infer<typeof schema>

function buildColumns(
  typeNameById: Record<string, string>,
  offeringLabelById: Record<string, string>,
): ColumnDef<Assessment>[] {
  return [
    { accessorKey: "name", header: "Name" },
    {
      accessorKey: "assessment_type_id",
      header: "Type",
      cell: ({ row }) =>
        typeNameById[row.original.assessment_type_id] ?? (
          <span className="text-muted-foreground">—</span>
        ),
    },
    { accessorKey: "total_marks", header: "Total Marks" },
    {
      accessorKey: "weightage_percent",
      header: "Weightage (%)",
      cell: ({ row }) => `${row.original.weightage_percent}%`,
    },
    {
      accessorKey: "section_offering_id",
      header: "Offering",
      cell: ({ row }) =>
        offeringLabelById[row.original.section_offering_id] ?? (
          <span className="text-muted-foreground">—</span>
        ),
    },
    {
      accessorKey: "status",
      header: "Status",
      cell: ({ row }) => <StatusBadge status={row.original.status} />,
    },
  ]
}

export function AssessmentsClient() {
  const [open, setOpen] = useState(false)
  const router = useRouter()
  const qc = useQueryClient()
  const searchParams = useSearchParams()
  const offeringId = searchParams.get("offering_id") ?? undefined

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.assessments.list({ offering_id: offeringId }),
    queryFn: async () => {
      const url = offeringId
        ? `/assessments?section_offering_id=${offeringId}`
        : "/assessments"
      const { data } = await apiClient.GET(url as never)
      return ((data as unknown) as { items?: Assessment[] })?.items ?? ((data as unknown) as Assessment[]) ?? []
    },
  })

  const { data: assessmentTypes = [] } = useQuery({
    queryKey: queryKeys.refData.assessmentTypes,
    queryFn: async () => {
      const { data } = await apiClient.GET("/ref-data/assessment-types" as never)
      return ((data as unknown) as AssessmentType[]) ?? []
    },
  })

  const { data: sectionOfferings = [] } = useQuery({
    queryKey: queryKeys.sectionOfferings.all,
    queryFn: async () => {
      const { data } = await apiClient.GET("/section-offerings" as never)
      return ((data as unknown) as { items?: SectionOffering[] })?.items ?? ((data as unknown) as SectionOffering[]) ?? []
    },
  })

  const { data: courses = [] } = useQuery({
    queryKey: queryKeys.courses.all,
    queryFn: async () => {
      const { data } = await apiClient.GET("/courses" as never)
      return ((data as unknown) as Course[]) ?? []
    },
  })

  const { data: sections = [] } = useQuery({
    queryKey: queryKeys.sections.all,
    queryFn: async () => {
      const { data } = await apiClient.GET("/sections" as never)
      return ((data as unknown) as Section[]) ?? []
    },
  })

  const typeNameById = useMemo(
    () => Object.fromEntries(assessmentTypes.map((t) => [t.id, t.name])),
    [assessmentTypes]
  )
  const offeringLabelById = useMemo(() => {
    const courseById = Object.fromEntries(courses.map((c) => [c.id, c]))
    const sectionById = Object.fromEntries(sections.map((s) => [s.id, s]))
    return Object.fromEntries(
      sectionOfferings.map((o) => {
        const course = courseById[o.course_id]
        const section = sectionById[o.section_id]
        const label = [course?.code, section ? `Section ${section.name}` : null]
          .filter(Boolean)
          .join(" — ")
        return [o.id, label || o.id]
      })
    )
  }, [sectionOfferings, courses, sections])

  const columns = useMemo(
    () => buildColumns(typeNameById, offeringLabelById),
    [typeNameById, offeringLabelById]
  )

  const {
    register,
    handleSubmit,
    setValue,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) })

  const mutation = useMutation({
    mutationFn: async (values: FormValues) => {
      await apiClient.POST("/assessments" as never, {
        body: {
          section_offering_id: values.section_offering_id,
          assessment_type_id: values.assessment_type_id,
          name: values.title,
          total_marks: values.total_marks,
          weightage_percent: values.weightage,
        },
      } as never)
    },
    onSuccess: () => {
      toast.success("Assessment created")
      qc.invalidateQueries({ queryKey: queryKeys.assessments.all })
      reset()
      setOpen(false)
    },
    onError: () => toast.error("Failed to create assessment"),
  })

  return (
    <div>
      <PageHeader
        title="Assessments"
        description="Manage course assessments."
        actions={
          <PermissionGate permission="assessment.configure">
            <Dialog open={open} onOpenChange={setOpen}>
              <DialogTrigger render={<Button />}>
                <Plus className="h-4 w-4" />
                New Assessment
              </DialogTrigger>
              <DialogContent className="sm:max-w-md">
                <DialogHeader>
                  <DialogTitle>Create Assessment</DialogTitle>
                </DialogHeader>
                <form
                  id="create-assessment-form"
                  onSubmit={handleSubmit((v) => mutation.mutate(v))}
                  className="space-y-4 py-2"
                >
                  <div className="space-y-2">
                    <Label htmlFor="title">Title</Label>
                    <Input id="title" {...register("title")} placeholder="Mid-term Exam" />
                    {errors.title && (
                      <p className="text-sm text-destructive">{errors.title.message}</p>
                    )}
                  </div>
                  <div className="space-y-2">
                    <Label>Assessment Type</Label>
                    <Select onValueChange={(v) => v != null && setValue("assessment_type_id", v as string)}>
                      <SelectTrigger className="w-full">
                        <SelectValue placeholder="Select type" />
                      </SelectTrigger>
                      <SelectContent>
                        {assessmentTypes.map((t) => (
                          <SelectItem key={t.id} value={t.id}>
                            {t.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {errors.assessment_type_id && (
                      <p className="text-sm text-destructive">{errors.assessment_type_id.message}</p>
                    )}
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="total_marks">Total Marks</Label>
                      <Input id="total_marks" type="number" min={1} {...register("total_marks", { valueAsNumber: true })} />
                      {errors.total_marks && (
                        <p className="text-sm text-destructive">{errors.total_marks.message}</p>
                      )}
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="weightage">Weightage (%)</Label>
                      <Input
                        id="weightage"
                        type="number"
                        min={0}
                        max={100}
                        {...register("weightage", { valueAsNumber: true })}
                      />
                      {errors.weightage && (
                        <p className="text-sm text-destructive">{errors.weightage.message}</p>
                      )}
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label>Section Offering</Label>
                    <Select onValueChange={(v) => v != null && setValue("section_offering_id", v as string)}>
                      <SelectTrigger className="w-full">
                        <SelectValue placeholder="Select section offering" />
                      </SelectTrigger>
                      <SelectContent>
                        {sectionOfferings.map((s) => (
                          <SelectItem key={s.id} value={s.id}>
                            {offeringLabelById[s.id] ?? s.id}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {errors.section_offering_id && (
                      <p className="text-sm text-destructive">
                        {errors.section_offering_id.message}
                      </p>
                    )}
                  </div>
                </form>
                <DialogFooter showCloseButton>
                  <Button
                    type="submit"
                    form="create-assessment-form"
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
      <DataTable
        columns={columns}
        data={data ?? []}
        loading={isLoading}
        onRowClick={(row) => router.push(`/assessments/${row.id}`)}
        emptyMessage="No assessments found."
      />
    </div>
  )
}
