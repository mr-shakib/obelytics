"use client"

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useForm, Controller } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { toast } from "sonner"
import { Loader2 } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
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
import { PageHeader } from "@/components/shared/page-header"
import { StatusBadge } from "@/components/shared/status-badge"
import { PermissionGate } from "@/components/shared/permission-gate"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"

type Program = {
  id: string
  title: string
  acronym: string
  department_id: string
  department_name: string
  program_type: string
  minimum_duration_semesters: number
  total_credits: number
  study_mode: string
  description?: string | null
  status: string
}

type Department = { id: string; name: string }

const PROGRAM_TYPES = [
  { value: "UNDERGRADUATE", label: "Undergraduate" },
  { value: "POSTGRADUATE", label: "Postgraduate" },
  { value: "PHD", label: "PhD" },
]

const STUDY_MODES = [
  { value: "FULL_TIME", label: "Full time" },
  { value: "PART_TIME", label: "Part time" },
]

function formatProgramType(type: string) {
  return PROGRAM_TYPES.find((t) => t.value === type)?.label ?? type
}

function formatStudyMode(mode: string) {
  return STUDY_MODES.find((m) => m.value === mode)?.label ?? mode
}

const schema = z.object({
  title: z.string().min(2, "Title required"),
  acronym: z.string().min(1, "Acronym required").max(20),
  department_id: z.string().min(1, "Department required"),
  program_type: z.enum(["UNDERGRADUATE", "POSTGRADUATE", "PHD"], { message: "Type required" }),
  minimum_duration_semesters: z.number().int().min(1).max(20),
  total_credits: z.number().int().min(1).max(500),
  study_mode: z.enum(["FULL_TIME", "PART_TIME"], { message: "Mode required" }),
  description: z.string().optional(),
})
type FormValues = z.infer<typeof schema>

interface Props {
  id: string
}

export function ProgramDetailClient({ id }: Props) {
  const qc = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.programs.detail(id),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/programs/${id}` as never)
      return (data as unknown) as Program
    },
  })

  const { data: departments } = useQuery({
    queryKey: queryKeys.departments.list(),
    queryFn: async () => {
      const { data } = await apiClient.GET("/departments" as never)
      return ((data as unknown) as { items?: Department[] })?.items ?? ((data as unknown) as Department[]) ?? []
    },
  })

  const {
    register,
    handleSubmit,
    control,
    formState: { errors, isSubmitting, isDirty },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    values: data
      ? {
          title: data.title,
          acronym: data.acronym,
          department_id: data.department_id,
          program_type: data.program_type as FormValues["program_type"],
          minimum_duration_semesters: data.minimum_duration_semesters,
          total_credits: data.total_credits,
          study_mode: data.study_mode as FormValues["study_mode"],
          description: data.description ?? "",
        }
      : undefined,
  })

  const mutation = useMutation({
    mutationFn: async (values: FormValues) => {
      await apiClient.PATCH(`/programs/${id}` as never, { body: values } as never)
    },
    onSuccess: () => {
      toast.success("Program updated")
      qc.invalidateQueries({ queryKey: queryKeys.programs.detail(id) })
      qc.invalidateQueries({ queryKey: queryKeys.programs.all })
    },
    onError: () => toast.error("Failed to update program"),
  })

  if (isLoading) return <div className="animate-pulse h-40 bg-muted rounded-md" />
  if (!data) return <p className="text-muted-foreground">Program not found.</p>

  return (
    <div className="max-w-3xl space-y-6">
      <PageHeader
        title={data.title}
        description={`${data.acronym} · ${formatProgramType(data.program_type)} · ${data.department_name}`}
        actions={<StatusBadge status={data.status} />}
      />

      <PermissionGate permission="program.update">
        <Card>
          <CardHeader>
            <CardTitle>Edit Details</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit((v) => mutation.mutate(v))} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="title">Title</Label>
                <Input id="title" {...register("title")} />
                {errors.title && <p className="text-sm text-destructive">{errors.title.message}</p>}
              </div>
              <div className="space-y-2">
                <Label htmlFor="acronym">Acronym</Label>
                <Input id="acronym" {...register("acronym")} />
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
                        <SelectValue placeholder="Select department" />
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
                  <Label htmlFor="minimum_duration_semesters">No. of Semesters</Label>
                  <Input
                    id="minimum_duration_semesters"
                    type="number"
                    min={1}
                    max={20}
                    {...register("minimum_duration_semesters", { valueAsNumber: true })}
                  />
                  {errors.minimum_duration_semesters && (
                    <p className="text-sm text-destructive">{errors.minimum_duration_semesters.message}</p>
                  )}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="total_credits">Total Credits</Label>
                  <Input
                    id="total_credits"
                    type="number"
                    min={1}
                    max={500}
                    {...register("total_credits", { valueAsNumber: true })}
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
                        <SelectValue placeholder="Select mode" />
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
                <Label htmlFor="description">Description</Label>
                <Textarea id="description" rows={2} {...register("description")} />
              </div>
              <Button type="submit" disabled={!isDirty || isSubmitting || mutation.isPending}>
                {(isSubmitting || mutation.isPending) && <Loader2 className="animate-spin" />}
                Save Changes
              </Button>
            </form>
          </CardContent>
        </Card>
      </PermissionGate>
    </div>
  )
}
