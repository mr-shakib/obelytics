"use client"

import { useState, useEffect, useCallback, useRef } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { Grid3x3, AlertTriangle, CheckCircle2, ArrowRight, ChevronDown, Loader2, Sparkles } from "lucide-react"
import { PermissionGate } from "@/components/shared/permission-gate"
import { CoPoSuggestionsPanel } from "@/components/courses/co-po-suggestions-panel"
import { usePermission } from "@/hooks/use-permission"
import { Card, CardHeader, CardTitle, CardDescription, CardAction, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Textarea } from "@/components/ui/textarea"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { cn } from "@/lib/utils"
import { apiClient } from "@/lib/api/client"
import { authoringApi, type MappingSuggestResponse, type SuggestedLink } from "@/lib/api/authoring"
import { queryKeys } from "@/lib/query-keys"

// ── Types ──────────────────────────────────────────────────────────────────────

type CourseOutcome  = { id: string; code: string; statement: string }
type ProgramOutcome = { id: string; code: string; statement: string }

type MappingSet = { id: string }
type MappingEntry = {
  id: string
  mapping_set_id: string
  course_outcome_id: string
  program_outcome_id: string
  weight: 1 | 2 | 3
  justification: string
}

type KnowledgeGap = { program_outcome_id: string; program_outcome_code: string; required_kp_codes: string[] }
type ValidationIssue = {
  course_outcome_id: string
  course_outcome_code: string
  missing_cep: boolean
  missing_cea: boolean
  /** POs this CO is mapped to without any of the knowledge profiles they require. */
  missing_kp?: KnowledgeGap[]
}
type ValidationResponse = { is_valid: boolean; issues: ValidationIssue[] }

// ── Helpers ───────────────────────────────────────────────────────────────────

const DEFAULT_WEIGHT = 2

function matrixKey(coId: string, poId: string) {
  return `${coId}:${poId}`
}

const EMPTY_ENTRIES: MappingEntry[] = []

type PendingMapping = { coId: string; poId: string; coCode: string; poCode: string }
type Weight = 1 | 2 | 3

// ── Component ─────────────────────────────────────────────────────────────────

