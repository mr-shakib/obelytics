"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Bot, Check, CircleAlert, CircleCheck, History, Loader2, X } from "lucide-react"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { type Diagnosis, type ImprovementPlan, improvementApi, type Intervention } from "@/lib/api/improvement"
import { useI18n } from "@/lib/i18n"
import { cn } from "@/lib/utils"

/**
 * Card 4: the improvement agent explains why COs were not attained and proposes changes.
 * It works only through fixed, read-only tools over class aggregates; every cited fact is
 * checked against what the tools returned. Teachers accept or reject each change.
 */
export function ImprovementPanel({ sectionId, canManage }: { sectionId: string; canManage: boolean }) {
  const { t } = useI18n()
  const ti = t.integrity.improvement
  const qc = useQueryClient()
  const key = ["improvement", "plan", sectionId]
  const { data: plan, isLoading } = useQuery({ queryKey: key, queryFn: () => improvementApi.latest(sectionId) })

  const run = useMutation({
    mutationFn: () => improvementApi.run(sectionId),
    onSuccess: (data) => qc.setQueryData(key, data),
  })
  const decide = useMutation({
    mutationFn: ({ planId, id, decision }: { planId: string; id: string; decision: "ACCEPTED" | "REJECTED" }) =>
      improvementApi.decide(planId, id, decision),
    onSuccess: (data) => qc.setQueryData(key, data),
  })

  return (
    <Card>
      <CardHeader>
        <CardTitle>{ti.title}</CardTitle>
        <CardDescription>{ti.description}</CardDescription>
        {canManage && (
          <CardAction>
            <Button size="sm" disabled={run.isPending} onClick={() => run.mutate()}>
              {run.isPending ? <Loader2 className="animate-spin" /> : <Bot />}
              {run.isPending ? ti.working : plan ? ti.runAgain : ti.run}
            </Button>
          </CardAction>
        )}
      </CardHeader>
      <CardContent className="space-y-4">
        {run.isError && (
          <Alert variant="destructive">
            <AlertTitle>{ti.couldNotFinish}</AlertTitle>
            <AlertDescription>{run.error.message}</AlertDescription>
          </Alert>
        )}
        {isLoading ? (
          <div className="h-16 animate-pulse rounded bg-muted" />
        ) : !plan ? (
          <p className="text-sm text-muted-foreground">{ti.noPlan}</p>
        ) : (
          <PlanView
            plan={plan}
            canManage={canManage}
            busy={decide.isPending}
            onDecide={(id, decision) => decide.mutate({ planId: plan.id, id, decision })}
          />
        )}
      </CardContent>
    </Card>
  )
}

function PlanView({
  plan,
  canManage,
  busy,
  onDecide,
}: {
  plan: ImprovementPlan
  canManage: boolean
  busy: boolean
  onDecide: (interventionId: string, decision: "ACCEPTED" | "REJECTED") => void
}) {
  const { t, dateTime } = useI18n()
  const ti = t.integrity.improvement
  return (
    <div className="space-y-4">
      <p className="text-sm leading-relaxed">{plan.summary}</p>
      {plan.follow_up && (
        <p className="flex items-start gap-2 rounded-md bg-muted px-3 py-2 text-sm">
          <History className="mt-0.5 h-4 w-4 shrink-0" />
          <span><span className="font-medium">{ti.sinceLast}</span>{plan.follow_up}</span>
        </p>
      )}
      {plan.diagnoses.length === 0 && (
        <p className="text-sm text-muted-foreground">{ti.noCo}</p>
      )}
      {plan.diagnoses.map((d) => (
        <DiagnosisCard key={d.id} diagnosis={d} canManage={canManage} busy={busy} onDecide={onDecide} />
      ))}
      <details className="rounded-md border px-3 py-2 text-sm">
        <summary className="cursor-pointer text-xs font-medium">
          {ti.howWorked(plan.steps.filter((s) => s.tool).length)}
        </summary>
        <ol className="mt-2 space-y-1.5">
          {plan.steps.map((step, i) => (
            <li key={i} className="flex gap-2 text-xs">
              <span className="w-5 shrink-0 text-muted-foreground">{i + 1}.</span>
              <span>
                {step.tool ? (
                  <span className="font-medium">
                    {ti.tools[step.tool] ?? step.tool}
                    {step.co ? ` — ${step.co}` : ""}
                  </span>
                ) : (
                  <span className="font-medium">{ti.finished}</span>
                )}
                {step.chosen_by === "fixed" && <Badge variant="outline" className="ml-1.5 text-[10px]">{ti.alwaysRun}</Badge>}
                {step.thought && <span className="text-muted-foreground"> · {step.thought}</span>}
              </span>
            </li>
          ))}
        </ol>
      </details>
      <p className="text-xs text-muted-foreground">
        {plan.model} · {plan.prompt_version} · {dateTime(plan.created_at)}
      </p>
    </div>
  )
}

