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
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { PageHeader } from "@/components/shared/page-header"
import { StatusBadge } from "@/components/shared/status-badge"
import { PermissionGate } from "@/components/shared/permission-gate"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"
import { cn } from "@/lib/utils"

type CourseOutcome = {
  id: string
  code: string
  statement: string
  status: string
  course_id: string
  bloom_level_id?: string
  bloom_level_name?: string
  course_name?: string
  curriculum_name?: string
}

type BloomDomain = { id: string; name: string }
type BloomLevel = { id: string; code: string; name: string; bloom_domain_id: string; order_index: number }

const CO_STATUSES = [
  "DRAFT",
  "SUBMITTED",
  "UNDER_REVIEW",
  "APPROVED",
  "PUBLISHED",
  "LOCKED",
] as const

const schema = z.object({
  code: z.string().min(1, "Code is required"),
  statement: z.string().min(20, "Statement must be at least 20 characters"),
  bloom_level_id: z.string().min(1, "Bloom level is required"),
})
type FormValues = z.infer<typeof schema>

function COStatusStepper({ status }: { status: string }) {
  const currentIndex = CO_STATUSES.indexOf(status as (typeof CO_STATUSES)[number])

  return (
    <div className="flex items-center gap-0 overflow-x-auto pb-1">
      {CO_STATUSES.map((s, i) => {
        const isPast = i < currentIndex
        const isCurrent = i === currentIndex
        const isLast = i === CO_STATUSES.length - 1

        return (
          <div key={s} className="flex items-center shrink-0">
            <div className="flex flex-col items-center gap-1">
              <div
                className={cn(
                  "h-2.5 w-2.5 rounded-full border-2 transition-colors",
                  isPast && "bg-primary border-primary",
                  isCurrent && "bg-primary border-primary ring-2 ring-primary/20",
                  !isPast && !isCurrent && "bg-background border-muted-foreground/30"
                )}
              />
              <span
                className={cn(
                  "text-[0.65rem] font-medium whitespace-nowrap",
                  isCurrent ? "text-primary" : "text-muted-foreground"
                )}
              >
                {s.replace(/_/g, " ")}
              </span>
            </div>
            {!isLast && (
              <div
                className={cn(
                  "h-0.5 w-8 mb-4 mx-0.5 transition-colors",
                  isPast ? "bg-primary" : "bg-muted-foreground/20"
                )}
              />
            )}
          </div>
        )
      })}
    </div>
  )
}

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

  const bloomLevelById = Object.fromEntries(bloomLevels.map((l) => [l.id, l]))

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

  const submitMutation = useMutation({
    mutationFn: async () => {
      await apiClient.POST(`/course-outcomes/${id}/submit` as never, {} as never)
    },
    onSuccess: () => {
      toast.success("Course Outcome submitted for review")
      qc.invalidateQueries({ queryKey: queryKeys.courseOutcomes.detail(id) })
      qc.invalidateQueries({ queryKey: queryKeys.courseOutcomes.all })
    },
    onError: () => toast.error("Failed to submit Course Outcome"),
  })

  const approveMutation = useMutation({
    mutationFn: async () => {
      await apiClient.POST(`/course-outcomes/${id}/approve` as never, {} as never)
    },
    onSuccess: () => {
      toast.success("Course Outcome approved")
      qc.invalidateQueries({ queryKey: queryKeys.courseOutcomes.detail(id) })
      qc.invalidateQueries({ queryKey: queryKeys.courseOutcomes.all })
    },
    onError: () => toast.error("Failed to approve Course Outcome"),
  })

  const publishMutation = useMutation({
    mutationFn: async () => {
      await apiClient.POST(`/course-outcomes/${id}/publish` as never, {} as never)
    },
    onSuccess: () => {
      toast.success("Course Outcome published")
      qc.invalidateQueries({ queryKey: queryKeys.courseOutcomes.detail(id) })
      qc.invalidateQueries({ queryKey: queryKeys.courseOutcomes.all })
    },
    onError: () => toast.error("Failed to publish Course Outcome"),
  })

  if (isLoading) return <div className="animate-pulse h-40 bg-muted rounded-md" />
  if (!data) return <p className="text-muted-foreground">Course Outcome not found.</p>

  const isDraft = data.status === "DRAFT"
  const isUnderReview = data.status === "UNDER_REVIEW"
  const isApproved = data.status === "APPROVED"

  return (
    <div className="max-w-3xl space-y-6">
      <PageHeader
        title={data.code}
        description={data.course_name ?? undefined}
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              nativeButton={false}
              render={<Link href={`/mappings/co-po?course_id=${data.course_id}`} />}
            >
              <GitBranch />
              CO-PO Mapping
            </Button>
            <StatusBadge status={data.status} />
          </div>
        }
      />

      {/* Workflow stepper */}
      <Card>
        <CardHeader>
          <CardTitle>Workflow Status</CardTitle>
        </CardHeader>
        <CardContent>
          <COStatusStepper status={data.status} />
          <div className="mt-4 flex flex-wrap gap-2">
            <PermissionGate permission="co.submit">
              {isDraft && (
                <Button
                  size="sm"
                  onClick={() => submitMutation.mutate()}
                  disabled={submitMutation.isPending}
                >
                  {submitMutation.isPending && <Loader2 className="animate-spin" />}
                  Submit for Review
                </Button>
              )}
            </PermissionGate>
            <PermissionGate permission="co.approve">
              {isUnderReview && (
                <Button
                  size="sm"
                  onClick={() => approveMutation.mutate()}
                  disabled={approveMutation.isPending}
                >
                  {approveMutation.isPending && <Loader2 className="animate-spin" />}
                  Approve
                </Button>
              )}
            </PermissionGate>
            <PermissionGate permission="co.publish">
              {isApproved && (
                <Button
                  size="sm"
                  onClick={() => publishMutation.mutate()}
                  disabled={publishMutation.isPending}
                >
                  {publishMutation.isPending && <Loader2 className="animate-spin" />}
                  Publish
                </Button>
              )}
            </PermissionGate>
          </div>
        </CardContent>
      </Card>

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
              <dd>{data.bloom_level_name ?? <span className="text-muted-foreground">—</span>}</dd>
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

      {/* Edit form — only when DRAFT */}
      <PermissionGate permission="co.update">
        {isDraft && (
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
                  <Label>Bloom Level</Label>
                  <Controller
                    name="bloom_level_id"
                    control={control}
                    render={({ field }) => (
                      <Select value={field.value ?? ""} onValueChange={field.onChange}>
                        <SelectTrigger className="w-full">
                          <SelectValue placeholder="Select bloom level">
                            {(v: string | null) => {
                              const bl = bloomLevelById[v ?? ""]
                              return bl ? `${bl.code} — ${bl.name}` : null
                            }}
                          </SelectValue>
                        </SelectTrigger>
                        <SelectContent>
                          {bloomDomains.map((domain) => {
                            const levels = bloomLevels
                              .filter((l) => l.bloom_domain_id === domain.id)
                              .sort((a, b) => a.order_index - b.order_index)
                            if (levels.length === 0) return null
                            return (
                              <SelectGroup key={domain.id}>
                                <SelectLabel>{domain.name}</SelectLabel>
                                {levels.map((l) => (
                                  <SelectItem key={l.id} value={l.id}>
                                    {l.code} — {l.name}
                                  </SelectItem>
                                ))}
                              </SelectGroup>
                            )
                          })}
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
        )}
      </PermissionGate>
    </div>
  )
}