export function CoPoMappingCard({
  curriculumId,
  courseId,
  cos,
  pos,
}: {
  curriculumId: string
  courseId: string
  cos: CourseOutcome[]
  pos: ProgramOutcome[]
}) {
  const qc = useQueryClient()

  const [setId,  setSetId]  = useState<string | null>(null)
  const [matrix, setMatrix] = useState<Set<string>>(new Set())
  const [pendingMapping, setPendingMapping] = useState<PendingMapping | null>(null)
  const [justificationText, setJustificationText] = useState("")
  const [saving, setSaving] = useState(false)
  const pendingRef = useRef<Set<string>>(new Set())
  const matrixRef = useRef<Set<string>>(new Set())
  const justificationsRef = useRef<Map<string, string>>(new Map())
  const weightsRef = useRef<Map<string, Weight>>(new Map())
  const [weights, setWeights] = useState<Map<string, Weight>>(new Map())
  const canUpdate = usePermission("mapping.co_po.update")

  // AI suggestions (advisory until applied)
  const [suggestion, setSuggestion] = useState<MappingSuggestResponse | null>(null)
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [weightOverrides, setWeightOverrides] = useState<Map<number, Weight>>(new Map())
  const [appliedAny, setAppliedAny] = useState(false)

  // ── Existing mapping set ─────────────────────────────────────────────────

  const { data: existingSet } = useQuery({
    queryKey: queryKeys.coPoMappings.byCourse(curriculumId, courseId),
    queryFn: async () => {
      try {
        const { data } = await apiClient.GET(
          `/mappings/co-po?curriculum_id=${curriculumId}&course_id=${courseId}` as never
        ) as { data: unknown }
        return ((data as unknown) as MappingSet) ?? null
      } catch {
        return null
      }
    },
    enabled: !!curriculumId && !!courseId,
    retry: false,
  })

  const { data: existingEntries = EMPTY_ENTRIES } = useQuery({
    queryKey: queryKeys.coPoMappings.entries(setId ?? ""),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/mappings/co-po/${setId}/entries` as never)
      return ((data as unknown) as MappingEntry[]) ?? []
    },
    enabled: !!setId,
  })

  const { data: validation } = useQuery({
    queryKey: queryKeys.coPoMappings.validation(setId ?? ""),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/mappings/co-po/${setId}/validate` as never)
      return ((data as unknown) as ValidationResponse) ?? null
    },
    enabled: !!setId,
  })

  // ── Sync state from loaded data ──────────────────────────────────────────

  useEffect(() => {
    if (existingSet !== undefined) {
      queueMicrotask(() => setSetId(existingSet?.id ?? null))
    }
  }, [existingSet])

  useEffect(() => {
    const m = new Set<string>()
    const j = new Map<string, string>()
    const w = new Map<string, Weight>()
    for (const e of existingEntries) {
      const key = matrixKey(e.course_outcome_id, e.program_outcome_id)
      m.add(key)
      j.set(key, e.justification)
      w.set(key, e.weight)
    }
    queueMicrotask(() => {
      setMatrix(m)
      setWeights(w)
      matrixRef.current = m
      justificationsRef.current = j
      weightsRef.current = w
    })
  }, [existingEntries])

  // ── Derived ──────────────────────────────────────────────────────────────

  const hasMatrix = cos.length > 0 && pos.length > 0

  // ── Handlers ─────────────────────────────────────────────────────────────

  const flushMatrix = useCallback(async (resolvedSetId: string, matrixSnapshot: Set<string>) => {
    const entries = Array.from(matrixSnapshot).map((key) => {
      const [course_outcome_id, program_outcome_id] = key.split(":")
      return {
        course_outcome_id,
        program_outcome_id,
        weight: weightsRef.current.get(key) ?? DEFAULT_WEIGHT,
        justification: justificationsRef.current.get(key) ?? "",
      }
    })

    await apiClient.PUT(`/mappings/co-po/${resolvedSetId}/entries` as never, {
      body: entries,
    } as never)

    qc.invalidateQueries({ queryKey: queryKeys.coPoMappings.entries(resolvedSetId) })
    qc.invalidateQueries({ queryKey: queryKeys.coPoMappings.validation(resolvedSetId) })
  }, [qc])

  const saveMutation = useMutation({
    mutationFn: async ({ nextMatrix }: { nextMatrix: Set<string> }) => {
      let resolvedSetId = setId
      if (!resolvedSetId) {
        const { data: setData } = await apiClient.POST("/mappings/co-po" as never, {
          body: { curriculum_id: curriculumId, course_id: courseId },
        } as never) as { data: unknown }
        resolvedSetId = (setData as MappingSet).id
        setSetId(resolvedSetId)
        qc.invalidateQueries({ queryKey: queryKeys.coPoMappings.byCourse(curriculumId, courseId) })
      }
      await flushMatrix(resolvedSetId, nextMatrix)
      return resolvedSetId
    },
    onSuccess: () => {
      setSaving(false)
    },
    onError: () => {
      toast.error("Failed to save mapping")
      setSaving(false)
    },
  })

  function applyMapping(coId: string, poId: string, justification: string | null = null) {
    const key = matrixKey(coId, poId)
    const isAdding = !matrixRef.current.has(key)
    if (isAdding && !justification?.trim()) return

    setMatrix((prev) => {
      const next = new Set(prev)
      const nextJustifications = new Map(justificationsRef.current)
      const nextWeights = new Map(weightsRef.current)
      if (next.has(key)) {
        next.delete(key)
        nextJustifications.delete(key)
        nextWeights.delete(key)
      } else {
        next.add(key)
        nextJustifications.set(key, justification!.trim())
        nextWeights.set(key, DEFAULT_WEIGHT)
      }

      matrixRef.current = next
      justificationsRef.current = nextJustifications
      weightsRef.current = nextWeights
      queueMicrotask(() => setWeights(nextWeights))

      // Optimistically update the react-query cache so the summary card reflects instantly
      if (setId) {
        const entries: MappingEntry[] = Array.from(next).map((k) => {
          const [course_outcome_id, program_outcome_id] = k.split(":")
          return {
            id: `optimistic-${k}`,
            mapping_set_id: setId,
            course_outcome_id,
            program_outcome_id,
            weight: nextWeights.get(k) ?? DEFAULT_WEIGHT,
            justification: nextJustifications.get(k) ?? "",
          }
        })
        qc.setQueryData(queryKeys.coPoMappings.entries(setId), entries)
      }

      if (!pendingRef.current.has("co-po")) {
        pendingRef.current.add("co-po")
        setSaving(true)
        setTimeout(() => {
          pendingRef.current.delete("co-po")
          saveMutation.mutate({ nextMatrix: matrixRef.current })
        }, 300)
      }

      return next
    })
  }

  function handleCellClick(co: CourseOutcome, po: ProgramOutcome) {
    const key = matrixKey(co.id, po.id)
    if (matrixRef.current.has(key)) {
      applyMapping(co.id, po.id)
      return
    }
    setPendingMapping({ coId: co.id, poId: po.id, coCode: co.code, poCode: po.code })
    setJustificationText("")
  }

  function savePendingMapping() {
    if (!pendingMapping || !justificationText.trim()) return
    applyMapping(pendingMapping.coId, pendingMapping.poId, justificationText.trim())
    setPendingMapping(null)
    setJustificationText("")
  }

  // ── AI suggestions ───────────────────────────────────────────────────────

  const suggestMutation = useMutation({
    /** coIds: map only these COs (e.g. one just added); undefined maps every CO. */
    mutationFn: (coIds?: string[]) =>
      authoringApi.suggestMapping({
        curriculum_id: curriculumId,
        course_id: courseId,
        course_outcome_ids: coIds,
      }),
    onSuccess: (data) => {
      if (suggestion && !appliedAny) authoringApi.decide(suggestion.suggestion_id, "REJECTED")
      setSuggestion(data)
      setSelected(new Set())
      setWeightOverrides(new Map())
      setAppliedAny(false)
    },
  })

  const applySuggestionsMutation = useMutation({
    mutationFn: async () => {
      if (!suggestion) throw new Error("no_suggestion")
      const items = Array.from(selected).map((index) => {
        const override = weightOverrides.get(index)
        return override ? { index, weight: override } : { index }
      })
      return authoringApi.applyMapping(suggestion.suggestion_id, items)
    },
    onSuccess: (result) => {
      const added = [
        result.added_knowledge_profiles && `${result.added_knowledge_profiles} knowledge profile`,
        result.added_complex_problems && `${result.added_complex_problems} CEP`,
        result.added_complex_activities && `${result.added_complex_activities} CEA`,
      ].filter(Boolean)
      toast.success(
        `Applied ${result.applied.length} link${result.applied.length === 1 ? "" : "s"}` +
          (added.length ? ` and added ${added.join(", ")} mapping${added.length > 1 ? "s" : ""}` : "")
      )
      const done = new Set([...result.applied, ...result.already_mapped])
      setSuggestion((prev) =>
        prev && {
          ...prev,
          links: prev.links.map((l) =>
            done.has(l.index) ? { ...l, already_mapped: true, can_apply: false } : l
          ),
        }
      )
      setSelected(new Set())
      setAppliedAny(true)
      setSetId(result.mapping_set_id)
      qc.invalidateQueries({ queryKey: queryKeys.coPoMappings.all })
      qc.invalidateQueries({ queryKey: ["complex-mappings"] })
    },
  })

  function dismissSuggestions() {
    // Applying records its own decision; only a suggestion left unused is a rejection.
    if (suggestion && !appliedAny) authoringApi.decide(suggestion.suggestion_id, "REJECTED")
    setSuggestion(null)
    setSelected(new Set())
  }

  function toggleSuggestion(index: number) {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(index)) next.delete(index)
      else next.add(index)
      return next
    })
  }

  // COs with no PO yet — usually ones just added — can be mapped on their own.
  const unmappedCos = cos.filter((co) => !pos.some((po) => matrix.has(matrixKey(co.id, po.id))))
  const pendingCoIds = suggestMutation.isPending ? suggestMutation.variables : undefined

  const suggestedByCell = new Map<string, SuggestedLink>()
  for (const link of suggestion?.links ?? []) {
    suggestedByCell.set(matrixKey(link.course_outcome_id, link.program_outcome_id), link)
  }

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <>
    <Card id="co-po-mapping">
      <CardHeader>
        <CardTitle>CO-PO Mapping</CardTitle>
        <CardDescription>
          Map course outcomes to program outcomes. Click a cell to toggle the mapping on or off. Changes save automatically.
        </CardDescription>
        <CardAction>
          <div className="flex items-center gap-3">
            {saving && (
              <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <Loader2 className="h-3 w-3 animate-spin" />
                Saving...
              </div>
            )}
            {hasMatrix && canUpdate && (
              <DropdownMenu>
                <DropdownMenuTrigger
                  disabled={suggestMutation.isPending}
                  render={<Button type="button" variant="outline" size="sm" />}
                >
                  {suggestMutation.isPending ? <Loader2 className="animate-spin" /> : <Sparkles />}
                  {suggestMutation.isPending ? "Suggesting…" : "Suggest with AI"}
                  <ChevronDown className="h-3 w-3" />
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-64">
                  <DropdownMenuItem
                    disabled={unmappedCos.length === 0}
                    onClick={() => suggestMutation.mutate(unmappedCos.map((co) => co.id))}
                  >
                    {unmappedCos.length > 0
                      ? `COs not mapped yet (${unmappedCos.map((co) => co.code).join(", ")})`
                      : "COs not mapped yet (none)"}
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => suggestMutation.mutate(undefined)}>
                    All COs ({cos.length}) — review the whole matrix
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            )}
          </div>
        </CardAction>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Legend */}
        {hasMatrix && (
          <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
            <span className="flex items-center gap-1">
              <span className="w-5 h-5 inline-flex items-center justify-center rounded bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300 font-semibold">
                3
              </span>
              Mapped (weight 1–3)
            </span>
            {suggestion && (
              <>
                <span className="flex items-center gap-1">
                  <span className="w-5 h-5 inline-flex items-center justify-center rounded border border-dashed border-violet-400 text-violet-700 dark:text-violet-300 font-semibold">
                    2
                  </span>
                  AI suggests
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-5 h-5 inline-flex items-center justify-center rounded border border-dashed border-destructive/50 text-destructive font-semibold">
                    !
                  </span>
                  Suggested, breaks a rule
                </span>
              </>
            )}
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

        {cos.length > 0 && pos.length === 0 && (
          <div className="border border-dashed border-border rounded-lg p-12 text-center text-sm text-muted-foreground">
            No program outcomes found for this curriculum&apos;s program.
          </div>
        )}

        {/* Matrix */}
        {hasMatrix && (
          <div className="overflow-x-auto rounded-md border">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="bg-muted/50">
                  <th className="px-3 py-2 text-left font-medium border-b border-r min-w-[200px] sticky left-0 bg-muted/50 z-10">
                    CO / PO
                  </th>
                  {pos.map((po) => (
                    <th
                      key={po.id}
                      className="px-2 py-2 text-center font-medium border-b border-r min-w-[54px] max-w-[54px]"
                      title={po.statement}
                    >
                      {po.code}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {cos.map((co, i) => (
                  <tr key={co.id} className={cn("hover:bg-muted/30", i % 2 !== 0 && "bg-muted/10")}>
                    <td
                      className="px-3 py-1 border-b border-r text-xs sticky left-0 bg-background z-10"
                      title={co.statement}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-mono font-semibold">{co.code}</span>
                        <span className="flex items-center gap-1">
                          {unmappedCos.includes(co) && (
                            <span className="rounded-full bg-muted px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
                              not mapped
                            </span>
                          )}
                          {canUpdate && (
                            <Button
                              type="button"
                              variant="ghost"
                              size="icon-xs"
                              aria-label={`Suggest POs for ${co.code} with AI`}
                              title={`Suggest POs for ${co.code} with AI`}
                              disabled={suggestMutation.isPending}
                              onClick={() => suggestMutation.mutate([co.id])}
                            >
                              {pendingCoIds?.length === 1 && pendingCoIds[0] === co.id ? (
                                <Loader2 className="animate-spin" />
                              ) : (
                                <Sparkles />
                              )}
                            </Button>
                          )}
                        </span>
                      </div>
                    </td>
                    {pos.map((po) => {
                      const key = matrixKey(co.id, po.id)
                      const mapped = matrix.has(key)
                      const weight = weights.get(key) ?? DEFAULT_WEIGHT
                      const suggested = mapped ? undefined : suggestedByCell.get(key)
                      const mappedBadge = (
                        <span className="w-7 h-7 inline-flex items-center justify-center rounded bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300 font-semibold">
                          {weight}
                        </span>
                      )
                      return (
                        <td key={po.id} className="border-b border-r text-center p-0">
                          <PermissionGate
                            permission="mapping.co_po.update"
                            fallback={
                              <div className="h-9 flex items-center justify-center">
                                {mapped && mappedBadge}
                              </div>
                            }
                          >
                            <button
                              type="button"
                              className="w-full h-9 flex items-center justify-center hover:bg-accent/50 transition-colors"
                              onClick={() =>
                                suggested?.can_apply ? toggleSuggestion(suggested.index) : handleCellClick(co, po)
                              }
                              title={
                                suggested
                                  ? suggested.can_apply
                                    ? `AI suggests ${co.code} → ${po.code}, weight ${weightOverrides.get(suggested.index) ?? suggested.weight}. Click to ${selected.has(suggested.index) ? "unselect" : "select"} it.\n${suggested.justification}`
                                    : `AI suggests ${co.code} → ${po.code}, but: ${suggested.issues.join(" ")}`
                                  : `${co.code} × ${po.code}${mapped ? ` — Mapped, weight ${weight}` : ""}`
                              }
                            >
                              {mapped ? (
                                mappedBadge
                              ) : suggested ? (
                                <span
                                  className={cn(
                                    "w-7 h-7 inline-flex items-center justify-center rounded border border-dashed text-xs font-semibold",
                                    suggested.can_apply
                                      ? selected.has(suggested.index)
                                        ? "border-solid border-violet-500 bg-violet-100 text-violet-800 dark:bg-violet-900/40 dark:text-violet-200"
                                        : "border-violet-400 text-violet-700 dark:text-violet-300"
                                      : "border-destructive/50 text-destructive"
                                  )}
                                >
                                  {suggested.can_apply ? (weightOverrides.get(suggested.index) ?? suggested.weight) : "!"}
                                </span>
                              ) : (
                                <span className="w-7 h-7 inline-flex items-center justify-center rounded border border-dashed border-muted-foreground/20 text-muted-foreground/30 text-xs">
                                  —
                                </span>
                              )}
                            </button>
                          </PermissionGate>
                        </td>
                      )
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {suggestion && (
          <CoPoSuggestionsPanel
            suggestion={suggestion}
            selected={selected}
            weights={weightOverrides}
            canManage={canUpdate}
            applying={applySuggestionsMutation.isPending}
            onToggle={toggleSuggestion}
            onSelectAll={(select) =>
              setSelected(select ? new Set(suggestion.links.filter((l) => l.can_apply).map((l) => l.index)) : new Set())
            }
            onWeightChange={(index, weight) =>
              setWeightOverrides((prev) => new Map(prev).set(index, weight))
            }
            onApply={() => applySuggestionsMutation.mutate()}
            onDismiss={dismissSuggestions}
          />
        )}

        {/* Mapping rules checklist (K / CEP / CEA) */}
        {hasMatrix && validation && (
          <div className={cn(
            "rounded-xl border p-4",
            validation.is_valid
              ? "border-green-200 bg-green-50 dark:border-green-900/40 dark:bg-green-900/10"
              : "border-amber-200 bg-amber-50 dark:border-amber-900/40 dark:bg-amber-900/10"
          )}>
            {validation.is_valid ? (
              <div className="flex items-center gap-2 text-sm text-green-800 dark:text-green-300">
                <CheckCircle2 className="h-4 w-4" />
                Every link meets the mapping rules: each CO shares a required knowledge profile with its POs, COs
                mapped to PO1–PO7 have a CEP, and COs mapped to PO10 have a CEA.
              </div>
            ) : (
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-sm font-medium text-amber-800 dark:text-amber-300">
                  <AlertTriangle className="h-4 w-4" />
                  Some links break the mapping rules
                </div>
                <ul className="space-y-1.5 text-sm">
                  {validation.issues.map((issue) => (
                    <li key={issue.course_outcome_id} className="flex flex-wrap items-center gap-2">
                      <span className="font-mono font-semibold">{issue.course_outcome_code}</span>
                      {(issue.missing_kp ?? []).map((gap) => (
                        <a
                          key={gap.program_outcome_id}
                          href="#co-kp-mapping"
                          title={`${issue.course_outcome_code} is mapped to ${gap.program_outcome_code} but to none of the knowledge profiles it requires.`}
                          className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800 hover:bg-amber-200 dark:bg-amber-900/30 dark:text-amber-300"
                        >
                          {gap.program_outcome_code} needs {gap.required_kp_codes.join(" or ")} <ArrowRight className="h-3 w-3" />
                        </a>
                      ))}
                      {issue.missing_cep && (
                        <a
                          href="#co-cp-mapping"
                          className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800 hover:bg-amber-200 dark:bg-amber-900/30 dark:text-amber-300"
                        >
                          Missing CEP <ArrowRight className="h-3 w-3" />
                        </a>
                      )}
                      {issue.missing_cea && (
                        <a
                          href="#co-ca-mapping"
                          className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800 hover:bg-amber-200 dark:bg-amber-900/30 dark:text-amber-300"
                        >
                          Missing CEA <ArrowRight className="h-3 w-3" />
                        </a>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
    <Dialog open={!!pendingMapping} onOpenChange={(open) => !open && setPendingMapping(null)}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Justification of Mapping</DialogTitle>
          <DialogDescription>
            {pendingMapping
              ? `Explain why ${pendingMapping.coCode} maps to ${pendingMapping.poCode}.`
              : "Explain this mapping."}
          </DialogDescription>
        </DialogHeader>
        <Textarea
          autoFocus
          rows={4}
          value={justificationText}
          onChange={(event) => setJustificationText(event.target.value)}
          placeholder="Enter justification..."
        />
        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={() => {
              setPendingMapping(null)
              setJustificationText("")
            }}
          >
            Cancel
          </Button>
          <Button type="button" disabled={!justificationText.trim()} onClick={savePendingMapping}>
            Save mapping
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
    </>
  )
}
