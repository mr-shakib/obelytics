"use client"

import { useQuery } from "@tanstack/react-query"
import { CircleCheck, CircleDashed, Hourglass } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { type StudentSkill, workforceApi } from "@/lib/api/workforce"
import { useI18n } from "@/lib/i18n"
import { cn } from "@/lib/utils"

const STATUS = {
  verified: {
    icon: CircleCheck,
    className: "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-300",
  },
  developing: {
    icon: Hourglass,
    className: "border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-300",
  },
  not_yet: {
    icon: CircleDashed,
    className: "border-border bg-muted text-muted-foreground",
  },
} as const

/**
 * A student's verified skills: the skills employers ask for in the program's job postings,
 * matched with the course outcomes this student attained. Computed in code from the
 * student's own published results; no model sees them.
 */
export function MySkillsClient() {
  const { t, locale } = useI18n()
  const ts = t.student.skills
  const { data, isLoading } = useQuery({ queryKey: ["student", "skills"], queryFn: workforceApi.mySkills })

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-28 w-full" />
        {[...Array(3)].map((_, i) => <Skeleton key={i} className="h-16 w-full" />)}
      </div>
    )
  }

  const statusLabel = { verified: ts.verified, developing: ts.developing, not_yet: ts.notYetTaught }

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <h1 className="text-2xl font-bold">{ts.title}</h1>
        <p className="text-sm text-muted-foreground">{ts.description}</p>
      </div>

      {!data || data.skills.length === 0 ? (
        <p className="text-sm text-muted-foreground">{ts.none}</p>
      ) : (
        <>
          <Card>
            <CardHeader>
              <CardTitle>{ts.readiness}</CardTitle>
              <CardDescription>{ts.readinessNote(data.summary.top_verified, data.summary.top_n)}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div
                className="h-2.5 w-full overflow-hidden rounded-full bg-muted"
                role="progressbar"
                aria-valuemin={0}
                aria-valuemax={data.summary.top_n}
                aria-valuenow={data.summary.top_verified}
              >
                <div
                  className="h-full rounded-full bg-emerald-500"
                  style={{ width: `${data.summary.top_n ? (data.summary.top_verified / data.summary.top_n) * 100 : 0}%` }}
                />
              </div>
              <div className="flex flex-wrap gap-2 text-xs">
                {(["verified", "developing", "not_yet"] as const).map((status) => (
                  <Badge key={status} variant="outline" className={STATUS[status].className}>
                    {statusLabel[status]}: {data.summary[status]}
                  </Badge>
                ))}
              </div>
              {data.analysis_date && (
                <p className="text-xs text-muted-foreground">
                  {ts.basedOn(new Date(data.analysis_date).toLocaleDateString(locale === "bn" ? "bn-BD" : undefined))}
                </p>
              )}
            </CardContent>
          </Card>

          <div className="space-y-2">
            {data.skills.map((skill) => (
              <SkillRow key={skill.skill} skill={skill} total={data.posting_count} label={statusLabel[skill.status]} />
            ))}
          </div>
        </>
      )}
    </div>
  )
}

function SkillRow({ skill, total, label }: { skill: StudentSkill; total: number; label: string }) {
  const { t } = useI18n()
  const ts = t.student.skills
  const status = STATUS[skill.status]
  return (
    <div className={cn("space-y-2 rounded-lg border p-3", skill.status === "not_yet" && "opacity-80")}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-medium">{skill.skill}</span>
          <Badge variant="outline" className={status.className}>
            <status.icon />
            {label}
          </Badge>
        </div>
        <span className="text-xs text-muted-foreground">{ts.demand(skill.postings, total)}</span>
      </div>
      {skill.evidence.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {skill.evidence.map((e) => (
            <span
              key={`${e.course_code}-${e.co_code}`}
              title={`${e.course_title}: ${e.statement}`}
              className={cn(
                "rounded-full px-2 py-0.5 font-mono text-xs",
                e.attained
                  ? "bg-emerald-50 text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-300"
                  : "bg-amber-50 text-amber-800 dark:bg-amber-950/40 dark:text-amber-300",
              )}
            >
              {ts.coResult(e.course_code, e.co_code, e.attainment_pct)}
            </span>
          ))}
          {skill.program_outcomes.map((po) => (
            <span key={po} className="rounded-full bg-violet-100 px-2 py-0.5 font-mono text-xs text-violet-800 dark:bg-violet-900/40 dark:text-violet-200">
              {po}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}
