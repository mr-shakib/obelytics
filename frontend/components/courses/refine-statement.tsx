"use client"

import { useState } from "react"
import { useMutation } from "@tanstack/react-query"
import { AlertTriangle, Check, Loader2, PenLine, RotateCcw, Sparkles, X } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { authoringApi, type BloomRef } from "@/lib/api/authoring"

interface Props {
  curriculumId?: string
  courseId?: string
  statement: string
  bloomLevelIds: string[]
  /** The CO being edited, so it is not reported as repeating itself. */
  courseOutcomeId?: string
  /** Also offer "Write with AI": draft a new CO from the course content. */
  allowWrite?: boolean
  onApply: (statement: string, bloomLevelIds: string[], bloomLevels: BloomRef[]) => void
  disabled?: boolean
}

type Suggestion = {
  mode: "write" | "refine"
  suggestionId: string
  statement: string
  bloomLevels: BloomRef[]
  /** write: why this outcome; refine: what changed */
  notes: string[]
  warnings: string[]
  /** refine only: the same checks on the teacher's wording */
  originalWarnings: string[]
}

const MIN_LENGTH = 3

/**
 * AI help for one CO statement.
 * - Write with AI: drafts a new CO for the course (optionally on a given focus).
 * - Refine with AI: improves the wording in the box — the teacher's own or an AI draft.
 * The suggestion is shown beside the form; nothing changes until "Use this".
 */
