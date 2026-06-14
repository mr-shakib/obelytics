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
  bloom_domain_id?: string | null
  po_type?: string | null
  program_id?: string
  program_name?: string
}

type BloomDomain = { id: string; name: string }
type POType = { id: string; name: string; is_active: boolean }

const NONE_PO_TYPE = "none"

const schema = z.object({
  code: z.string().min(1, "Code is required"),
  statement: z.string().min(1, "Statement is required").max(500, "Max 500 characters"),
  bloom_domain_id: z.string().optional(),
  po_type: z.string().optional(),
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

  const { data: bloomDomains = [] } = useQuery({
    queryKey: queryKeys.refData.bloomDomains,
    queryFn: async () => {
      const { data } = await apiClient.GET("/ref-data/bloom-domains" as never)
      return ((data as unknown) as { items?: BloomDomain[] })?.items ?? ((data as unknown) as BloomDomain[]) ?? []
    },
  })

  const { data: poTypes = [] } = useQuery({
    queryKey: queryKeys.refData.poTypes,
    queryFn: async () => {
      const { data } = await apiClient.GET("/ref-data/po-types" as never)
      return ((data as unknown) as { items?: POType[] })?.items ?? ((data as unknown) as POType[]) ?? []
    },
  })

  const bloomDomainById = Object.fromEntries(bloomDomains.map((d) => [d.id, d]))
  const activePoTypes = poTypes.filter((t) => t.is_active)

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
          bloom_domain_id: data.bloom_domain_id ?? "",
          po_type: data.po_type ?? NONE_PO_TYPE,
        }
      : undefined,
  })

  const mutation = useMutation({
    mutationFn: async (values: FormValues) => {
      await apiClient.PATCH(`/program-outcomes/${id}` as never, {
        body: {
          code: values.code,
          statement: values.statement,
          ...(values.bloom_domain_id ? { bloom_domain_id: values.bloom_domain_id } : {}),
          po_type: values.po_type === NONE_PO_TYPE ? undefined : values.po_type,
        },
      } as never)
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
              <dt className="text-muted-foreground font-medium">Bloom Domain</dt>
              <dd>{bloomDomainById[data.bloom_domain_id ?? ""]?.name ?? <span className="text-muted-foreground">—</span>}</dd>
            </div>
            <div className="grid grid-cols-[auto_1fr] gap-x-4 items-start">
              <dt className="text-muted-foreground font-medium">PO Type</dt>
              <dd>{data.po_type ?? <span className="text-muted-foreground">—</span>}</dd>
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
                <Label>Bloom Domain</Label>
                <Controller
                  name="bloom_domain_id"
                  control={control}
                  render={({ field }) => (
                    <Select value={field.value ?? ""} onValueChange={field.onChange}>
                      <SelectTrigger className="w-full">
                        <SelectValue placeholder="Select bloom domain" />
                      </SelectTrigger>
                      <SelectContent>
                        {bloomDomains.map((domain) => (
                          <SelectItem key={domain.id} value={domain.id}>
                            {domain.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  )}
                />
                {errors.bloom_domain_id && (
                  <p className="text-sm text-destructive">{errors.bloom_domain_id.message}</p>
                )}
              </div>

              <div className="space-y-2">
                <Label>PO Type</Label>
                <Controller
                  name="po_type"
                  control={control}
                  render={({ field }) => (
                    <Select value={field.value ?? NONE_PO_TYPE} onValueChange={field.onChange}>
                      <SelectTrigger className="w-full">
                        <SelectValue placeholder="Select PO type" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value={NONE_PO_TYPE}>— None —</SelectItem>
                        {activePoTypes.map((t) => (
                          <SelectItem key={t.id} value={t.name}>
                            {t.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  )}
                />
                {errors.po_type && (
                  <p className="text-sm text-destructive">{errors.po_type.message}</p>
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
