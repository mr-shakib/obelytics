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
import { formatDate } from "@/lib/utils"

type Department = {
  id: string
  name: string
  short_name: string
  year_established?: number | null
  description?: string | null
  vision?: string | null
  mission?: string | null
  status: string
  current_hod?: { user_id: string; full_name: string } | null
  hod_history?: Array<{ user_id: string; full_name: string; effective_from: string; effective_to?: string | null }>
}

type User = { id: string; full_name: string }

const schema = z.object({
  name: z.string().min(2, "Name must be at least 2 characters"),
  short_name: z.string().min(1, "Short name is required").max(30, "Short name too long"),
  year_established: z.number().int().min(1800).max(2100).optional(),
  description: z.string().optional(),
  vision: z.string().optional(),
  mission: z.string().optional(),
})
type FormValues = z.infer<typeof schema>

interface Props {
  id: string
}

export function DepartmentDetailClient({ id }: Props) {
  const qc = useQueryClient()
  const [hodId, setHodId] = useState("")

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.departments.detail(id),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/departments/${id}` as never)
      return (data as unknown) as Department
    },
  })

  const { data: users } = useQuery({
    queryKey: queryKeys.users.list(),
    queryFn: async () => {
      const { data } = await apiClient.GET("/users" as never)
      return ((data as unknown) as User[]) ?? []
    },
  })

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting, isDirty },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    values: data
      ? {
          name: data.name,
          short_name: data.short_name,
          year_established: data.year_established ?? undefined,
          description: data.description ?? "",
          vision: data.vision ?? "",
          mission: data.mission ?? "",
        }
      : undefined,
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

  const assignHeadMutation = useMutation({
    mutationFn: async (user_id: string) => {
      await apiClient.POST(`/departments/${id}/head` as never, { body: { user_id } } as never)
    },
    onSuccess: () => {
      toast.success("Head of Department assigned")
      qc.invalidateQueries({ queryKey: queryKeys.departments.detail(id) })
      setHodId("")
    },
    onError: () => toast.error("Failed to assign Head of Department"),
  })

  if (isLoading) return <div className="animate-pulse h-40 bg-muted rounded-md" />
  if (!data) return <p className="text-muted-foreground">Department not found.</p>

  return (
    <div className="max-w-3xl space-y-6">
      <PageHeader
        title={data.name}
        description={`Short name: ${data.short_name}`}
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
                <Label htmlFor="short_name">Short Name</Label>
                <Input id="short_name" {...register("short_name")} />
                {errors.short_name && (
                  <p className="text-sm text-destructive">{errors.short_name.message}</p>
                )}
              </div>
              <div className="space-y-2">
                <Label htmlFor="year_established">Year Established</Label>
                <Input
                  id="year_established"
                  type="number"
                  {...register("year_established", { valueAsNumber: true })}
                />
                {errors.year_established && (
                  <p className="text-sm text-destructive">{errors.year_established.message}</p>
                )}
              </div>
              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <Textarea id="description" rows={2} {...register("description")} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="mission">Mission</Label>
                <Textarea id="mission" rows={2} {...register("mission")} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="vision">Vision</Label>
                <Textarea id="vision" rows={2} {...register("vision")} />
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

      <Card>
        <CardHeader>
          <CardTitle>Head of Department</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm">
            Current:{" "}
            <span className="font-medium">{data.current_hod?.full_name ?? "Not assigned"}</span>
          </p>

          <PermissionGate permission="department.update">
            <div className="flex items-end gap-2">
              <div className="flex-1 space-y-2">
                <Label>Assign new Head of Department</Label>
                <Select value={hodId} onValueChange={(v) => setHodId((v as string) ?? "")}>
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Select a user">
                      {(value: string) => value
                        ? ((users ?? []).find((u) => u.id === value)?.full_name ?? value)
                        : null}
                    </SelectValue>
                  </SelectTrigger>
                  <SelectContent>
                    {(users ?? []).map((u) => (
                      <SelectItem key={u.id} value={u.id}>
                        {u.full_name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <Button
                disabled={!hodId || assignHeadMutation.isPending}
                onClick={() => hodId && assignHeadMutation.mutate(hodId)}
              >
                {assignHeadMutation.isPending && <Loader2 className="animate-spin" />}
                Assign
              </Button>
            </div>
          </PermissionGate>

          {data.hod_history && data.hod_history.length > 0 && (
            <div>
              <p className="mb-2 text-sm font-medium">History</p>
              <ul className="space-y-2 text-sm">
                {data.hod_history.map((h, i) => (
                  <li key={i} className="flex items-center justify-between border-b pb-2 last:border-0">
                    <span className="font-medium">{h.full_name}</span>
                    <span className="text-muted-foreground">
                      {formatDate(h.effective_from)} — {h.effective_to ? formatDate(h.effective_to) : "Present"}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
