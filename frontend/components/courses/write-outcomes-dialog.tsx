"use client"

import { useState } from "react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Loader2, Sparkles, Trash2 } from "lucide-react"
import { toast } from "sonner"
import { PermissionGate } from "@/components/shared/permission-gate"
import { RefineStatement, WarningList } from "@/components/courses/refine-statement"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import { apiClient } from "@/lib/api/client"
import { authoringApi, type BloomRef, type DraftResponse } from "@/lib/api/authoring"
import { queryKeys } from "@/lib/query-keys"
import { cn } from "@/lib/utils"

type Draft = {
  key: number
  statement: string
  original: string
  bloomLevels: BloomRef[]
  rationale: string
  warnings: string[]
  selected: boolean
  edited: boolean
}

interface Props {
  curriculumId: string
  courseId: string
  existingCodes: string[]
}

const COUNTS = [1, 2, 3, 4, 5, 6, 7, 8]

function nextNumber(codes: string[]): number {
  const numbers = codes.map((c) => Number(/^CO(\d+)$/i.exec(c.trim())?.[1] ?? 0))
  return Math.max(0, ...numbers) + 1
}

/** Drafts COs with AI. The teacher edits, refines or drops each one before adding it. */
export function WriteOutcomesDialog({ curriculumId, courseId, existingCodes }: Props) {
  const qc = useQueryClient()
  const [open, setOpen] = useState(false)
  const [count, setCount] = useState(existingCodes.length > 0 ? 3 : 5)
  const [instruction, setInstruction] = useState("")
  const [suggestion, setSuggestion] = useState<DraftResponse | null>(null)
  const [drafts, setDrafts] = useState<Draft[]>([])

  const generate = useMutation({
    mutationFn: () =>
      authoringApi.draft({
        curriculum_id: curriculumId,
        course_id: courseId,
        count,
        instruction: instruction.trim() || undefined,
      }),
    onSuccess: (data) => {
      if (suggestion) authoringApi.decide(suggestion.suggestion_id, "REJECTED")
      setSuggestion(data)
      setDrafts(
        data.outcomes.map((o, i) => ({
          key: i,
          statement: o.statement,
          original: o.statement,
          bloomLevels: o.bloom_levels,
          rationale: o.rationale,
          warnings: o.warnings,
          selected: true,
          edited: false,
        }))
      )
    },
  })

  const chosen = drafts.filter((d) => d.selected && d.statement.trim().length >= 10)
  const firstNumber = nextNumber(existingCodes)

  const add = useMutation({
    mutationFn: async () => {
      let number = firstNumber
      for (const draft of chosen) {
        await apiClient.POST("/course-outcomes" as never, {
          body: {
            curriculum_id: curriculumId,
            course_id: courseId,
            code: `CO${number}`,
            statement: draft.statement.trim(),
            bloom_level_ids: draft.bloomLevels.map((b) => b.id),
          },
        } as never)
        number += 1
      }
    },
    onSuccess: () => {
      if (suggestion) {
        const accepted = chosen.map((d) => d.key)
        const edited = chosen.filter((d) => d.edited).map((d) => d.key)
        const decision = edited.length > 0 ? "EDITED" : accepted.length === drafts.length ? "ACCEPTED" : "PARTIAL"
        authoringApi.decide(suggestion.suggestion_id, decision, { accepted, edited })
      }
      toast.success(`${chosen.length} course outcome${chosen.length === 1 ? "" : "s"} added`)
      qc.invalidateQueries({ queryKey: queryKeys.courseOutcomes.list(curriculumId, courseId) })
      reset()
      setOpen(false)
    },
    onError: () => {
      toast.error("Some outcomes could not be added. Check the list and try again.")
      qc.invalidateQueries({ queryKey: queryKeys.courseOutcomes.list(curriculumId, courseId) })
    },
  })

  function reset() {
    setSuggestion(null)
    setDrafts([])
    setInstruction("")
  }

  function update(key: number, change: Partial<Draft>) {
    setDrafts((prev) => prev.map((d) => (d.key === key ? { ...d, ...change } : d)))
  }

  function handleOpenChange(next: boolean) {
    if (!next && suggestion && !add.isSuccess) {
      authoringApi.decide(suggestion.suggestion_id, "REJECTED")
      reset()
    }
    setOpen(next)
  }

  return (
    <>
      <PermissionGate permission="co.create">
        <Button variant="outline" onClick={() => setOpen(true)}>
          <Sparkles />
          Write COs with AI
        </Button>
      </PermissionGate>

      <Dialog open={open} onOpenChange={handleOpenChange}>
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-3xl">
          <DialogHeader>
            <DialogTitle>Write course outcomes with AI</DialogTitle>
            <DialogDescription>
              AI drafts outcomes from the course description, syllabus, objectives, weekly topics and
              program outcomes. Nothing is saved until you add them — read and edit each one first.
            </DialogDescription>
          </DialogHeader>

          <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
            <div className="space-y-1.5">
              <Label>How many</Label>
              <Select value={String(count)} onValueChange={(v) => v && setCount(Number(v))}>
                <SelectTrigger className="w-24">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {COUNTS.map((n) => (
                    <SelectItem key={n} value={String(n)}>{n}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex-1 space-y-1.5">
              <Label htmlFor="ai-co-instruction">Anything to focus on? (optional)</Label>
              <Input
                id="ai-co-instruction"
                value={instruction}
                onChange={(event) => setInstruction(event.target.value)}
                placeholder="e.g. include one outcome on the term project"
                maxLength={500}
              />
            </div>
            <Button onClick={() => generate.mutate()} disabled={generate.isPending || add.isPending}>
              {generate.isPending ? <Loader2 className="animate-spin" /> : <Sparkles />}
              {generate.isPending ? "Writing…" : drafts.length > 0 ? "Write again" : "Write drafts"}
            </Button>
          </div>

          {drafts.length > 0 && (
            <ol className="space-y-3">
              {drafts.map((draft, i) => (
                <li
                  key={draft.key}
                  className={cn(
                    "space-y-2 rounded-lg border p-3 transition-opacity",
                    !draft.selected && "opacity-50"
                  )}
                >
                  <div className="flex items-center justify-between gap-2">
                    <label className="flex items-center gap-2 text-sm font-medium">
                      <input
                        type="checkbox"
                        className="h-4 w-4 accent-primary"
                        checked={draft.selected}
                        onChange={(event) => update(draft.key, { selected: event.target.checked })}
                      />
                      {draft.selected
                        ? `CO${firstNumber + chosen.findIndex((d) => d.key === draft.key)}`
                        : `Draft ${i + 1}`}
                    </label>
                    <div className="flex items-center gap-1">
                      {draft.bloomLevels.map((b) => (
                        <Badge key={b.id} variant="secondary" className="font-mono text-xs">
                          {b.code} {b.name}
                        </Badge>
                      ))}
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon-sm"
                        aria-label="Remove draft"
                        onClick={() => setDrafts((prev) => prev.filter((d) => d.key !== draft.key))}
                      >
                        <Trash2 />
                      </Button>
                    </div>
                  </div>
                  <Textarea
                    rows={2}
                    value={draft.statement}
                    onChange={(event) =>
                      update(draft.key, {
                        statement: event.target.value,
                        edited: event.target.value !== draft.original,
                        warnings: [],
                      })
                    }
                  />
                  {draft.rationale && (
                    <p className="text-xs text-muted-foreground">{draft.rationale}</p>
                  )}
                  <WarningList warnings={draft.warnings} />
                  <RefineStatement
                    curriculumId={curriculumId}
                    courseId={courseId}
                    statement={draft.statement}
                    bloomLevelIds={draft.bloomLevels.map((b) => b.id)}
                    disabled={add.isPending}
                    onApply={(statement, _ids, levels) =>
                      update(draft.key, {
                        statement,
                        bloomLevels: levels.length > 0 ? levels : draft.bloomLevels,
                        edited: true,
                        warnings: [],
                      })
                    }
                  />
                </li>
              ))}
            </ol>
          )}

          {suggestion && (
            <p className="text-xs text-muted-foreground">
              Drafted by {suggestion.model} · {suggestion.prompt_version}
            </p>
          )}

          <DialogFooter showCloseButton>
            <Button
              onClick={() => add.mutate()}
              disabled={chosen.length === 0 || add.isPending || generate.isPending}
            >
              {add.isPending && <Loader2 className="animate-spin" />}
              {chosen.length > 0
                ? `Add ${chosen.length} CO${chosen.length === 1 ? "" : "s"}`
                : "Add COs"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
