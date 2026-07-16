"use client"

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useForm, Controller } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { toast } from "sonner"
import { Loader2, GitBranch } from "lucide-react"
import Link from "next/link"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { PageHeader } from "@/components/shared/page-header"
import { PermissionGate } from "@/components/shared/permission-gate"
import { BloomLevelCheckboxGroup, sortBloomLevelIds } from "@/components/shared/bloom-level-checkbox-group"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"

type CourseOutcome = {
  id: string
  code: string
  statement: string
  course_id: string
  bloom_level_ids: string[]
  course_name?: string
  curriculum_name?: string
}

type BloomDomain = { id: string; name: string }
type BloomLevel = { id: string; code: string; name: string; bloom_domain_id: string; order_index: number }

const schema = z.object({
  code: z.string().min(1, "Code is required"),
  statement: z.string().min(20, "Statement must be at least 20 characters"),
  bloom_level_ids: z.array(z.string()),
})
type FormValues = z.infer<typeof schema>

interface Props {
  id: string
}

export function CourseOutcomeDetailClient({ id }: Props) {
  const qc = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.courseOutcomes.detail(id),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/course-outcomes/${id}` as never)
      return (data as unknown) as CourseOutcome
    },
  })

  const { data: bloomDomains = [] } = useQuery({
    queryKey: queryKeys.refData.bloomDomains,
    queryFn: async () => {
      const { data } = await apiClient.GET("/ref-data/bloom-domains" as never)
      return ((data as unknown) as { items?: BloomDomain[] })?.items ?? ((data as unknown) as BloomDomain[]) ?? []
    },
  })

  const { data: bloomLevels = [] } = useQuery({
    queryKey: queryKeys.refData.bloomLevels,
    queryFn: async () => {
      const { data } = await apiClient.GET("/ref-data/bloom-levels" as never)
      return ((data as unknown) as BloomLevel[]) ?? []
    },
  })

  const bloomMap = new Map(bloomLevels.map((b) => [b.id, `${b.code} — ${b.name}`]))

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
          bloom_level_ids: data.bloom_level_ids ?? [],
        }
      : undefined,
  })

  const updateMutation = useMutation({
    mutationFn: async (values: FormValues) => {
      await apiClient.PATCH(`/course-outcomes/${id}` as never, { body: values } as never)
    },
    onSuccess: () => {
      toast.success("Course Outcome updated")
      qc.invalidateQueries({ queryKey: queryKeys.courseOutcomes.detail(id) })
      qc.invalidateQueries({ queryKey: queryKeys.courseOutcomes.all })
    },
    onError: () => toast.error("Failed to update Course Outcome"),
  })

  if (isLoading) return <div className="animate-pulse h-40 bg-muted rounded-md" />
  if (!data) return <p className="text-muted-foreground">Course Outcome not found.</p>

  return (
    <div className="max-w-3xl space-y-6">
      <PageHeader
        title={data.code}
        description={data.course_name ?? undefined}
        actions={
          <Button
            variant="outline"
            size="sm"
            nativeButton={false}
            render={<Link href={`/courses/${data.course_id}/mappings#co-po-mapping`} />}
          >
            <GitBranch />
            CO-PO Mapping
          </Button>
        }
      />

      {/* Details */}
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
              <dd>
                {data.bloom_level_ids.length > 0 ? (
                  <div className="flex flex-wrap gap-1">
                    {sortBloomLevelIds(data.bloom_level_ids, bloomLevels, bloomDomains).map((bid) => (
                      <Badge key={bid} variant="secondary" className="font-normal">
                        {bloomMap.get(bid) ?? bid}
                      </Badge>
                    ))}
                  </div>
                ) : (
                  <span className="text-muted-foreground">—</span>
                )}
              </dd>
            </div>
            {data.course_name && (
              <div className="grid grid-cols-[auto_1fr] gap-x-4 items-start">
                <dt className="text-muted-foreground font-medium">Course</dt>
                <dd>{data.course_name}</dd>
              </div>
            )}
            {data.curriculum_name && (
              <div className="grid grid-cols-[auto_1fr] gap-x-4 items-start">
                <dt className="text-muted-foreground font-medium">Curriculum</dt>
                <dd>{data.curriculum_name}</dd>
              </div>
            )}
          </dl>
        </CardContent>
      </Card>

      {/* Edit form */}
      <PermissionGate permission="co.update">
        <Card>
          <CardHeader>
            <CardTitle>Edit Details</CardTitle>
          </CardHeader>
          <CardContent>
            <form
              onSubmit={handleSubmit((v) => updateMutation.mutate(v))}
              className="space-y-4"
            >
              <div className="space-y-2">
                <Label htmlFor="co-code">Code</Label>
                <Input id="co-code" {...register("code")} />
                {errors.code && (
                  <p className="text-sm text-destructive">{errors.code.message}</p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="co-statement">Statement</Label>
                <Textarea id="co-statement" {...register("statement")} rows={4} />
                {errors.statement && (
                  <p className="text-sm text-destructive">{errors.statement.message}</p>
                )}
              </div>

              <div className="space-y-2">
                <Label>Bloom Level <span className="text-muted-foreground font-normal">(optional, multiple allowed)</span></Label>
                <Controller
                  name="bloom_level_ids"
                  control={control}
                  render={({ field }) => (
                    <BloomLevelCheckboxGroup
                      bloomDomains={bloomDomains}
                      bloomLevels={bloomLevels}
                      value={field.value ?? []}
                      onChange={field.onChange}
                    />
                  )}
                />
                {errors.bloom_level_ids && (
                  <p className="text-sm text-destructive">{errors.bloom_level_ids.message}</p>
                )}
              </div>

              <Button
                type="submit"
                disabled={!isDirty || isSubmitting || updateMutation.isPending}
              >
                {(isSubmitting || updateMutation.isPending) && (
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
