"use client"

import { useQuery } from "@tanstack/react-query"
import { CheckCircle2, CircleDashed, XCircle } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { useI18n } from "@/lib/i18n"
import { queryKeys } from "@/lib/query-keys"
import { cn } from "@/lib/utils"

import { type COFigures, type EvidenceOutcome, type EvidenceQuestion, evidenceApi } from "./api"

const VERDICT_CLASS: Record<EvidenceOutcome["verdict"], string> = {
  UNCHANGED: "text-muted-foreground",
  LOWER: "text-amber-700 dark:text-amber-400",
  NOT_SUPPORTED: "text-red-700 dark:text-red-400",
  NO_EVIDENCE: "text-red-700 dark:text-red-400",
}

function pct(value: number) {
  return `${Math.round(value)}%`
}

function Figure({ title, figures, threshold }: { title: string; figures: COFigures | null; threshold: number }) {
  const { t } = useI18n()
  return (
    <div className="space-y-1">
      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{title}</p>
      {figures ? (
        <>
          <div className="flex items-center gap-2">
            <span className="text-2xl font-semibold tabular-nums">{pct(figures.attained_share_pct)}</span>
            <Badge
              variant="outline"
              className={cn(
                figures.is_attained
                  ? "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-300"
                  : "border-red-200 bg-red-50 text-red-700 dark:border-red-900 dark:bg-red-950/40 dark:text-red-300",
              )}
            >
              {figures.is_attained ? t.common.attained : t.common.notAttained}
            </Badge>
          </div>
          <p className="text-xs text-muted-foreground">
            {t.integrity.evidence.figureNote(threshold, pct(figures.average_pct), figures.max_marks)}
          </p>
        </>
      ) : (
        <p className="text-sm text-muted-foreground">{t.integrity.evidence.noQuestionsLeft}</p>
      )}
    </div>
  )
}

function QuestionChip({ question }: { question: EvidenceQuestion }) {
  const { t } = useI18n()
  const te = t.integrity.evidence
  const exam = question.exam_type === "MID" ? te.examMid : te.examFinal
  if (question.status === "CONTRADICTED") {
    return (
      <Badge variant="outline" className="border-red-200 text-red-700 dark:border-red-900 dark:text-red-300">
        <XCircle />
        {exam} {question.label} {te.tests(question.ai_course_outcome?.code ?? te.anotherOutcome)}
        {question.review_status === "PENDING" && te.awaitingReview}
      </Badge>
    )
  }
  if (question.status === "UNVERIFIED") {
    return (
      <Badge variant="outline" className="text-muted-foreground">
        <CircleDashed />
        {exam} {question.label} {question.alignment === "ABSTAINED" ? te.aiNotSure : te.notAudited}
      </Badge>
    )
  }
  return (
    <Badge variant="outline" className="border-emerald-200 text-emerald-700 dark:border-emerald-900 dark:text-emerald-300">
      <CheckCircle2 />
      {exam} {question.label}
      {question.review_status === "OVERRIDDEN" && te.teachersMapping}
    </Badge>
  )
}

export function EvidencePanel({ sectionId }: { sectionId: string }) {
  const { t } = useI18n()
  const te = t.integrity.evidence
  const { data, isLoading } = useQuery({
    queryKey: queryKeys.integrity.evidence(sectionId),
    queryFn: () => evidenceApi.get(sectionId),
  })

  return (
    <Card>
      <CardHeader>
        <CardTitle>{te.title}</CardTitle>
        <CardDescription>{te.description}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {isLoading || !data ? (
          <div className="h-24 animate-pulse rounded-lg bg-muted" />
        ) : data.total_students === 0 || data.outcomes.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            {data.outcomes.length === 0 ? te.noMapped : te.noStudents}
          </p>
        ) : (
          <>
            {data.summary.contradicted_pending_review > 0 && (
              <p className="text-sm text-muted-foreground">{te.pendingNote(data.summary.contradicted_pending_review)}</p>
            )}
            {data.outcomes.map((outcome) => {

              return (
                <div key={outcome.course_outcome.id} className="space-y-3 rounded-lg border p-4">
                  <div>
                    <p className="font-semibold">{outcome.course_outcome.code}</p>
                    <p className="text-sm text-muted-foreground">{outcome.course_outcome.statement}</p>
                  </div>
                  <div className="grid gap-4 sm:grid-cols-2">
                    <Figure title={te.reported} figures={outcome.reported} threshold={data.threshold_pct} />
                    <Figure title={te.supported} figures={outcome.evidence} threshold={data.threshold_pct} />
                  </div>
                  <p className={cn("text-sm", VERDICT_CLASS[outcome.verdict])}>{te.verdicts[outcome.verdict]}</p>
                  <div className="flex flex-wrap gap-1.5">
                    {outcome.questions.map((question) => (
                      <QuestionChip key={question.question_id} question={question} />
                    ))}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {te.auditedShare(pct(outcome.judged_marks_share * 100))}
                  </p>
                </div>
              )
            })}
          </>
        )}
      </CardContent>
    </Card>
  )
}
