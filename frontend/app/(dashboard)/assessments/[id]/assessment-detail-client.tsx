"use client"

import Link from "next/link"
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

type Assessment = {
  id: string
  title: string
  assessment_type: string
  total_marks: number
  weightage: number
  status: string
  section_offering_id: string
}

const schema = z.object({
  title: z.string().min(1, "Title is required"),
  total_marks: z.number().min(1, "Must be at least 1"),
  weightage: z.number().min(0).max(100, "Must be 0–100"),
})
type FormValues = z.infer<typeof schema>

interface Props {
  id: string
}

export function AssessmentDetailClient({ id }: Props) {
  const qc = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.assessments.detail(id),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/assessment/assessments/${id}` as never)
      return (data as unknown) as Assessment
    },
  })

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting, isDirty },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    values: data
      ? { title: data.title, total_marks: data.total_marks, weightage: data.weightage }
      : undefined,
  })

  const mutation = useMutation({
    mutationFn: async (values: FormValues) => {
      await apiClient.PATCH(`/assessment/assessments/${id}` as never, { body: values } as never)
    },
    onSuccess: () => {
      toast.success("Assessment updated")
      qc.invalidateQueries({ queryKey: queryKeys.assessments.detail(id) })
      qc.invalidateQueries({ queryKey: queryKeys.assessments.all })
    },
    onError: () => toast.error("Failed to update assessment"),
  })

  if (isLoading) return <div className="animate-pulse h-40 bg-muted rounded-md" />
  if (!data) return <p className="text-muted-foreground">Assessment not found.</p>

  const isLocked = data.status === "LOCKED"

  return (
    <div className="max-w-3xl space-y-6">
      <PageHeader
        title={data.title}
        description={`Type: ${data.assessment_type} · Total: ${data.total_marks} marks · Weightage: ${data.weightage}%`}
        actions={
          <div className="flex items-center gap-2">
            <StatusBadge status={data.status} />
            <PermissionGate permission="marks.enter">
              <Button nativeButton={false} render={<Link href={`/assessments/${id}/marks`} />}>
                Enter Marks
              </Button>
            </PermissionGate>
          </div>
        }
      />

      {!isLocked && (
        <PermissionGate permission="assessment.configure">
          <Card>
            <CardHeader>
              <CardTitle>Edit Assessment</CardTitle>
            </CardHeader>
            <CardContent>
              <form
                onSubmit={handleSubmit((v) => mutation.mutate(v))}
                className="space-y-4"
              >
                <div className="space-y-2">
                  <Label htmlFor="title">Title</Label>
                  <Input id="title" {...register("title")} />
                  {errors.title && (
                    <p className="text-sm text-destructive">{errors.title.message}</p>
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
                <Button
                  type="submit"
                  disabled={!isDirty || isSubmitting || mutation.isPending}
                >
                  {(isSubmitting || mutation.isPending) && (
                    <Loader2 className="animate-spin" />
                  )}
                  Save Changes
                </Button>
              </form>
            </CardContent>
          </Card>
        </PermissionGate>
      )}
    </div>
  )
}
