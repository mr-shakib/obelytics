"use client"

import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { toast } from "sonner"
import { Loader2 } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
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
  name: string
  acronym: string
  department_id: string
  department_name: string
  duration_years: number
  status: string
}

type Department = { id: string; name: string }

const schema = z.object({
  name: z.string().min(2, "Name required"),
  acronym: z.string().min(1, "Acronym required").max(10),
  department_id: z.string().min(1, "Department required"),
  duration_years: z.number().int().min(1).max(10),
})
type FormValues = z.infer<typeof schema>

interface Props {
  id: string
}

export function ProgramDetailClient({ id }: Props) {
  const qc = useQueryClient()
  const [deptId, setDeptId] = useState("")

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
    setValue,
    formState: { errors, isSubmitting, isDirty },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    values: data
      ? {
          name: data.name,
          acronym: data.acronym,
          department_id: data.department_id,
          duration_years: data.duration_years,
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

  const currentDeptId = deptId || data.department_id

  return (
    <div className="max-w-3xl space-y-6">
      <PageHeader
        title={data.name}
        description={`${data.acronym} · ${data.duration_years} years · ${data.department_name}`}
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
                <Label htmlFor="name">Name</Label>
                <Input id="name" {...register("name")} />
                {errors.name && <p className="text-sm text-destructive">{errors.name.message}</p>}
              </div>
              <div className="space-y-2">
                <Label htmlFor="acronym">Acronym</Label>
                <Input id="acronym" {...register("acronym")} />
                {errors.acronym && <p className="text-sm text-destructive">{errors.acronym.message}</p>}
              </div>
              <div className="space-y-2">
                <Label>Department</Label>
                <Select
                  value={currentDeptId}
                  onValueChange={(v) => {
                    if (v == null) return
                    setDeptId(v as string)
                    setValue("department_id", v as string, { shouldValidate: true, shouldDirty: true })
                  }}
                >
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
                {errors.department_id && (
                  <p className="text-sm text-destructive">{errors.department_id.message}</p>
                )}
              </div>
              <div className="space-y-2">
                <Label htmlFor="duration_years">Duration (years)</Label>
                <Input id="duration_years" type="number" min={1} max={10} {...register("duration_years", { valueAsNumber: true })} />
                {errors.duration_years && (
                  <p className="text-sm text-destructive">{errors.duration_years.message}</p>
                )}
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
