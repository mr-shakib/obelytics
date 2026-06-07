"use client"

import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { Loader2, Save } from "lucide-react"
import { PageHeader } from "@/components/shared/page-header"
import { PermissionGate } from "@/components/shared/permission-gate"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { cn } from "@/lib/utils"
import { apiClient } from "@/lib/api/client"
import { queryKeys } from "@/lib/query-keys"

type Curriculum = { id: string; name: string; program_name: string }
type ProgramOutcome = { id: string; code: string; statement: string }
type CourseOutcome = { id: string; code: string; statement: string; course_name?: string }

type Strength = 1 | 2 | 3

type MappingEntry = {
  co_id: string
  po_id: string
  strength: Strength | null
}

const STRENGTH_LABELS: Record<Strength, string> = { 1: "L", 2: "M", 3: "H" }
const STRENGTH_COLORS: Record<Strength, string> = {
  1: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300",
  2: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300",
  3: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300",
}

function nextStrength(s: Strength | null): Strength | null {
  if (s === null) return 1
  if (s === 1) return 2
  if (s === 2) return 3
  return null
}

export function CoPoMappingClient() {
  const qc = useQueryClient()
  const [curriculumId, setCurriculumId] = useState<string>("")
  const [matrix, setMatrix] = useState<Map<string, Strength | null>>(new Map())
  const [dirty, setDirty] = useState(false)

  const { data: curricula } = useQuery({
    queryKey: queryKeys.curricula.list(),
    queryFn: async () => {
      const { data } = await apiClient.GET("/curricula" as never)
      return ((data as unknown) as { items?: Curriculum[] })?.items ?? ((data as unknown) as Curriculum[]) ?? []
    },
  })

  const { data: programOutcomes } = useQuery({
    queryKey: queryKeys.programOutcomes.list({ curriculum_id: curriculumId }),
    queryFn: async () => {
      const url = curriculumId
        ? `/program-outcomes?curriculum_id=${curriculumId}`
        : "/program-outcomes"
      const { data } = await apiClient.GET(url as never)
      return ((data as unknown) as { items?: ProgramOutcome[] })?.items ?? ((data as unknown) as ProgramOutcome[]) ?? []
    },
    enabled: !!curriculumId,
  })

  const { data: courseOutcomes } = useQuery({
    queryKey: queryKeys.courseOutcomes.list(curriculumId),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/course-outcomes?curriculum_id=${curriculumId}` as never)
      return ((data as unknown) as { items?: CourseOutcome[] })?.items ?? ((data as unknown) as CourseOutcome[]) ?? []
    },
    enabled: !!curriculumId,
  })

  const { data: existingMappings } = useQuery({
    queryKey: queryKeys.coPoMappings.list({ curriculum_id: curriculumId }),
    queryFn: async () => {
      const { data } = await apiClient.GET(`/co-po-mappings?curriculum_id=${curriculumId}` as never)
      return ((data as unknown) as { items?: MappingEntry[] })?.items ?? ((data as unknown) as MappingEntry[]) ?? []
    },
    enabled: !!curriculumId,
    onSuccess: (entries: MappingEntry[]) => {
      const m = new Map<string, Strength | null>()
      for (const e of entries) {
        m.set(`${e.co_id}:${e.po_id}`, e.strength)
      }
      setMatrix(m)
      setDirty(false)
    },
  } as Parameters<typeof useQuery>[0])

  const saveMutation = useMutation({
    mutationFn: async () => {
      const entries = Array.from(matrix.entries())
        .filter(([, s]) => s !== null)
        .map(([key, strength]) => {
          const [co_id, po_id] = key.split(":")
          return { co_id, po_id, strength }
        })
      await apiClient.PUT(`/co-po-mappings?curriculum_id=${curriculumId}` as never, {
        body: { entries },
      } as never)
    },
    onSuccess: () => {
      toast.success("CO-PO mapping saved")
      qc.invalidateQueries({ queryKey: queryKeys.coPoMappings.list({ curriculum_id: curriculumId }) })
      setDirty(false)
    },
    onError: () => toast.error("Failed to save mappings"),
  })

  function toggleCell(coId: string, poId: string) {
    const key = `${coId}:${poId}`
    const current = matrix.get(key) ?? null
    const next = nextStrength(current)
    setMatrix((prev) => {
      const next_ = new Map(prev)
      if (next === null) {
        next_.delete(key)
      } else {
        next_.set(key, next)
      }
      return next_
    })
    setDirty(true)
  }

  const pos = programOutcomes ?? []
  const cos = courseOutcomes ?? []

  return (
    <div className="space-y-4">
      <PageHeader
        title="CO-PO Mapping Matrix"
        description="Map course outcomes to program outcomes. Click cells to cycle: empty → Low → Medium → High → empty."
        actions={
          dirty && (
            <PermissionGate permission="co.po.map">
              <Button
                onClick={() => saveMutation.mutate()}
                disabled={saveMutation.isPending}
              >
                {saveMutation.isPending ? <Loader2 className="animate-spin" /> : <Save />}
                Save Matrix
              </Button>
            </PermissionGate>
          )
        }
      />

      <div className="flex gap-4 items-center mb-4">
        <div className="w-64">
          <Select
            value={curriculumId}
            onValueChange={(v) => setCurriculumId((v as string | null) ?? "")}
          >
            <SelectTrigger>
              <SelectValue placeholder="Select curriculum" />
            </SelectTrigger>
            <SelectContent>
              {(curricula ?? []).map((c) => (
                <SelectItem key={c.id} value={c.id}>
                  {c.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="flex items-center gap-3 text-xs text-muted-foreground">
          <span className="flex items-center gap-1">
            <span className="w-5 h-5 inline-flex items-center justify-center rounded text-xs bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300 font-bold">L</span>Low (1)
          </span>
          <span className="flex items-center gap-1">
            <span className="w-5 h-5 inline-flex items-center justify-center rounded text-xs bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300 font-bold">M</span>Medium (2)
          </span>
          <span className="flex items-center gap-1">
            <span className="w-5 h-5 inline-flex items-center justify-center rounded text-xs bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300 font-bold">H</span>High (3)
          </span>
        </div>
      </div>

      {!curriculumId && (
        <p className="text-sm text-muted-foreground">Select a curriculum to view the CO-PO matrix.</p>
      )}

      {curriculumId && cos.length === 0 && (
        <p className="text-sm text-muted-foreground">No course outcomes found for this curriculum.</p>
      )}

      {curriculumId && cos.length > 0 && pos.length > 0 && (
        <div className="overflow-x-auto rounded-md border">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="bg-muted/50">
                <th className="px-3 py-2 text-left font-medium border-b border-r min-w-[180px]">
                  CO / PO
                </th>
                {pos.map((po) => (
                  <th
                    key={po.id}
                    className="px-2 py-2 text-center font-medium border-b border-r min-w-[56px] max-w-[56px]"
                    title={po.statement}
                  >
                    {po.code}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {cos.map((co, i) => (
                <tr
                  key={co.id}
                  className={cn("hover:bg-muted/30", i % 2 === 0 ? "" : "bg-muted/10")}
                >
                  <td className="px-3 py-2 border-b border-r font-medium text-xs">
                    <div className="flex flex-col">
                      <span>{co.code}</span>
                      {co.course_name && (
                        <span className="text-muted-foreground font-normal">{co.course_name}</span>
                      )}
                    </div>
                  </td>
                  {pos.map((po) => {
                    const key = `${co.id}:${po.id}`
                    const strength = matrix.get(key) ?? null
                    return (
                      <td key={po.id} className="border-b border-r text-center p-0">
                        <PermissionGate
                          permission="co.po.map"
                          fallback={
                            <div className="h-9 flex items-center justify-center">
                              {strength !== null ? (
                                <span className={cn(
                                  "w-7 h-7 inline-flex items-center justify-center rounded text-xs font-bold",
                                  STRENGTH_COLORS[strength]
                                )}>
                                  {STRENGTH_LABELS[strength]}
                                </span>
                              ) : null}
                            </div>
                          }
                        >
                          <button
                            type="button"
                            className="w-full h-9 flex items-center justify-center hover:bg-accent/50 transition-colors"
                            onClick={() => toggleCell(co.id, po.id)}
                            title={`${co.code} × ${po.code}${strength ? ` — ${strength === 1 ? "Low" : strength === 2 ? "Medium" : "High"}` : ""}`}
                          >
                            {strength !== null ? (
                              <span className={cn(
                                "w-7 h-7 inline-flex items-center justify-center rounded text-xs font-bold",
                                STRENGTH_COLORS[strength]
                              )}>
                                {STRENGTH_LABELS[strength]}
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
    </div>
  )
}
