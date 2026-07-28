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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogTrigger,
} from "@/components/ui/dialog"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"

type Program = {
  id: string
  title: string
  acronym: string
  department_name?: string
  program_type: string
  minimum_duration_semesters: number
  total_credits: number
  study_mode: string
  status: string
}

type Department = {
  id: string
  name: string
}

type POVersion = {
  id: string
  name: string
  is_active: boolean
}

const PROGRAM_TYPES = [
  { value: "UNDERGRADUATE", label: "Undergraduate" },
  { value: "POSTGRADUATE", label: "Postgraduate" },
  { value: "PHD", label: "PhD" },
]

const STUDY_MODES = [
  { value: "FULL_TIME", label: "Full time" },
  { value: "PART_TIME", label: "Part time" },
]

const schema = z.object({
  title: z.string().min(2, "Title required"),
  acronym: z.string().min(1, "Acronym required").max(20),
  department_id: z.string().min(1, "Department required"),
  program_type: z.enum(["UNDERGRADUATE", "POSTGRADUATE", "PHD"], { message: "Type required" }),
  minimum_duration_semesters: z.number().int().min(1).max(20),
  total_credits: z.number().min(1).max(500),
  study_mode: z.enum(["FULL_TIME", "PART_TIME"], { message: "Mode required" }),
  description: z.string().optional(),
  po_version_id: z.string().optional(),
})
type FormValues = z.infer<typeof schema>

function formatProgramType(type: string) {
  return PROGRAM_TYPES.find((t) => t.value === type)?.label ?? type
}

function formatStudyMode(mode: string) {
  return STUDY_MODES.find((m) => m.value === mode)?.label ?? mode
}

const columns: ColumnDef<Program>[] = [
  { accessorKey: "title", header: "Title" },
  { accessorKey: "acronym", header: "Acronym" },
  { accessorKey: "department_name", header: "Department" },
  {
    accessorKey: "program_type",
    header: "Type",
    cell: ({ row }) => formatProgramType(row.original.program_type),
  },
  {
    accessorKey: "minimum_duration_semesters",
    header: "Min. Duration",
    cell: ({ row }) => `${row.original.minimum_duration_semesters} semesters`,
  },
  { accessorKey: "total_credits", header: "Credits" },
  {
    accessorKey: "study_mode",
    header: "Mode",
    cell: ({ row }) => formatStudyMode(row.original.study_mode),
  },
  {
    accessorKey: "status",
    header: "Status",
    cell: ({ row }) => <StatusBadge status={row.original.status} />,
  },
]

