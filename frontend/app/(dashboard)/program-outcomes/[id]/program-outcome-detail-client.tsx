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

type ProgramOutcome = {
  id: string
  code: string
  statement: string
  status: string
  bloom_level_id?: string
  bloom_level_name?: string
  program_id?: string
  program_name?: string
}

type BloomDomain = { id: string; name: string }

const schema = z.object({
  code: z.string().min(1, "Code is required"),
  statement: z.string().min(1, "Statement is required").max(500, "Max 500 characters"),
  bloom_level_id: z.string().min(1, "Bloom level is required"),
})
type FormValues = z.infer<typeof schema>

interface Props {
  id: string
}

export function ProgramOutcomeDetailClient({ id }: Props) {
  const qc = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.programOutcomes.detail(id),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/program-outcomes/${id}` as never)
      return (data as unknown) as ProgramOutcome
    },
  })

  const { data: bloomDomains } = useQuery({
    queryKey: queryKeys.refData.bloomDomains,
    queryFn: async () => {
      const { data } = await apiClient.GET("/ref-data/bloom-domains" as never)
      return ((data as unknown) as { items?: BloomDomain[] })?.items ?? ((data as unknown) as BloomDomain[]) ?? []
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
          code: data.code,
          statement: data.statement,
          bloom_level_id: data.bloom_level_id ?? "",
        }
      : undefined,
  })

  const mutation = useMutation({
    mutationFn: async (values: FormValues) => {
      await apiClient.PATCH(`/program-outcomes/${id}` as never, { body: values } as never)
    },
    onSuccess: () => {
      toast.success("Program Outcome updated")
      qc.invalidateQueries({ queryKey: queryKeys.programOutcomes.detail(id) })
      qc.invalidateQueries({ queryKey: queryKeys.programOutcomes.all })
    },
    onError: () => toast.error("Failed to update Program Outcome"),
  })

  if (isLoading) return <div className="animate-pulse h-40 bg-muted rounded-md" />
  if (!data) return <p className="text-muted-foreground">Program Outcome not found.</p>

  return (
    <div className="max-w-3xl space-y-6">
      <PageHeader
        title={data.code}
        description={data.program_name ? `Program: ${data.program_name}` : undefined}
        actions={<StatusBadge status={data.status} />}
      />

      <Card>
        <CardHeader>
          <CardTitle>Details</CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="space-y-3 text-sm">
            <div className="grid grid-cols-[auto_1fr] gap-x-4 items-start">
              <dt className="text-muted-foreground font-medium">Code</dt>
              <dd>{data.code}</dd>
            </div>
            <div className="grid grid-cols-[auto_1fr] gap-x-4 items-start">
              <dt className="text-muted-foreground font-medium">Statement</dt>
              <dd className="leading-relaxed">{data.statement}</dd>
            </div>
            <div className="grid grid-cols-[auto_1fr] gap-x-4 items-start">
              <dt className="text-muted-foreground font-medium">Bloom Level</dt>
              <dd>{data.bloom_level_name ?? <span className="text-muted-foreground">—</span>}</dd>
            </div>
            <div className="grid grid-cols-[auto_1fr] gap-x-4 items-start">
              <dt className="text-muted-foreground font-medium">Status</dt>
              <dd><StatusBadge status={data.status} /></dd>
            </div>
            {data.program_name && (
              <div className="grid grid-cols-[auto_1fr] gap-x-4 items-start">
                <dt className="text-muted-foreground font-medium">Program</dt>
                <dd>{data.program_name}</dd>
              </div>
            )}
          </dl>
        </CardContent>
      </Card>

      <PermissionGate permission="po.update">
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
                <Label htmlFor="po-code">Code</Label>
                <Input id="po-code" {...register("code")} />
                {errors.code && (
                  <p className="text-sm text-destructive">{errors.code.message}</p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="po-statement">Statement</Label>
                <Textarea
                  id="po-statement"
                  {...register("statement")}
                  rows={4}
                  maxLength={500}
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
    </div>
  )
}
