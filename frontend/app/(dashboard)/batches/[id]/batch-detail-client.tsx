"use client"

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
import { PageHeader } from "@/components/shared/page-header"
import { StatusBadge } from "@/components/shared/status-badge"
import { PermissionGate } from "@/components/shared/permission-gate"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"

type Batch = {
  id: string
  name: string
  program_name: string
  program_id: string
  intake_year: number
  status: string
}

const schema = z.object({
  name: z.string().min(1, "Name is required"),
  intake_year: z.number().int().min(2000).max(2100),
})
type FormValues = z.infer<typeof schema>

interface Props {
  id: string
}

export function BatchDetailClient({ id }: Props) {
  const qc = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.batches.detail(id),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/batches/${id}` as never)
      return (data as unknown) as Batch
    },
  })

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting, isDirty },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    values: data ? { name: data.name, intake_year: data.intake_year } : undefined,
  })

  const mutation = useMutation({
    mutationFn: async (values: FormValues) => {
      await apiClient.PATCH(`/batches/${id}` as never, { body: values } as never)
    },
    onSuccess: () => {
      toast.success("Batch updated")
      qc.invalidateQueries({ queryKey: queryKeys.batches.detail(id) })
      qc.invalidateQueries({ queryKey: queryKeys.batches.all })
    },
    onError: () => toast.error("Failed to update batch"),
  })

  if (isLoading) return <div className="animate-pulse h-40 bg-muted rounded-md" />
  if (!data) return <p className="text-muted-foreground">Batch not found.</p>

  return (
    <div className="max-w-3xl space-y-6">
      <PageHeader
        title={data.name}
        description={`${data.program_name} · ${data.intake_year}`}
        actions={<StatusBadge status={data.status} />}
      />

      <Card>
        <CardHeader><CardTitle>Details</CardTitle></CardHeader>
        <CardContent className="space-y-2 text-sm">
          <div className="flex gap-4">
            <span className="text-muted-foreground w-32">Program</span>
            <span>{data.program_name}</span>
          </div>
          <div className="flex gap-4">
            <span className="text-muted-foreground w-32">Intake Year</span>
            <span>{data.intake_year}</span>
          </div>
          <div className="flex gap-4">
            <span className="text-muted-foreground w-32">Status</span>
            <StatusBadge status={data.status} />
          </div>
        </CardContent>
      </Card>

      <PermissionGate permission="batch.update">
        <Card>
          <CardHeader><CardTitle>Edit Details</CardTitle></CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit((v) => mutation.mutate(v))} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name">Name</Label>
                <Input id="name" {...register("name")} />
                {errors.name && <p className="text-sm text-destructive">{errors.name.message}</p>}
              </div>
              <div className="space-y-2">
                <Label htmlFor="intake_year">Intake Year</Label>
                <Input id="intake_year" type="number" min={2000} max={2100} {...register("intake_year", { valueAsNumber: true })} />
                {errors.intake_year && <p className="text-sm text-destructive">{errors.intake_year.message}</p>}
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