export function ProgramsClient() {
  const [open, setOpen] = useState(false)
  const router = useRouter()
  const qc = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.programs.list(),
    queryFn: async () => {
      const { data } = await apiClient.GET("/programs" as never)
      return ((data as unknown) as { items?: Program[] })?.items ?? ((data as unknown) as Program[]) ?? []
    },
  })

  const { data: departments } = useQuery({
    queryKey: queryKeys.departments.list(),
    queryFn: async () => {
      const { data } = await apiClient.GET("/departments" as never)
      return ((data as unknown) as { items?: Department[] })?.items ?? ((data as unknown) as Department[]) ?? []
    },
  })

  const { data: poVersions = [] } = useQuery({
    queryKey: queryKeys.poVersions.list(),
    queryFn: async () => {
      const { data } = await apiClient.GET("/po-versions" as never)
      return ((data as unknown) as POVersion[]) ?? []
    },
  })

  const {
    register,
    handleSubmit,
    control,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
  })

  const mutation = useMutation({
    mutationFn: async (values: FormValues) => {
      await apiClient.POST("/programs" as never, {
        body: {
          ...values,
          po_version_id: values.po_version_id || undefined,
        },
      } as never)
    },
    onSuccess: () => {
      toast.success("Program created")
      qc.invalidateQueries({ queryKey: queryKeys.programs.all })
      reset()
      setOpen(false)
    },
    onError: () => toast.error("Failed to create program"),
  })

  return (
    <div>
      <PageHeader
        title="Programs"
        description="Manage academic programs."
        actions={
          <PermissionGate permission="program.create">
            <Dialog open={open} onOpenChange={setOpen}>
              <DialogTrigger
                render={
                  <Button>
                    <Plus />
                    New Program
                  </Button>
                }
              />
              <DialogContent className="sm:max-w-lg">
                <DialogHeader>
                  <DialogTitle>Create Program</DialogTitle>
                </DialogHeader>
                <form
                  id="create-prog-form"
                  onSubmit={handleSubmit((v) => mutation.mutate(v))}
                  className="space-y-4 py-2 overflow-y-auto flex-1 min-h-0 pr-1"
                >
                  <div className="space-y-2">
                    <Label htmlFor="prog-title">Title</Label>
                    <Input id="prog-title" {...register("title")} placeholder="Bachelor of Science in CS" />
                    {errors.title && <p className="text-sm text-destructive">{errors.title.message}</p>}
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="prog-acronym">Acronym</Label>
                    <Input id="prog-acronym" {...register("acronym")} placeholder="BSCS" />
                    {errors.acronym && <p className="text-sm text-destructive">{errors.acronym.message}</p>}
                  </div>
                  <div className="space-y-2">
                    <Label>Department</Label>
                    <Controller
                      name="department_id"
                      control={control}
                      render={({ field }) => (
                        <Select value={field.value ?? ""} onValueChange={field.onChange}>
                          <SelectTrigger className="w-full">
                            <SelectValue placeholder="Select department">
                              {field.value ? (departments ?? []).find((d) => d.id === field.value)?.name ?? field.value : undefined}
                            </SelectValue>
                          </SelectTrigger>
                          <SelectContent>
                            {(departments ?? []).map((d) => (
                              <SelectItem key={d.id} value={d.id}>
                                {d.name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      )}
                    />
                    {errors.department_id && (
                      <p className="text-sm text-destructive">{errors.department_id.message}</p>
                    )}
                  </div>
                  <div className="space-y-2">
                    <Label>Type</Label>
                    <Controller
                      name="program_type"
                      control={control}
                      render={({ field }) => (
                        <Select value={field.value ?? ""} onValueChange={field.onChange}>
                          <SelectTrigger className="w-full">
                            <SelectValue placeholder="Select type" />
                          </SelectTrigger>
                          <SelectContent>
                            {PROGRAM_TYPES.map((t) => (
                              <SelectItem key={t.value} value={t.value}>
                                {t.label}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      )}
                    />
                    {errors.program_type && (
                      <p className="text-sm text-destructive">{errors.program_type.message}</p>
                    )}
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="prog-semesters">No. of Semesters</Label>
                      <Input
                        id="prog-semesters"
                        type="number"
                        min={1}
                        max={20}
                        {...register("minimum_duration_semesters", { valueAsNumber: true })}
                        placeholder="8"
                      />
                      {errors.minimum_duration_semesters && (
                        <p className="text-sm text-destructive">{errors.minimum_duration_semesters.message}</p>
                      )}
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="prog-credits">Total Credits</Label>
                      <Input
                        id="prog-credits"
                        type="number"
                        min={1}
                        max={500}
                        step="0.25"
                        {...register("total_credits", { valueAsNumber: true })}
                        placeholder="160"
                      />
                      {errors.total_credits && (
                        <p className="text-sm text-destructive">{errors.total_credits.message}</p>
                      )}
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label>Mode</Label>
                    <Controller
                      name="study_mode"
                      control={control}
                      render={({ field }) => (
                        <Select value={field.value ?? ""} onValueChange={field.onChange}>
                          <SelectTrigger className="w-full">
                            <SelectValue placeholder="Select mode">
                              {field.value ? (STUDY_MODES.find((m) => m.value === field.value)?.label ?? field.value) : undefined}
                            </SelectValue>
                          </SelectTrigger>
                          <SelectContent>
                            {STUDY_MODES.map((m) => (
                              <SelectItem key={m.value} value={m.value}>
                                {m.label}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      )}
                    />
                    {errors.study_mode && (
                      <p className="text-sm text-destructive">{errors.study_mode.message}</p>
                    )}
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="prog-description">Vision</Label>
                    <Textarea id="prog-description" rows={2} {...register("description")} placeholder="Optional" />
                  </div>
                  <div className="space-y-2">
                    <Label>PO Version</Label>
                    <Controller
                      name="po_version_id"
                      control={control}
                      render={({ field }) => (
                        <Select value={field.value ?? ""} onValueChange={(v) => field.onChange(v === "none" ? "" : v)}>
                          <SelectTrigger className="w-full">
                            <SelectValue placeholder="Select PO version (optional)">
                              {field.value ? poVersions.find((v) => v.id === field.value)?.name ?? field.value : undefined}
                            </SelectValue>
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="none">None</SelectItem>
                            {poVersions.map((v) => (
                              <SelectItem key={v.id} value={v.id}>
                                {v.name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      )}
                    />
                    {errors.po_version_id && (
                      <p className="text-sm text-destructive">{errors.po_version_id.message}</p>
                    )}
                  </div>
                </form>
                <DialogFooter showCloseButton>
                  <Button
                    type="submit"
                    form="create-prog-form"
                    disabled={isSubmitting || mutation.isPending}
                  >
                    {(isSubmitting || mutation.isPending) && <Loader2 className="animate-spin" />}
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
        onRowClick={(row) => router.push(`/programs/${row.id}`)}
        emptyMessage="No programs found."
      />
    </div>
  )
}
