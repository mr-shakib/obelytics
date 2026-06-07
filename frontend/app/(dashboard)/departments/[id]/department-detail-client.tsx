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
import { formatDate } from "@/lib/utils"

type Department = {
  id: string
  name: string
  code: string
  status: string
  hod_name?: string
  hod_history?: Array<{ hod_name: string; from_date: string; to_date?: string }>
}

const schema = z.object({
  name: z.string().min(2, "Name must be at least 2 characters"),
  code: z.string().min(1, "Code is required"),
})
type FormValues = z.infer<typeof schema>

interface Props {
  id: string
}

export function DepartmentDetailClient({ id }: Props) {
  const qc = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.departments.detail(id),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/departments/${id}` as never)
      return (data as unknown) as Department
    },
  })

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting, isDirty },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    values: data ? { name: data.name, code: data.code } : undefined,
  })

  const mutation = useMutation({
    mutationFn: async (values: FormValues) => {
      await apiClient.PATCH(`/departments/${id}` as never, { body: values } as never)
    },
    onSuccess: () => {
      toast.success("Department updated")
      qc.invalidateQueries({ queryKey: queryKeys.departments.detail(id) })
      qc.invalidateQueries({ queryKey: queryKeys.departments.all })
    },
    onError: () => toast.error("Failed to update department"),
  })

  if (isLoading) return <div className="animate-pulse h-40 bg-muted rounded-md" />
  if (!data) return <p className="text-muted-foreground">Department not found.</p>

  return (
    <div className="max-w-3xl space-y-6">
      <PageHeader
        title={data.name}
        description={`Code: ${data.code}`}
        actions={<StatusBadge status={data.status} />}
      />

      <PermissionGate permission="department.update">
        <Card>
          <CardHeader>
            <CardTitle>Edit Details</CardTitle>
          </CardHeader>
          <CardContent>
            <form
              onSubmit={handleSubmit((v) => mutation.mutate(v))}
              className="space-y-4"
            >
              <div className="space-y-2">
                <Label htmlFor="name">Name</Label>
                <Input id="name" {...register("name")} />
                {errors.name && (
                  <p className="text-sm text-destructive">{errors.name.message}</p>
                )}
              </div>
              <div className="space-y-2">
                <Label htmlFor="code">Code</Label>
                <Input id="code" {...register("code")} />
                {errors.code && (
                  <p className="text-sm text-destructive">{errors.code.message}</p>
                )}
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

      {data.hod_history && data.hod_history.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>HOD History</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2 text-sm">
              {data.hod_history.map((h, i) => (
                <li key={i} className="flex items-center justify-between border-b pb-2 last:border-0">
                  <span className="font-medium">{h.hod_name}</span>
                  <span className="text-muted-foreground">
                    {formatDate(h.from_date)} — {h.to_date ? formatDate(h.to_date) : "Present"}
                  </span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
