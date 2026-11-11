"use client"

import { useEffect, useRef, useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { toast } from "sonner"

import { PageHeader } from "@/components/shared/page-header"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { usePermission } from "@/hooks/use-permission"
import { queryKeys } from "@/lib/query-keys"
import { cn } from "@/lib/utils"

import {
  type AuditableSection,
  type ExamType,
  type IntegrityJob,
  type IntegrityOverview,
  integrityApi,
  isJobActive,
} from "./api"
import { AuditPanel } from "./audit-panel"
import { PaperPanel } from "./paper-panel"

const EXAMS: { value: ExamType; label: string }[] = [
  { value: "MID", label: "Mid term" },
  { value: "FINAL", label: "Final" },
]

function sectionLabel(section: AuditableSection) {
  return `${section.course_code} ${section.course_title} · ${section.section_name} · ${section.term_name}`
}

export function IntegrityClient() {
  const canManage = usePermission("integrity.manage")
  const [chosenSectionId, setChosenSectionId] = useState<string | null>(null)
  const [examType, setExamType] = useState<ExamType>("FINAL")

  const { data: sections = [], isLoading: sectionsLoading } = useQuery({
    queryKey: queryKeys.integrity.sections,
    queryFn: integrityApi.sections,
  })
  const sectionId = chosenSectionId ?? sections[0]?.id ?? null

  const { data: overview, isLoading: overviewLoading } = useQuery({
    queryKey: queryKeys.integrity.overview(sectionId ?? "", examType),
    queryFn: () => integrityApi.overview(sectionId as string, examType),
    enabled: sectionId !== null,
    // Reading and auditing run in the background; follow them until they finish.
    refetchInterval: (query) => (isJobActive(query.state.data?.job) ? 2000 : false),
  })
  useJobNotifications(overview?.job)

  return (
    <div className="max-w-6xl space-y-6">
      <PageHeader
        title="Assessment Integrity"
        description="Checks whether each exam question really tests the Bloom level and course outcome it is mapped to. The AI only advises: marks and attainment never change."
      />

      <div className="flex flex-wrap items-center gap-3">
        <Select
          value={sectionId}
          onValueChange={(value) => { if (value != null) setChosenSectionId(value as string) }}
        >
          <SelectTrigger className="w-full sm:w-[36rem]" disabled={sections.length === 0}>
            <SelectValue placeholder={sectionsLoading ? "Loading sections…" : "Choose a section"}>
              {sectionId ? sectionLabel(sections.find((s) => s.id === sectionId) ?? sections[0]) : undefined}
            </SelectValue>
          </SelectTrigger>
          <SelectContent>
            {sections.map((section) => (
              <SelectItem key={section.id} value={section.id}>{sectionLabel(section)}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <div className="inline-flex rounded-lg border p-0.5">
          {EXAMS.map((exam) => (
            <Button
              key={exam.value}
              size="sm"
              variant={examType === exam.value ? "default" : "ghost"}
              onClick={() => setExamType(exam.value)}
            >
              {exam.label}
            </Button>
          ))}
        </div>
      </div>

      {!sectionsLoading && sections.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            No sections to audit. Sections you teach or lead appear here.
          </CardContent>
        </Card>
      ) : overviewLoading || !overview || !sectionId ? (
        <div className="space-y-4">
          <div className="h-20 animate-pulse rounded-lg bg-muted" />
          <div className="h-64 animate-pulse rounded-lg bg-muted" />
        </div>
      ) : (
        <>
          <Summary overview={overview} />
          <PaperPanel overview={overview} sectionId={sectionId} examType={examType} canManage={canManage} />
          <AuditPanel overview={overview} sectionId={sectionId} examType={examType} canManage={canManage} />
        </>
      )}
    </div>
  )
}

function jobDoneMessage(job: IntegrityJob) {
  const result = job.result ?? {}
  if (job.kind === "READ_PAPER") {
    const flagged = result.flagged ? ` ${result.flagged} need a closer look.` : ""
    return `Read ${result.questions ?? 0} questions from the paper.${flagged} Check them below.`
  }
  return `Audited ${result.audited ?? 0} questions.`
}

/** Toast when a job this page watched running finishes. */
function useJobNotifications(job: IntegrityJob | null | undefined) {
  const watching = useRef(new Set<string>())
  useEffect(() => {
    if (!job) return
    if (isJobActive(job)) {
      watching.current.add(job.id)
      return
    }
    if (!watching.current.delete(job.id)) return
    if (job.status === "DONE") toast.success(jobDoneMessage(job))
    else toast.error(job.error ?? "The AI could not finish.")
  }, [job])
}

function Summary({ overview }: { overview: IntegrityOverview }) {
  const s = overview.summary
  const tiles = [
    { label: "Questions audited", value: `${s.audited} / ${s.questions}`, tone: "" },
    { label: "Match the mapping", value: s.aligned, tone: "text-emerald-600 dark:text-emerald-400" },
    { label: "Different Bloom level", value: s.partial, tone: "text-amber-600 dark:text-amber-400" },
    { label: "Test a different CO", value: s.misaligned, tone: "text-red-600 dark:text-red-400" },
    { label: "AI not sure", value: s.abstained, tone: "text-muted-foreground" },
    { label: "Awaiting your review", value: s.pending_review, tone: "" },
  ]
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
      {tiles.map((tile) => (
        <Card key={tile.label} size="sm">
          <CardContent>
            <p className={cn("text-2xl font-semibold tabular-nums", tile.tone)}>{tile.value}</p>
            <p className="text-xs text-muted-foreground">{tile.label}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
