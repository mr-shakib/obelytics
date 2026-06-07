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

type SectionOffering = {
  id: string
  code: string
  course_name: string
  batch_name: string
  term_name: string
  section: string
  status: string
}

type Course = { id: string; code: string; title: string }
type Batch = { id: string; name: string }
type AcademicTerm = { id: string; name: string }

const schema = z.object({
  course_id: z.string().min(1, "Course is required"),
  batch_id: z.string().min(1, "Batch is required"),
  academic_term_id: z.string().min(1, "Academic term is required"),
  section: z.string().min(1, "Section is required"),
})
type FormValues = z.infer<typeof schema>

const columns: ColumnDef<SectionOffering>[] = [
  { accessorKey: "code", header: "Code" },
  { accessorKey: "course_name", header: "Course" },
  { accessorKey: "batch_name", header: "Batch" },
  { accessorKey: "term_name", header: "Term" },
  { accessorKey: "section", header: "Section" },
  {
    accessorKey: "status",
    header: "Status",
    cell: ({ row }) => <StatusBadge status={row.original.status} />,
  },
]

export function SectionOfferingsClient() {
  const [open, setOpen] = useState(false)
  const qc = useQueryClient()
  const router = useRouter()

  const { data: offerings = [], isLoading } = useQuery({
    queryKey: queryKeys.sectionOfferings.all,
    queryFn: async () => {
      const { data } = await apiClient.GET("/section-offerings" as never)
      return ((data as unknown) as SectionOffering[]) ?? []
    },
  })

  const { data: courses = [] } = useQuery({
    queryKey: queryKeys.courses.all,
    queryFn: async () => {
      const { data } = await apiClient.GET("/courses" as never)
      return ((data as unknown) as Course[]) ?? []
    },
  })

  const { data: batches = [] } = useQuery({
    queryKey: queryKeys.batches.all,
    queryFn: async () => {
      const { data } = await apiClient.GET("/batches" as never)
      return ((data as unknown) as Batch[]) ?? []
    },
  })

  const { data: terms = [] } = useQuery({
    queryKey: queryKeys.academicTerms.all,
    queryFn: async () => {
      const { data } = await apiClient.GET("/academic-terms" as never)
      return ((data as unknown) as AcademicTerm[]) ?? []
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
      await apiClient.POST("/section-offerings" as never, { body: values } as never)
    },
    onSuccess: () => {
      toast.success("Section offering created")
      qc.invalidateQueries({ queryKey: queryKeys.sectionOfferings.all })
      setOpen(false)
      reset()
    },
    onError: () => toast.error("Failed to create section offering"),
  })

  return (
    <div>
      <PageHeader
        title="Section Offerings"
        description="Manage course section offerings per term."
        actions={
          <PermissionGate permission="curriculum.read">
            <Dialog open={open} onOpenChange={setOpen}>
              <DialogTrigger render={<Button />}>
                <Plus className="h-4 w-4" />
                New Offering
              </DialogTrigger>
              <DialogContent className="sm:max-w-md">
                <DialogHeader>
                  <DialogTitle>Create Section Offering</DialogTitle>
                </DialogHeader>
                <form
                  id="create-offering-form"
                  onSubmit={handleSubmit((v) => mutation.mutate(v))}
                  className="space-y-4 py-2"
                >
                  <div className="space-y-2">
                    <Label>Course</Label>
                    <Select onValueChange={(v) => v != null && setValue("course_id", v as string)}>
                      <SelectTrigger className="w-full">
                        <SelectValue placeholder="Select course" />
                      </SelectTrigger>
                      <SelectContent>
                        {courses.map((c) => (
                          <SelectItem key={c.id} value={c.id}>
                            {c.code} — {c.title}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {errors.course_id && (
                      <p className="text-sm text-destructive">{errors.course_id.message}</p>
                    )}
                  </div>
                  <div className="space-y-2">
                    <Label>Batch</Label>
                    <Select onValueChange={(v) => v != null && setValue("batch_id", v as string)}>
                      <SelectTrigger className="w-full">
                        <SelectValue placeholder="Select batch" />
                      </SelectTrigger>
                      <SelectContent>
                        {batches.map((b) => (
                          <SelectItem key={b.id} value={b.id}>
                            {b.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {errors.batch_id && (
                      <p className="text-sm text-destructive">{errors.batch_id.message}</p>
                    )}
                  </div>
                  <div className="space-y-2">
                    <Label>Academic Term</Label>
                    <Select onValueChange={(v) => v != null && setValue("academic_term_id", v as string)}>
                      <SelectTrigger className="w-full">
                        <SelectValue placeholder="Select term" />
                      </SelectTrigger>
                      <SelectContent>
                        {terms.map((t) => (
                          <SelectItem key={t.id} value={t.id}>
                            {t.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {errors.academic_term_id && (
                      <p className="text-sm text-destructive">{errors.academic_term_id.message}</p>
                    )}
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="section">Section</Label>
                    <Input id="section" {...register("section")} placeholder="e.g. A" />
                    {errors.section && (
                      <p className="text-sm text-destructive">{errors.section.message}</p>
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
                    form="create-offering-form"
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
        data={offerings}
        loading={isLoading}
        onRowClick={(row) => router.push(`/section-offerings/${row.id}`)}
        emptyMessage="No section offerings found."
      />
    </div>
  )
}
