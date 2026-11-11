"use client"

import { useQuery } from "@tanstack/react-query"
import { CheckCircle2, CircleDashed, XCircle } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { queryKeys } from "@/lib/query-keys"
import { cn } from "@/lib/utils"

import { type COFigures, type EvidenceOutcome, type EvidenceQuestion, evidenceApi } from "./api"

const VERDICT_TEXT: Record<EvidenceOutcome["verdict"], { text: string; className: string }> = {
  UNCHANGED: { text: "The audited questions back the reported figure.", className: "text-muted-foreground" },
  LOWER: {
    text: "Lower once questions that test another outcome are left out.",
    className: "text-amber-700 dark:text-amber-400",
  },
  NOT_SUPPORTED: {
    text: "Reported as attained, but the questions that really test this outcome do not show it.",
    className: "text-red-700 dark:text-red-400",
  },
  NO_EVIDENCE: {
    text: "Every question mapped to this outcome tests something else, so nothing in the exam backs it.",
    className: "text-red-700 dark:text-red-400",
  },
}

function pct(value: number) {
  return `${Math.round(value)}%`
}

function Figure({ title, figures, threshold }: { title: string; figures: COFigures | null; threshold: number }) {
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
              {figures.is_attained ? "Attained" : "Not attained"}
            </Badge>
          </div>
          <p className="text-xs text-muted-foreground">
            of students scored {threshold}% or more · average {pct(figures.average_pct)} · from {figures.max_marks} marks
          </p>
        </>
      ) : (
        <p className="text-sm text-muted-foreground">No questions left to count</p>
      )}
    </div>
  )
}

function QuestionChip({ question }: { question: EvidenceQuestion }) {
  const exam = question.exam_type === "MID" ? "Mid" : "Final"
  if (question.status === "CONTRADICTED") {
    return (
      <Badge variant="outline" className="border-red-200 text-red-700 dark:border-red-900 dark:text-red-300">
        <XCircle />
        {exam} {question.label} tests {question.ai_course_outcome?.code ?? "another outcome"}
        {question.review_status === "PENDING" && " · awaiting review"}
      </Badge>
    )
  }
  if (question.status === "UNVERIFIED") {
    return (
      <Badge variant="outline" className="text-muted-foreground">
        <CircleDashed />
        {exam} {question.label} {question.alignment === "ABSTAINED" ? "· AI not sure" : "· not audited"}
      </Badge>
    )
  }
  return (
    <Badge variant="outline" className="border-emerald-200 text-emerald-700 dark:border-emerald-900 dark:text-emerald-300">
      <CheckCircle2 />
      {exam} {question.label}
      {question.review_status === "OVERRIDDEN" && " · teacher's mapping"}
    </Badge>
  )
}

export function EvidencePanel({ sectionId }: { sectionId: string }) {
  const { data, isLoading } = useQuery({
    queryKey: queryKeys.integrity.evidence(sectionId),
    queryFn: () => evidenceApi.get(sectionId),
  })

  return (
    <Card>
      <CardHeader>
        <CardTitle>3. Is attainment backed by the exam?</CardTitle>
        <CardDescription>
          The official CO attainment for this section (mid term and final) next to the same figure counting only
          questions the audit does not contradict. The official results are not changed.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {isLoading || !data ? (
          <div className="h-24 animate-pulse rounded-lg bg-muted" />
        ) : data.total_students === 0 || data.outcomes.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            {data.outcomes.length === 0
              ? "No marksheet questions are mapped to course outcomes yet."
              : "No students are enrolled in this section yet."}
          </p>
        ) : (
          <>
            {data.summary.contradicted_pending_review > 0 && (
              <p className="text-sm text-muted-foreground">
                {data.summary.contradicted_pending_review} flagged question
                {data.summary.contradicted_pending_review === 1 ? " is" : "s are"} still awaiting your review. If you
                disagree with the AI, your mapping counts again.
              </p>
            )}
            {data.outcomes.map((outcome) => {
              const verdict = VERDICT_TEXT[outcome.verdict]
              return (
                <div key={outcome.course_outcome.id} className="space-y-3 rounded-lg border p-4">
                  <div>
                    <p className="font-semibold">{outcome.course_outcome.code}</p>
                    <p className="text-sm text-muted-foreground">{outcome.course_outcome.statement}</p>
                  </div>
                  <div className="grid gap-4 sm:grid-cols-2">
                    <Figure title="Reported" figures={outcome.reported} threshold={data.threshold_pct} />
                    <Figure title="Supported by evidence" figures={outcome.evidence} threshold={data.threshold_pct} />
                  </div>
                  <p className={cn("text-sm", verdict.className)}>{verdict.text}</p>
                  <div className="flex flex-wrap gap-1.5">
                    {outcome.questions.map((question) => (
                      <QuestionChip key={question.question_id} question={question} />
                    ))}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {`${pct(outcome.judged_marks_share * 100)} of this outcome's marks have been audited.`}
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
