"use client"

import { useState } from "react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { AlertTriangle, Check, CheckCircle2, CircleHelp, Loader2, Sparkles, X, XCircle } from "lucide-react"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Textarea } from "@/components/ui/textarea"
import { queryKeys } from "@/lib/query-keys"
import { cn } from "@/lib/utils"

import {
  type AuditedQuestion,
  bloomLabel,
  type BloomLevelRef,
  type CourseOutcomeRef,
  type ExamType,
  type IntegrityOverview,
  integrityApi,
  isJobActive,
  type QuestionAudit,
} from "./api"
import { JobProgress } from "./paper-panel"
import { QuestionText } from "./question-text"

const VERDICTS = {
  ALIGNED: {
    label: "Matches the mapping",
    icon: CheckCircle2,
    className: "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-300",
  },
  PARTIAL: {
    label: "Different Bloom level",
    icon: AlertTriangle,
    className: "border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-300",
  },
  MISALIGNED: {
    label: "Tests a different CO",
    icon: XCircle,
    className: "border-red-200 bg-red-50 text-red-700 dark:border-red-900 dark:bg-red-950/40 dark:text-red-300",
  },
  ABSTAINED: {
    label: "AI not sure",
    icon: CircleHelp,
    className: "border-border bg-muted text-muted-foreground",
  },
} as const

type ReviewInput = { auditId: string; decision: "ACCEPT" | "OVERRIDE"; reason?: string }

export function AuditPanel({
  overview,
  sectionId,
  examType,
  canManage,
}: {
  overview: IntegrityOverview
  sectionId: string
  examType: ExamType
  canManage: boolean
}) {
  const qc = useQueryClient()
  const key = queryKeys.integrity.overview(sectionId, examType)
  const [disagreeWith, setDisagreeWith] = useState<AuditedQuestion | null>(null)
  const summary = overview.summary
  const job = overview.job
  const busy = isJobActive(job)
  const auditing = busy && job?.kind === "AUDIT"
  const auditFailed = job?.kind === "AUDIT" && job.status === "FAILED"

  const run = useMutation({
    mutationFn: () => integrityApi.runAudit(sectionId, examType),
    onSuccess: (data) => qc.setQueryData(key, data),
  })
  const review = useMutation({
    mutationFn: ({ auditId, decision, reason }: ReviewInput) => integrityApi.review(auditId, decision, reason),
    onSuccess: (data) => {
      qc.setQueryData(key, data)
      setDisagreeWith(null)
    },
  })

  return (
    <Card>
      <CardHeader>
        <CardTitle>2. AI audit</CardTitle>
        <CardDescription>
          The AI judges what each question really demands and which outcome it tests without seeing your
          mapping, then compares the two. It never changes marks or attainment.
        </CardDescription>
        {canManage && (
          <CardAction>
            <Button
              size="sm"
              disabled={run.isPending || busy || summary.with_text === 0}
              onClick={() => run.mutate()}
            >
              {run.isPending || auditing ? <Loader2 className="animate-spin" /> : <Sparkles />}
              {summary.audited > 0 ? "Run again" : "Run audit"}
            </Button>
          </CardAction>
        )}
      </CardHeader>
      <CardContent className="space-y-3">
        {auditing && job && <JobProgress job={job} title="Judging the questions…" unit="Question" />}
        {run.isError && (
          <Alert variant="destructive">
            <AlertTitle>The audit could not start</AlertTitle>
            <AlertDescription>{run.error.message}</AlertDescription>
          </Alert>
        )}
        {auditFailed && !run.isError && (
          <Alert variant="destructive">
            <AlertTitle>The last audit could not finish</AlertTitle>
            <AlertDescription>{job.error} Earlier results, if any, are unchanged.</AlertDescription>
          </Alert>
        )}
        {overview.questions.length === 0 ? (
          <p className="text-sm text-muted-foreground">This exam has no marksheet questions yet.</p>
        ) : (
          overview.questions.map((question) => (
            <QuestionCard
              key={question.question_id}
              question={question}
              canManage={canManage}
              busy={review.isPending}
              onAccept={(audit) => review.mutate({ auditId: audit.id, decision: "ACCEPT" })}
              onDisagree={() => setDisagreeWith(question)}
            />
          ))
        )}
      </CardContent>
      <DisagreeDialog
        key={disagreeWith?.question_id ?? "closed"}
        question={disagreeWith}
        pending={review.isPending}
        onClose={() => setDisagreeWith(null)}
        onSubmit={(reason) => {
          if (disagreeWith?.audit) review.mutate({ auditId: disagreeWith.audit.id, decision: "OVERRIDE", reason })
        }}
      />
    </Card>
  )
}

