"use client"

import { useQuery, useQueries, useMutation, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { Grid3x3, Check, Loader2 } from "lucide-react"
import { usePermission } from "@/hooks/use-permission"
import { Card, CardHeader, CardTitle, CardDescription, CardAction, CardContent } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"

// ── Types ──────────────────────────────────────────────────────────────────────

type CourseOutcome = { id: string; code: string; statement: string }

type ComplexOption = { id: string; code: string; name: string | null; description: string; is_active: boolean }

type ComplexMapping = {
  id: string
  course_outcome_id: string
  status: string
  complex_problem_id?: string
  complex_activity_id?: string
  knowledge_profile_id?: string
}

const EMPTY_OPTIONS: ComplexOption[] = []
const EMPTY_MAPPINGS: ComplexMapping[] = []

// ── Per-kind configuration ───────────────────────────────────────────────────

export type ComplexMappingKind = "cp" | "ca" | "kp"

const KIND_CONFIG: Record<
  ComplexMappingKind,
  {
    title: string
    description: string
    optionsPath: "/ref-data/complex-problems" | "/ref-data/complex-activities" | "/ref-data/knowledge-profiles"
    optionsQueryKey: readonly unknown[]
    mappingsPath: "/mappings/co-cp" | "/mappings/co-ca" | "/mappings/co-kp"
    optionField: "complex_problem_id" | "complex_activity_id" | "knowledge_profile_id"
    managePermission: string
    columnLabel: string
    cardId: string
  }
> = {
  cp: {
    title: "CO-CP Mapping",
    description:
      "Map course outcomes to Complex Engineering Problems (CEP). Required for any CO mapped to PO1–PO7. Click a cell to toggle the mapping on or off.",
    optionsPath: "/ref-data/complex-problems",
    optionsQueryKey: queryKeys.refData.complexProblems,
    mappingsPath: "/mappings/co-cp",
    optionField: "complex_problem_id",
    managePermission: "mapping.co_cp.manage",
    columnLabel: "CEP",
    cardId: "co-cp-mapping",
  },
  ca: {
    title: "CO-CA Mapping",
    description:
      "Map course outcomes to Complex Engineering Activities (CEA). Required for any CO mapped to PO10. Click a cell to toggle the mapping on or off.",
    optionsPath: "/ref-data/complex-activities",
    optionsQueryKey: queryKeys.refData.complexActivities,
    mappingsPath: "/mappings/co-ca",
    optionField: "complex_activity_id",
    managePermission: "mapping.co_ca.manage",
    columnLabel: "CEA",
    cardId: "co-ca-mapping",
  },
  kp: {
    title: "CO-KP Mapping",
    description:
      "Map course outcomes to Knowledge Profiles (KP). Click a cell to toggle the mapping on or off.",
    optionsPath: "/ref-data/knowledge-profiles",
    optionsQueryKey: queryKeys.refData.knowledgeProfiles,
    mappingsPath: "/mappings/co-kp",
    optionField: "knowledge_profile_id",
    managePermission: "mapping.co_kp.manage",
    columnLabel: "KP",
    cardId: "co-kp-mapping",
  },
}

function getOptionId(mapping: ComplexMapping, kind: ComplexMappingKind): string | undefined {
  if (kind === "cp") return mapping.complex_problem_id
  if (kind === "ca") return mapping.complex_activity_id
  return mapping.knowledge_profile_id
}

// ── Component ─────────────────────────────────────────────────────────────────

export function ComplexMappingCard({
  kind,
  cos,
}: {
  kind: ComplexMappingKind
  cos: CourseOutcome[]
}) {
  const config = KIND_CONFIG[kind]
  const qc = useQueryClient()

  const canManage = usePermission(config.managePermission)

  // ── Data fetching ────────────────────────────────────────────────────────

  const { data: options = EMPTY_OPTIONS } = useQuery({
    queryKey: config.optionsQueryKey,
    queryFn: async () => {
      const { data } = await apiClient.GET(config.optionsPath as never)
      return ((data as unknown) as ComplexOption[]) ?? []
    },
  })

  const activeOptions = options.filter((o) => o.is_active)

  const mappingQueries = useQueries({
    queries: cos.map((co) => ({
      queryKey: queryKeys.complexMappings.byCo(kind, co.id),
      queryFn: async () => {
        const { data } = await apiClient.GET(
          `${config.mappingsPath}?course_outcome_id=${co.id}` as never
        )
        return ((data as unknown) as ComplexMapping[]) ?? []
      },
    })),
  })

  const mappingsByCo = new Map<string, ComplexMapping[]>()
  cos.forEach((co, i) => {
    mappingsByCo.set(co.id, mappingQueries[i]?.data ?? EMPTY_MAPPINGS)
  })

  // ── Derived ──────────────────────────────────────────────────────────────

  const hasMatrix = cos.length > 0 && activeOptions.length > 0

  // ── Mutations ────────────────────────────────────────────────────────────

  const invalidateCo = (coId: string) =>
    qc.invalidateQueries({ queryKey: queryKeys.complexMappings.byCo(kind, coId) })

  const createMutation = useMutation({
    mutationFn: async ({ coId, optionId }: { coId: string; optionId: string }) => {
      const { data } = await apiClient.POST(config.mappingsPath as never, {
        body: { course_outcome_id: coId, [config.optionField]: optionId },
      } as never) as { data: unknown }
      return data as ComplexMapping
    },
    onMutate: async ({ coId, optionId }) => {
      const queryKey = queryKeys.complexMappings.byCo(kind, coId)
      await qc.cancelQueries({ queryKey })
      const prev = qc.getQueryData<ComplexMapping[]>(queryKey) ?? []
      const optimisticId = `optimistic-${coId}-${optionId}`
      const optimisticMapping: ComplexMapping = {
        id: optimisticId,
        course_outcome_id: coId,
        status: "active",
        [config.optionField]: optionId,
      } as ComplexMapping
      qc.setQueryData<ComplexMapping[]>(queryKey, [...prev, optimisticMapping])
      return { prev, queryKey }
    },
    onError: (_err, _vars, context) => {
      if (context) {
        qc.setQueryData(context.queryKey, context.prev)
        toast.error("Failed to add mapping")
      }
    },
    onSettled: (_data, _err, vars) => {
      invalidateCo(vars.coId)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: async (vars: { mappingId: string; coId: string }) => {
      await apiClient.DELETE(`${config.mappingsPath}/${vars.mappingId}` as never)
    },
    onMutate: async ({ mappingId, coId }) => {
      const queryKey = queryKeys.complexMappings.byCo(kind, coId)
      await qc.cancelQueries({ queryKey })
      const prev = qc.getQueryData<ComplexMapping[]>(queryKey) ?? []
      qc.setQueryData<ComplexMapping[]>(
        queryKey,
        prev.filter((m) => m.id !== mappingId)
      )
      return { prev, queryKey }
    },
    onError: (_err, _vars, context) => {
      if (context) {
        qc.setQueryData(context.queryKey, context.prev)
        toast.error("Failed to remove mapping")
      }
    },
    onSettled: (_data, _err, vars) => {
      invalidateCo(vars.coId)
    },
  })

  const isMutating = createMutation.isPending || deleteMutation.isPending

  function handleCellClick(co: CourseOutcome, option: ComplexOption) {
    if (!canManage) return
    const mappings = mappingsByCo.get(co.id) ?? []
    const existing = mappings.find((m) => getOptionId(m, kind) === option.id)

    if (!existing) {
      createMutation.mutate({ coId: co.id, optionId: option.id })
    } else {
      deleteMutation.mutate({ mappingId: existing.id, coId: co.id })
    }
  }

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <Card id={config.cardId}>
      <CardHeader>
        <CardTitle>{config.title}</CardTitle>
        <CardDescription>{config.description}</CardDescription>
        {isMutating && (
          <CardAction>
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <Loader2 className="h-3 w-3 animate-spin" />
              Saving...
            </div>
          </CardAction>
        )}
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Legend */}
        {hasMatrix && (
          <div className="flex items-center gap-3 text-xs text-muted-foreground">
            <span className="flex items-center gap-1">
              <span className="w-5 h-5 inline-flex items-center justify-center rounded bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300">
                <Check className="h-3 w-3" />
              </span>
              Mapped{canManage ? " (click to remove)" : ""}
            </span>
            <span className="flex items-center gap-1">
              <span className="w-5 h-5 inline-flex items-center justify-center rounded border border-dashed border-muted-foreground/30 text-muted-foreground/40 text-xs">—</span>
              Not mapped
            </span>
          </div>
        )}

        {/* Empty states */}
        {cos.length === 0 && (
          <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed border-border p-12 text-center">
            <Grid3x3 className="h-8 w-8 text-muted-foreground/50" />
            <p className="text-sm text-muted-foreground">
              No course outcomes for this course yet. Add COs via &quot;Manage Course Outcomes&quot; above.
            </p>
          </div>
        )}

        {cos.length > 0 && activeOptions.length === 0 && (
          <div className="border border-dashed border-border rounded-lg p-12 text-center text-sm text-muted-foreground">
            No {config.columnLabel} options configured. Add some on the Complex Attributes page.
          </div>
        )}

        {/* Matrix */}
        {hasMatrix && (
          <div className="overflow-x-auto rounded-md border">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="bg-muted/50">
                  <th className="px-3 py-2 text-left font-medium border-b border-r min-w-[200px] sticky left-0 bg-muted/50 z-10">
                    CO / {config.columnLabel}
                  </th>
                  {activeOptions.map((option) => (
                    <th
                      key={option.id}
                      className="px-2 py-2 text-center font-medium border-b border-r min-w-[64px] max-w-[64px]"
                      title={option.description}
                    >
                      {option.code}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {cos.map((co, i) => (
                  <tr key={co.id} className={cn("hover:bg-muted/30", i % 2 !== 0 && "bg-muted/10")}>
                    <td
                      className="px-3 py-2 border-b border-r font-mono font-semibold text-xs sticky left-0 bg-background z-10"
                      title={co.statement}
                    >
                      {co.code}
                    </td>
                    {activeOptions.map((option) => {
                      const mappings = mappingsByCo.get(co.id) ?? []
                      const existing = mappings.find((m) => getOptionId(m, kind) === option.id)
                      const mapped = !!existing
                      const cellTitle = `${co.code} × ${option.code}${mapped ? " — Mapped" : ""}`

                      const badge = mapped ? (
                        <span className="w-7 h-7 inline-flex items-center justify-center rounded bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300">
                          <Check className="h-4 w-4" />
                        </span>
                      ) : (
                        <span className="w-7 h-7 inline-flex items-center justify-center rounded border border-dashed border-muted-foreground/20 text-muted-foreground/30 text-xs">
                          —
                        </span>
                      )

                      return (
                        <td key={option.id} className="border-b border-r text-center p-0">
                          {canManage ? (
                            <button
                              type="button"
                              className="w-full h-9 flex items-center justify-center hover:bg-accent/50 transition-colors"
                              onClick={() => handleCellClick(co, option)}
                              title={cellTitle}
                            >
                              {badge}
                            </button>
                          ) : (
                            <div className="h-9 flex items-center justify-center" title={cellTitle}>
                              {badge}
                            </div>
                          )}
                        </td>
                      )
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
