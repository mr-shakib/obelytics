"use client"

import { useState } from "react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { BookmarkCheck, CheckCircle2, Copy, Loader2, RotateCcw, ShieldAlert, Wand2, X } from "lucide-react"
import { toast } from "sonner"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { type Dictionary, useI18n } from "@/lib/i18n"

import { type AuditedQuestion, integrityApi, type QuestionRewrite } from "./api"
import { QuestionText } from "./question-text"

/**
 * "Rewrite to fit the mapping": AI rewrites the question so it really tests the mapped CO and
 * Bloom level, and the auditor — not told the target — checks the result. The marksheet
 * question is never changed; a kept rewrite is wording for the next paper.
 */
export function RewritePanel({
  question,
  canManage,
  invalidateKey,
}: {
  question: AuditedQuestion
  canManage: boolean
  invalidateKey: readonly unknown[]
}) {
  const { t } = useI18n()
  const tr = t.integrity.rewrite
  const qc = useQueryClient()
  const [instruction, setInstruction] = useState("")
  const [result, setResult] = useState<QuestionRewrite | null>(null)

  const rewrite = useMutation({
    mutationFn: () => integrityApi.rewrite(question.question_id, instruction.trim()),
    onSuccess: setResult,
  })
  const decide = useMutation({
    mutationFn: ({ id, decision }: { id: string; decision: "KEPT" | "DISCARDED" }) =>
      integrityApi.decideRewrite(id, decision),
    onSuccess: (data) => {
      setResult(null)
      if (data.decision === "KEPT") toast.success(tr.keptToast(question.label))
      qc.invalidateQueries({ queryKey: invalidateKey })
    },
  })

  const hasTarget = !!question.declared_course_outcome || !!question.declared_bloom_level
  const mismatch = question.audit && ["PARTIAL", "MISALIGNED"].includes(question.audit.alignment)
  const kept = question.kept_rewrite

  if (!question.question_text) return null

  return (
    <div className="space-y-2">
      {kept && !result && <KeptRewrite rewrite={kept} />}

      {canManage && hasTarget && !result && (
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
          <Button
            type="button"
            size="sm"
            variant={mismatch ? "default" : "outline"}
            disabled={rewrite.isPending}
            onClick={() => rewrite.mutate()}
          >
            {rewrite.isPending ? <Loader2 className="animate-spin" /> : <Wand2 />}
            {rewrite.isPending ? tr.rewriting : tr.button}
          </Button>
          <Input
            value={instruction}
            onChange={(event) => setInstruction(event.target.value)}
            placeholder={tr.placeholder}
            maxLength={500}
            className="h-7 text-xs"
            disabled={rewrite.isPending}
          />
        </div>
      )}

      {result && (
        <div className="space-y-3 rounded-lg border border-violet-200 bg-violet-50/60 p-3 dark:border-violet-900/50 dark:bg-violet-950/20">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="flex items-center gap-1.5 text-xs font-medium text-violet-800 dark:text-violet-300">
              <Wand2 className="h-3.5 w-3.5" />
              {tr.rewrittenTo(targetLabel(result, t))}
            </span>
            <Verification rewrite={result} />
          </div>
          <QuestionText text={result.rewritten_text} />
          {result.changes.length > 0 && (
            <ul className="list-disc space-y-0.5 pl-4 text-xs text-muted-foreground">
              {result.changes.map((change, i) => <li key={i}>{change}</li>)}
            </ul>
          )}
          <Checks rewrite={result} />
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              size="sm"
              disabled={decide.isPending}
              onClick={() => decide.mutate({ id: result.id, decision: "KEPT" })}
            >
              <BookmarkCheck />
              {tr.keep}
            </Button>
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={() => {
                navigator.clipboard?.writeText(result.rewritten_text)
                toast.success(tr.copied)
              }}
            >
              <Copy />
              {tr.copy}
            </Button>
            <Button
              type="button"
              size="sm"
              variant="ghost"
              disabled={rewrite.isPending || decide.isPending}
              onClick={() => {
                integrityApi.decideRewrite(result.id, "DISCARDED").catch(() => undefined)
                rewrite.mutate()
              }}
            >
              {rewrite.isPending ? <Loader2 className="animate-spin" /> : <RotateCcw />}
              {tr.tryAgain}
            </Button>
            <Button
              type="button"
              size="sm"
              variant="ghost"
              disabled={decide.isPending}
              onClick={() => decide.mutate({ id: result.id, decision: "DISCARDED" })}
            >
              <X />
              {tr.discard}
            </Button>
          </div>
          <p className="text-xs text-muted-foreground">
            {tr.notChanged} {result.model} · {result.prompt_version}
          </p>
        </div>
      )}
    </div>
  )
}

function targetLabel(rewrite: QuestionRewrite, t: Dictionary) {
  const tr = t.integrity.rewrite
  return [rewrite.target_course_outcome?.code, rewrite.target_bloom_code].filter(Boolean).join(tr.at) || tr.itsMapping
}

function Verification({ rewrite }: { rewrite: QuestionRewrite }) {
  const { t } = useI18n()
  const tr = t.integrity.rewrite
  const final = rewrite.attempts[rewrite.attempts.length - 1]
  const judged = [final?.judged_co, final?.judged_bloom].filter(Boolean).join(" · ")
  const confidence = rewrite.verified_confidence !== null ? ` (${Math.round(rewrite.verified_confidence * 100)}%)` : ""
  if (rewrite.verified_alignment === "ALIGNED") {
    return (
      <Badge variant="outline" className="border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-300">
        <CheckCircle2 />
        {tr.confirms(judged)}{confidence}
      </Badge>
    )
  }
  return (
    <Badge variant="outline" className="border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-300">
      <ShieldAlert />
      {tr.notVerified(judged || tr.unclear)}{confidence}
    </Badge>
  )
}

function Checks({ rewrite }: { rewrite: QuestionRewrite }) {
  const { t } = useI18n()
  const tr = t.integrity.rewrite
  const final = rewrite.attempts[rewrite.attempts.length - 1]
  return (
    <div className="space-y-1 text-xs text-muted-foreground">
      {rewrite.attempts.length > 1 && (
        <p>{tr.tookTries(rewrite.attempts.length, rewrite.attempts[0].judged_bloom ?? tr.unclearShort)}</p>
      )}
      {final?.rationale && (
        <p>
          <span className="font-medium">{tr.auditor}</span>
          {final.rationale}
        </p>
      )}
    </div>
  )
}

function KeptRewrite({ rewrite }: { rewrite: QuestionRewrite }) {
  const { t } = useI18n()
  return (
    <details className="rounded-md border bg-muted/30 px-3 py-2 text-sm">
      <summary className="cursor-pointer text-xs font-medium">
        {t.integrity.rewrite.keptSummary(targetLabel(rewrite, t), rewrite.verified_alignment === "ALIGNED")}
      </summary>
      <div className="mt-2">
        <QuestionText text={rewrite.rewritten_text} />
      </div>
    </details>
  )
}