function QuestionCard({
  question,
  canManage,
  busy,
  onAccept,
  onDisagree,
}: {
  question: AuditedQuestion
  canManage: boolean
  busy: boolean
  onAccept: (audit: QuestionAudit) => void
  onDisagree: () => void
}) {
  const audit = question.audit
  const verdict = audit ? VERDICTS[audit.alignment] : null
  const judged = audit !== null && audit.alignment !== "ABSTAINED"
  const bloomDiffers =
    judged && question.declared_bloom_level !== null &&
    audit.ai_bloom_level?.code !== question.declared_bloom_level.code
  const coDiffers =
    judged && question.declared_course_outcome !== null &&
    audit.ai_course_outcome?.id !== question.declared_course_outcome.id

  return (
    <div className="space-y-3 rounded-lg border p-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-semibold">{question.label}</span>
          <span className="text-xs text-muted-foreground">{question.max_marks} marks</span>
          {verdict && (
            <Badge variant="outline" className={verdict.className}>
              <verdict.icon />
              {verdict.label}
            </Badge>
          )}
          {judged && audit.confidence !== null && (
            <span className="text-xs text-muted-foreground">
              {Math.round(audit.confidence * 100)}% confident
              {audit.samples != null && audit.samples > 1 && audit.agreement != null &&
                ` · ${Math.round(audit.agreement * audit.samples)} of ${audit.samples} independent judgments agree`}
            </span>
          )}
        </div>
        {audit && (
          <ReviewControls
            audit={audit}
            canManage={canManage}
            busy={busy}
            onAccept={() => onAccept(audit)}
            onDisagree={onDisagree}
          />
        )}
      </div>

      {question.question_text ? (
        <QuestionText text={question.question_text} />
      ) : (
        <p className="text-sm text-muted-foreground">
          No wording yet. Upload the paper above, check it, and save it to the marksheet.
        </p>
      )}

      {audit && (
        <>
          <div className="grid gap-3 sm:grid-cols-2">
            <Judgment
              title="Mapped by the teacher"
              bloom={question.declared_bloom_level}
              outcome={question.declared_course_outcome}
            />
            <Judgment
              title="Judged by the AI"
              bloom={audit.ai_bloom_level}
              outcome={audit.ai_course_outcome}
              bloomDiffers={bloomDiffers}
              outcomeDiffers={coDiffers}
            />
          </div>
          {audit.evidence_quote && (
            <blockquote className="border-l-2 pl-3 text-sm italic text-muted-foreground">
              “{audit.evidence_quote.replace(/^["'“”]+|["'“”]+$/g, "")}”
            </blockquote>
          )}
          {audit.rationale && (
            <p className="text-sm">
              <span className="font-medium">Why: </span>
              {audit.rationale}
            </p>
          )}
          {audit.review_status === "OVERRIDDEN" && audit.override_reason && (
            <p className="rounded-md bg-muted px-3 py-2 text-sm">
              <span className="font-medium">Teacher disagreed: </span>
              {audit.override_reason}
            </p>
          )}
          <p className="text-xs text-muted-foreground">
            {audit.model} · {audit.prompt_version} · {new Date(audit.created_at).toLocaleString()}
          </p>
        </>
      )}
    </div>
  )
}

function Judgment({
  title,
  bloom,
  outcome,
  bloomDiffers = false,
  outcomeDiffers = false,
}: {
  title: string
  bloom: BloomLevelRef | null
  outcome: CourseOutcomeRef | null
  bloomDiffers?: boolean
  outcomeDiffers?: boolean
}) {
  return (
    <div className="space-y-2 rounded-md bg-muted/40 p-3">
      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{title}</p>
      <div className="flex flex-wrap gap-2">
        <Badge
          variant="outline"
          className={cn(bloomDiffers && "border-amber-400 bg-amber-50 text-amber-800 dark:bg-amber-950/40 dark:text-amber-300")}
        >
          {bloomLabel(bloom)}
        </Badge>
        <Badge
          variant="outline"
          className={cn(outcomeDiffers && "border-red-400 bg-red-50 text-red-800 dark:bg-red-950/40 dark:text-red-300")}
        >
          {outcome?.code ?? "—"}
        </Badge>
      </div>
      {outcome && <p className="text-xs text-muted-foreground">{outcome.statement}</p>}
    </div>
  )
}

function ReviewControls({
  audit,
  canManage,
  busy,
  onAccept,
  onDisagree,
}: {
  audit: QuestionAudit
  canManage: boolean
  busy: boolean
  onAccept: () => void
  onDisagree: () => void
}) {
  if (audit.review_status === "PENDING") {
    return canManage ? (
      <div className="flex gap-2">
        <Button size="sm" variant="outline" disabled={busy} onClick={onAccept}>
          <Check />
          Agree
        </Button>
        <Button size="sm" variant="outline" disabled={busy} onClick={onDisagree}>
          <X />
          Disagree
        </Button>
      </div>
    ) : (
      <Badge variant="secondary">Awaiting review</Badge>
    )
  }
  const accepted = audit.review_status === "ACCEPTED"
  return (
    <div className="flex items-center gap-2">
      <Badge variant="secondary">{accepted ? "You agreed" : "You disagreed"}</Badge>
      {canManage && (
        <Button size="xs" variant="ghost" disabled={busy} onClick={accepted ? onDisagree : onAccept}>
          {accepted ? "Disagree instead" : "Agree instead"}
        </Button>
      )}
    </div>
  )
}

function DisagreeDialog({
  question,
  pending,
  onClose,
  onSubmit,
}: {
  question: AuditedQuestion | null
  pending: boolean
  onClose: () => void
  onSubmit: (reason: string) => void
}) {
  const [reason, setReason] = useState("")
  return (
    <Dialog open={question !== null} onOpenChange={(open) => { if (!open) onClose() }}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Disagree with the AI on {question?.label}</DialogTitle>
          <DialogDescription>
            Say why the question does test what you mapped. Your reason is kept with the audit record.
          </DialogDescription>
        </DialogHeader>
        <Textarea
          value={reason}
          rows={4}
          placeholder="For example: students must derive the normal equations themselves, not follow a taught routine."
          onChange={(event) => setReason(event.target.value)}
        />
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button disabled={pending || !reason.trim()} onClick={() => onSubmit(reason.trim())}>
            {pending && <Loader2 className="animate-spin" />}
            Save
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