function DiagnosisCard({
  diagnosis,
  canManage,
  busy,
  onDecide,
}: {
  diagnosis: Diagnosis
  canManage: boolean
  busy: boolean
  onDecide: (interventionId: string, decision: "ACCEPTED" | "REJECTED") => void
}) {
  const { t } = useI18n()
  const ti = t.integrity.improvement
  return (
    <div className={cn("space-y-3 rounded-lg border p-4", !diagnosis.supported && "border-amber-300")}>
      <div className="flex flex-wrap items-center gap-2">
        <Badge className="font-mono">{diagnosis.co}</Badge>
        {diagnosis.confidence !== null && (
          <span className="text-xs text-muted-foreground">{t.common.confident(Math.round(diagnosis.confidence * 100))}</span>
        )}
        {!diagnosis.supported && (
          <Badge variant="outline" className="border-amber-300 text-amber-700 dark:text-amber-300">
            <CircleAlert />
            {ti.evidenceNotFound}
          </Badge>
        )}
      </div>
      <p className="text-sm"><span className="font-medium">{ti.whatNumbers}</span>{diagnosis.problem}</p>
      <p className="text-sm"><span className="font-medium">{ti.likelyCause}</span>{diagnosis.likely_cause}</p>
      {diagnosis.evidence.length > 0 && (
        <ul className="space-y-1">
          {diagnosis.evidence.map((e, i) => (
            <li key={i} className="flex items-start gap-1.5 text-xs">
              {e.verified ? (
                <CircleCheck className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-600" />
              ) : (
                <CircleAlert className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-600" />
              )}
              <span>
                <span className="font-mono">{e.ref}</span> — {e.detail}
                {!e.verified && <span className="text-amber-700 dark:text-amber-300">{ti.notInTools}</span>}
              </span>
            </li>
          ))}
        </ul>
      )}
      <div className="space-y-2">
        {diagnosis.interventions.map((i) => (
          <InterventionRow key={i.id} intervention={i} canManage={canManage} busy={busy} onDecide={onDecide} />
        ))}
      </div>
    </div>
  )
}

function InterventionRow({
  intervention,
  canManage,
  busy,
  onDecide,
}: {
  intervention: Intervention
  canManage: boolean
  busy: boolean
  onDecide: (interventionId: string, decision: "ACCEPTED" | "REJECTED") => void
}) {
  const { t } = useI18n()
  const ti = t.integrity.improvement
  const i = intervention
  return (
    <div className={cn("flex flex-wrap items-start justify-between gap-2 rounded-md bg-muted/40 p-2.5", i.decision === "REJECTED" && "opacity-60")}>
      <div className="min-w-0 flex-1 space-y-1">
        <p className="text-sm">{i.action}</p>
        <div className="flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
          <Badge variant="secondary" className="text-[10px] capitalize">{i.kind}</Badge>
          <Badge variant="outline" className="text-[10px]">{ti.effort(i.effort)}</Badge>
          <span>{ti.checkNext}{i.success_measure}</span>
        </div>
      </div>
      {i.decision ? (
        <Badge variant={i.decision === "ACCEPTED" ? "default" : "outline"}>
          {i.decision === "ACCEPTED" ? ti.accepted : ti.rejected}
        </Badge>
      ) : canManage ? (
        <div className="flex gap-1">
          <Button size="xs" disabled={busy} onClick={() => onDecide(i.id, "ACCEPTED")}>
            <Check />
            {ti.accept}
          </Button>
          <Button size="xs" variant="outline" disabled={busy} onClick={() => onDecide(i.id, "REJECTED")}>
            <X />
            {ti.reject}
          </Button>
        </div>
      ) : null}
    </div>
  )
}