export function RefineStatement({
  curriculumId,
  courseId,
  statement,
  bloomLevelIds,
  courseOutcomeId,
  allowWrite = false,
  onApply,
  disabled,
}: Props) {
  const [instruction, setInstruction] = useState("")
  const [result, setResult] = useState<Suggestion | null>(null)

  const write = useMutation({
    mutationFn: () =>
      authoringApi.draft({
        curriculum_id: curriculumId!,
        course_id: courseId!,
        count: 1,
        instruction: instruction.trim() || undefined,
      }),
    onSuccess: (data) => {
      const outcome = data.outcomes[0]
      if (!outcome) return
      setResult({
        mode: "write",
        suggestionId: data.suggestion_id,
        statement: outcome.statement,
        bloomLevels: outcome.bloom_levels,
        notes: outcome.rationale ? [outcome.rationale] : [],
        warnings: outcome.warnings,
        originalWarnings: [],
      })
    },
  })

  const refine = useMutation({
    mutationFn: () =>
      authoringApi.refine({
        curriculum_id: curriculumId!,
        course_id: courseId!,
        statement,
        bloom_level_ids: bloomLevelIds,
        instruction: instruction.trim() || undefined,
        course_outcome_id: courseOutcomeId,
      }),
    onSuccess: (data) =>
      setResult({
        mode: "refine",
        suggestionId: data.suggestion_id,
        statement: data.statement,
        bloomLevels: data.bloom_levels,
        notes: data.changes,
        warnings: data.warnings,
        originalWarnings: data.original_warnings,
      }),
  })

  const busy = write.isPending || refine.isPending
  const hasCourse = !!curriculumId && !!courseId
  const canRefine = hasCourse && statement.trim().length >= MIN_LENGTH
  const hasText = statement.trim().length > 0

  function run(mode: "write" | "refine") {
    if (result) authoringApi.decide(result.suggestionId, "REJECTED")
    setResult(null)
    if (mode === "write") write.mutate()
    else refine.mutate()
  }

  function close(decision: "ACCEPTED" | "REJECTED") {
    if (result) authoringApi.decide(result.suggestionId, decision)
    setResult(null)
  }

  function use() {
    if (!result) return
    onApply(result.statement, result.bloomLevels.map((b) => b.id), result.bloomLevels)
    close("ACCEPTED")
    setInstruction("")
  }

  return (
    <div className="space-y-2">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
        <div className="flex shrink-0 gap-2">
          {allowWrite && (
            <Button
              type="button"
              variant={hasText ? "outline" : "default"}
              size="sm"
              disabled={disabled || !hasCourse || busy}
              onClick={() => run("write")}
              title={hasCourse ? "Let AI write a course outcome for this course" : "Choose a course first"}
            >
              {write.isPending ? <Loader2 className="animate-spin" /> : <PenLine />}
              {write.isPending ? "Writing…" : "Write with AI"}
            </Button>
          )}
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={disabled || !canRefine || busy}
            onClick={() => run("refine")}
            title={
              !hasCourse
                ? "Choose a course first"
                : canRefine
                  ? "Let AI improve this statement"
                  : "Write a statement first"
            }
          >
            {refine.isPending ? <Loader2 className="animate-spin" /> : <Sparkles />}
            {refine.isPending ? "Refining…" : "Refine with AI"}
          </Button>
        </div>
        <Input
          value={instruction}
          onChange={(event) => setInstruction(event.target.value)}
          placeholder={
            allowWrite
              ? "Optional: what it should cover or change, e.g. the term project"
              : "Optional: what should change? e.g. make it lab-focused"
          }
          maxLength={500}
          className="h-7 text-xs"
          disabled={disabled || busy}
          onKeyDown={(event) => {
            if (event.key !== "Enter") return
            event.preventDefault()
            if (busy) return
            if (canRefine) run("refine")
            else if (allowWrite && hasCourse) run("write")
          }}
        />
      </div>

      {result && (
        <div className="space-y-3 rounded-lg border border-violet-200 bg-violet-50/60 p-3 dark:border-violet-900/50 dark:bg-violet-950/20">
          <div className="flex items-center gap-1.5 text-xs font-medium text-violet-800 dark:text-violet-300">
            <Sparkles className="h-3.5 w-3.5" />
            {result.mode === "write" ? "AI draft" : "AI suggestion"} — check it before you use it
          </div>
          <p className="text-sm leading-relaxed">{result.statement}</p>
          {result.bloomLevels.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {result.bloomLevels.map((b) => (
                <Badge key={b.id} variant="secondary" className="font-mono text-xs">
                  {b.code} {b.name}
                </Badge>
              ))}
            </div>
          )}
          {result.notes.length > 0 && (
            <div className="space-y-1">
              <p className="text-xs font-medium text-muted-foreground">
                {result.mode === "write" ? "Why this outcome" : "What changed"}
              </p>
              <ul className="list-disc space-y-0.5 pl-4 text-xs text-muted-foreground">
                {result.notes.map((note, i) => <li key={i}>{note}</li>)}
              </ul>
            </div>
          )}
          {result.originalWarnings.length > 0 && (
            <div className="space-y-1">
              <p className="text-xs font-medium text-muted-foreground">In your current wording</p>
              <ul className="list-disc space-y-0.5 pl-4 text-xs text-muted-foreground">
                {result.originalWarnings.map((w, i) => <li key={i}>{w}</li>)}
              </ul>
            </div>
          )}
          <WarningList warnings={result.warnings} />
          <div className="flex flex-wrap gap-2">
            <Button type="button" size="sm" onClick={use}>
              <Check />
              Use this
            </Button>
            <Button type="button" size="sm" variant="outline" onClick={() => close("REJECTED")}>
              <X />
              {result.mode === "write" ? "Discard" : "Keep mine"}
            </Button>
            <Button
              type="button"
              size="sm"
              variant="ghost"
              disabled={busy}
              onClick={() => run(result.mode)}
            >
              {busy ? <Loader2 className="animate-spin" /> : <RotateCcw />}
              Try again
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}

export function WarningList({ warnings }: { warnings: string[] }) {
  if (warnings.length === 0) return null
  return (
    <ul className="space-y-1">
      {warnings.map((w, i) => (
        <li key={i} className="flex items-start gap-1.5 text-xs text-amber-800 dark:text-amber-300">
          <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          {w}
        </li>
      ))}
    </ul>
  )
}
