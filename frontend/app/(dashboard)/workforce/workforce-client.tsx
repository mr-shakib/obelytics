"use client"

import { useState } from "react"
import Link from "next/link"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Briefcase, ExternalLink, FileUp, Link2, Loader2, Plus, Sparkles, Trash2 } from "lucide-react"
import { toast } from "sonner"

import { PageHeader } from "@/components/shared/page-header"
import { WarningList } from "@/components/courses/refine-statement"
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
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import { useHasAnyPermission } from "@/hooks/use-permission"
import { apiClient } from "@/lib/api/client"
import { authoringApi, type DraftResponse } from "@/lib/api/authoring"
import { type ImportResult, type MarketAnalysis, type SkillCoverage, workforceApi } from "@/lib/api/workforce"
import { useI18n } from "@/lib/i18n"
import { cn } from "@/lib/utils"

type Curriculum = { id: string; name: string; program_id: string; status: string }

const COVERAGE_CLASS = {
  covered: "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-300",
  partial: "border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-300",
  gap: "border-red-200 bg-red-50 text-red-700 dark:border-red-900 dark:bg-red-950/40 dark:text-red-300",
  unjudged: "border-border bg-muted text-muted-foreground",
} as const

function isLink(source: string | null): source is string {
  return !!source && /^https?:\/\//i.test(source)
}

export function WorkforceClient() {
  const { t } = useI18n()
  const tw = t.workforce
  const qc = useQueryClient()
  const canManage = useHasAnyPermission(["po.update", "curriculum.update"])
  const [curriculumId, setCurriculumId] = useState("")
  const [adding, setAdding] = useState(false)
  const [importing, setImporting] = useState(false)
  const [draftFor, setDraftFor] = useState<SkillCoverage | null>(null)

  const { data: curricula = [] } = useQuery({
    queryKey: ["curricula", "list", "workforce"],
    queryFn: async () => {
      const { data } = await apiClient.GET("/curricula" as never)
      const raw = data as unknown as Curriculum[] | { items?: Curriculum[] }
      return Array.isArray(raw) ? raw : raw?.items ?? []
    },
  })
  const curriculum = curricula.find((c) => c.id === curriculumId) ?? (curricula.length === 1 ? curricula[0] : undefined)
  const programId = curriculum?.program_id

  const postingsKey = ["workforce", "postings", programId]
  const analysisKey = ["workforce", "analysis", programId, curriculum?.id]
  const { data: postings = [], isLoading: postingsLoading } = useQuery({
    queryKey: postingsKey,
    queryFn: () => workforceApi.postings(programId!),
    enabled: !!programId,
  })
  const { data: analysis } = useQuery({
    queryKey: analysisKey,
    queryFn: () => workforceApi.latest(programId!, curriculum!.id),
    enabled: !!programId && !!curriculum,
  })

  const analyze = useMutation({
    mutationFn: () => workforceApi.analyze(programId!, curriculum!.id),
    onSuccess: (data) => {
      qc.setQueryData(analysisKey, data)
      qc.invalidateQueries({ queryKey: postingsKey })
    },
  })
  const remove = useMutation({
    mutationFn: (id: string) => workforceApi.deletePosting(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: postingsKey }),
  })

  return (
    <div className="space-y-6">
      <PageHeader title={tw.title} description={tw.description} />

      <div className="max-w-md space-y-1.5">
        <Label>{tw.curriculum}</Label>
        <Select value={curriculum?.id ?? ""} onValueChange={(v) => v && setCurriculumId(v)}>
          <SelectTrigger>
            <SelectValue placeholder={tw.chooseCurriculum}>{curriculum?.name}</SelectValue>
          </SelectTrigger>
          <SelectContent>
            {curricula.map((c) => (
              <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {programId && curriculum && (
        <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(0,2fr)]">
          <Card>
            <CardHeader>
              <CardTitle>{tw.postings(postings.length)}</CardTitle>
              <CardDescription>{tw.postingsDescription}</CardDescription>
              {canManage && (
                <CardAction className="flex gap-1.5">
                  <Button size="sm" variant="outline" onClick={() => setImporting(true)}>
                    <FileUp />
                    {tw.import}
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => setAdding(true)}>
                    <Plus />
                    {tw.add}
                  </Button>
                </CardAction>
              )}
            </CardHeader>
            <CardContent className="space-y-3">
              {postingsLoading ? (
                <div className="h-20 animate-pulse rounded bg-muted" />
              ) : postings.length === 0 ? (
                <p className="text-sm text-muted-foreground">{tw.noPostings}</p>
              ) : (
                postings.map((p) => (
                  <div key={p.id} className="space-y-1.5 rounded-md border p-3">
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <p className="text-sm font-medium">{p.title}</p>
                        {p.employer && <p className="text-xs text-muted-foreground">{p.employer}</p>}
                        {isLink(p.source) && (
                          <a
                            href={p.source}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex max-w-full items-center gap-1 truncate text-xs text-primary hover:underline"
                          >
                            <ExternalLink className="size-3 shrink-0" />
                            <span className="truncate">{new URL(p.source).hostname}</span>
                          </a>
                        )}
                      </div>
                      {canManage && (
                        <Button
                          variant="ghost"
                          size="icon-xs"
                          aria-label={tw.remove(p.title)}
                          disabled={remove.isPending}
                          onClick={() => remove.mutate(p.id)}
                        >
                          <Trash2 />
                        </Button>
                      )}
                    </div>
                    {p.skills ? (
                      <div className="flex flex-wrap gap-1">
                        {p.skills.map((s) => (
                          <Badge key={s.name} variant={s.required ? "secondary" : "outline"} className="text-xs font-normal">
                            {s.name}
                          </Badge>
                        ))}
                      </div>
                    ) : (
                      <p className="text-xs text-muted-foreground">{tw.skillsNotRead}</p>
                    )}
                  </div>
                ))
              )}
            </CardContent>
          </Card>

          <AnalysisCard
            analysis={analysis ?? null}
            canManage={canManage}
            running={analyze.isPending}
            canRun={postings.length > 0}
            onRun={() => analyze.mutate()}
            onDraft={setDraftFor}
          />
        </div>
      )}

      <AddPostingDialog
        open={adding}
        programId={programId}
        onClose={() => setAdding(false)}
        onAdded={() => qc.invalidateQueries({ queryKey: postingsKey })}
      />
      <ImportDialog
        open={importing}
        programId={programId}
        onClose={() => setImporting(false)}
        onImported={() => qc.invalidateQueries({ queryKey: postingsKey })}
      />
      <DraftForGapDialog
        skill={draftFor}
        curriculumId={curriculum?.id}
        onClose={() => setDraftFor(null)}
      />
    </div>
  )
}

function AnalysisCard({
  analysis,
  canManage,
  running,
  canRun,
  onRun,
  onDraft,
}: {
  analysis: MarketAnalysis | null
  canManage: boolean
  running: boolean
  canRun: boolean
  onRun: () => void
  onDraft: (skill: SkillCoverage) => void
}) {
  const { t, dateTime } = useI18n()
  const tw = t.workforce
  const maxDemand = Math.max(1, ...(analysis?.program_outcomes.map((p) => p.demand) ?? [1]))
  return (
    <Card>
      <CardHeader>
        <CardTitle>{tw.analysisTitle}</CardTitle>
        <CardDescription>{tw.analysisDescription}</CardDescription>
        {canManage && (
          <CardAction>
            <Button size="sm" disabled={running || !canRun} onClick={onRun}>
              {running ? <Loader2 className="animate-spin" /> : <Sparkles />}
              {running ? tw.analysing : analysis ? tw.analyseAgain : tw.analyse}
            </Button>
          </CardAction>
        )}
      </CardHeader>
      <CardContent className="space-y-5">
        {!analysis ? (
          <p className="text-sm text-muted-foreground">{canRun ? tw.runFirst : tw.addFirst}</p>
        ) : (
          <>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <Stat label={tw.demandCovered} value={analysis.summary.coverage_pct !== null ? `${analysis.summary.coverage_pct}%` : "—"} strong />
              <Stat label={tw.covered} value={analysis.summary.covered} />
              <Stat label={tw.partlyCovered} value={analysis.summary.partial} />
              <Stat label={tw.gaps} value={analysis.summary.gap} />
            </div>

            <div className="divide-y rounded-lg border">
              {analysis.skills.map((s) => (
                <div key={s.skill} className="space-y-1.5 p-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-medium">{s.skill}</span>
                      <Badge variant="outline" className={COVERAGE_CLASS[s.coverage]}>{tw.coverage[s.coverage]}</Badge>
                      <span className="text-xs text-muted-foreground">
                        {tw.ofPostings(s.postings, analysis.posting_count, s.required === s.postings)}
                      </span>
                      {!!s.aliases?.length && (
                        <span className="text-xs text-muted-foreground">· {tw.alsoCalled(s.aliases.join(", "))}</span>
                      )}
                    </div>
                    {canManage && (s.coverage === "gap" || s.coverage === "partial") && s.suggested_course && (
                      <Button size="xs" variant="outline" onClick={() => onDraft(s)}>
                        <Sparkles />
                        {tw.draftIn(s.suggested_course.code)}
                      </Button>
                    )}
                  </div>
                  <p className="text-sm text-muted-foreground">{s.reason}</p>
                  {(s.outcomes.length > 0 || s.program_outcomes.length > 0) && (
                    <div className="flex flex-wrap items-center gap-1">
                      {s.outcomes.map((o) => (
                        <Link
                          key={o.ref}
                          href={`/courses/${o.course_id}/mappings`}
                          title={`${o.course_title}: ${o.statement}`}
                          className="rounded-full bg-muted px-2 py-0.5 font-mono text-xs hover:bg-muted/70"
                        >
                          {o.ref}
                        </Link>
                      ))}
                      {s.program_outcomes.map((po) => (
                        <span key={po} className="rounded-full bg-violet-100 px-2 py-0.5 font-mono text-xs text-violet-800 dark:bg-violet-900/40 dark:text-violet-200">
                          {po}
                        </span>
                      ))}
                    </div>
                  )}
                  <WarningList warnings={s.notes} />
                </div>
              ))}
            </div>

            <div className="space-y-2">
              <p className="text-sm font-medium">{tw.whichPos}</p>
              <p className="text-xs text-muted-foreground">{tw.whichPosNote}</p>
              <div className="space-y-1">
                {analysis.program_outcomes.map((po) => (
                  <div key={po.code} className="flex items-center gap-2 text-xs" title={po.skills.join(", ") || tw.noDemandedSkill}>
                    <span className="w-12 font-mono">{po.code}</span>
                    <div className="h-2 flex-1 rounded-full bg-muted">
                      <div className="h-2 rounded-full bg-violet-500" style={{ width: `${(po.demand / maxDemand) * 100}%` }} />
                    </div>
                    <span className="w-10 text-right tabular-nums text-muted-foreground">{po.demand}</span>
                  </div>
                ))}
              </div>
            </div>
            <p className="text-xs text-muted-foreground">
              {tw.footer(analysis.posting_count)} · {analysis.model} · {analysis.prompt_version} · {dateTime(analysis.created_at)}
            </p>
          </>
        )}
      </CardContent>
    </Card>
  )
}

function Stat({ label, value, strong }: { label: string; value: string | number; strong?: boolean }) {
  return (
    <div className={cn("rounded-lg border p-3", strong && "border-violet-200 bg-violet-50/60 dark:border-violet-900/50 dark:bg-violet-950/20")}>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-xl font-semibold tabular-nums">{value}</p>
    </div>
  )
}

function AddPostingDialog({
  open,
  programId,
  onClose,
  onAdded,
}: {
  open: boolean
  programId?: string
  onClose: () => void
  onAdded: () => void
}) {
  const { t } = useI18n()
  const tw = t.workforce
  const [title, setTitle] = useState("")
  const [employer, setEmployer] = useState("")
  const [text, setText] = useState("")
  const add = useMutation({
    mutationFn: () => workforceApi.addPosting(programId!, { title, employer: employer || undefined, text }),
    onSuccess: (posting) => {
      toast.success(posting.skills ? tw.readSkills(posting.skills.length) : tw.savedLater)
      onAdded()
      setTitle("")
      setEmployer("")
      setText("")
      onClose()
    },
  })
  return (
    <Dialog open={open} onOpenChange={(next) => !next && onClose()}>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>{tw.addTitle}</DialogTitle>
          <DialogDescription>{tw.addDescription}</DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="posting-title">{tw.jobTitle}</Label>
              <Input id="posting-title" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Junior Backend Engineer" />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="posting-employer">{tw.employer}</Label>
              <Input id="posting-employer" value={employer} onChange={(e) => setEmployer(e.target.value)} />
            </div>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="posting-text">{tw.descriptionLabel}</Label>
            <Textarea id="posting-text" rows={10} value={text} onChange={(e) => setText(e.target.value)} />
          </div>
        </div>
        <DialogFooter showCloseButton>
          <Button disabled={title.trim().length < 2 || text.trim().length < 40 || add.isPending} onClick={() => add.mutate()}>
            {add.isPending && <Loader2 className="animate-spin" />}
            {tw.addAndRead}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

/** Real postings in bulk: links to public job pages, or a CSV export. Skills are read at the next analysis. */
function ImportDialog({
  open,
  programId,
  onClose,
  onImported,
}: {
  open: boolean
  programId?: string
  onClose: () => void
  onImported: () => void
}) {
  const { t } = useI18n()
  const tw = t.workforce
  const [mode, setMode] = useState<"links" | "csv">("links")
  const [links, setLinks] = useState("")
  const [file, setFile] = useState<File | null>(null)
  const [result, setResult] = useState<ImportResult | null>(null)

  const urls = links.split(/\s+/).map((u) => u.trim()).filter((u) => /^https?:\/\//i.test(u))
  const run = useMutation({
    mutationFn: () => (mode === "links" ? workforceApi.importUrls(programId!, urls) : workforceApi.importCsv(programId!, file!)),
    onSuccess: (data) => {
      setResult(data)
      if (data.added.length) {
        toast.success(tw.imported(data.added.length, data.errors.length))
        onImported()
      }
      if (!data.errors.length) close()
    },
  })

  function close() {
    setLinks("")
    setFile(null)
    setResult(null)
    onClose()
  }

  return (
    <Dialog open={open} onOpenChange={(next) => !next && close()}>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>{tw.importTitle}</DialogTitle>
          <DialogDescription>{tw.importDescription}</DialogDescription>
        </DialogHeader>
        <div className="inline-flex w-fit rounded-lg border p-0.5">
          <Button size="sm" variant={mode === "links" ? "default" : "ghost"} onClick={() => setMode("links")}>
            <Link2 />
            {tw.fromLinks}
          </Button>
          <Button size="sm" variant={mode === "csv" ? "default" : "ghost"} onClick={() => setMode("csv")}>
            <FileUp />
            {tw.fromCsv}
          </Button>
        </div>
        {mode === "links" ? (
          <div className="space-y-1.5">
            <Label htmlFor="import-links">{tw.linksLabel}</Label>
            <Textarea
              id="import-links"
              rows={6}
              value={links}
              placeholder={tw.linksPlaceholder}
              onChange={(e) => setLinks(e.target.value)}
              className="font-mono text-xs"
            />
          </div>
        ) : (
          <div className="space-y-1.5">
            <Label htmlFor="import-csv">{tw.csvLabel}</Label>
            <Input id="import-csv" type="file" accept=".csv,text/csv" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
          </div>
        )}
        {run.isError && <p className="text-sm text-destructive">{run.error.message}</p>}
        {result && result.errors.length > 0 && (
          <div className="space-y-1 rounded-md border border-amber-200 bg-amber-50/60 p-2 text-xs dark:border-amber-900 dark:bg-amber-950/20">
            <p className="font-medium">{tw.importErrors}</p>
            <ul className="space-y-0.5">
              {result.errors.map((e, i) => (
                <li key={i} className="break-all">
                  <span className="text-muted-foreground">{e.source}</span> — {e.error}
                </li>
              ))}
            </ul>
          </div>
        )}
        <DialogFooter showCloseButton>
          <Button
            disabled={run.isPending || (mode === "links" ? urls.length === 0 : !file)}
            onClick={() => run.mutate()}
          >
            {run.isPending && <Loader2 className="animate-spin" />}
            {run.isPending ? tw.importing : tw.importButton}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

/** Close a gap: AI drafts one CO for the suggested course; the teacher adds it or not. */
function DraftForGapDialog({
  skill,
  curriculumId,
  onClose,
}: {
  skill: SkillCoverage | null
  curriculumId?: string
  onClose: () => void
}) {
  const { t } = useI18n()
  const tw = t.workforce
  const qc = useQueryClient()
  const [draft, setDraft] = useState<DraftResponse | null>(null)
  const [statement, setStatement] = useState("")
  const course = skill?.suggested_course

  const write = useMutation({
    mutationFn: () =>
      authoringApi.draft({
        curriculum_id: curriculumId!,
        course_id: course!.id,
        count: 1,
        instruction: `Cover the job-market skill "${skill!.skill}". ${skill!.reason}`,
      }),
    onSuccess: (data) => {
      setDraft(data)
      setStatement(data.outcomes[0]?.statement ?? "")
    },
  })

  const add = useMutation({
    mutationFn: async () => {
      const { data } = await apiClient.GET(
        `/course-outcomes?curriculum_id=${curriculumId}&course_id=${course!.id}` as never,
      )
      const codes = ((data as unknown) as { code: string }[] ?? []).map((c) => Number(/^CO(\d+)$/i.exec(c.code)?.[1] ?? 0))
      const code = `CO${Math.max(0, ...codes) + 1}`
      await apiClient.POST("/course-outcomes" as never, {
        body: {
          curriculum_id: curriculumId,
          course_id: course!.id,
          code,
          statement: statement.trim(),
          bloom_level_ids: draft!.outcomes[0]?.bloom_levels.map((b) => b.id) ?? [],
        },
      } as never)
      return code
    },
    onSuccess: (code) => {
      authoringApi.decide(draft!.suggestion_id, statement !== draft!.outcomes[0]?.statement ? "EDITED" : "ACCEPTED")
      toast.success(tw.addedCo(code, course!.code))
      qc.invalidateQueries({ queryKey: ["course-outcomes"] })
      close()
    },
  })

  function close() {
    if (draft && !add.isSuccess) authoringApi.decide(draft.suggestion_id, "REJECTED")
    setDraft(null)
    setStatement("")
    onClose()
  }

  const outcome = draft?.outcomes[0]
  return (
    <Dialog open={!!skill} onOpenChange={(next) => !next && close()}>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>{tw.gapTitle(skill?.skill ?? "")}</DialogTitle>
          <DialogDescription>
            {course ? tw.gapDescription(`${course.code} ${course.title}`) : ""}
            {tw.gapEdit}
          </DialogDescription>
        </DialogHeader>
        {!draft ? (
          <Button disabled={write.isPending || !course} onClick={() => write.mutate()}>
            {write.isPending ? <Loader2 className="animate-spin" /> : <Sparkles />}
            {write.isPending ? tw.writing : tw.draftFor(course?.code ?? tw.theCourse)}
          </Button>
        ) : (
          <div className="space-y-2">
            <Textarea rows={3} value={statement} onChange={(e) => setStatement(e.target.value)} />
            <div className="flex flex-wrap gap-1">
              {outcome?.bloom_levels.map((b) => (
                <Badge key={b.id} variant="secondary" className="font-mono text-xs">{b.code} {b.name}</Badge>
              ))}
            </div>
            {outcome?.rationale && <p className="text-xs text-muted-foreground">{outcome.rationale}</p>}
            <WarningList warnings={statement === outcome?.statement ? outcome.warnings : []} />
          </div>
        )}
        <DialogFooter showCloseButton>
          {draft && (
            <Button disabled={statement.trim().length < 10 || add.isPending} onClick={() => add.mutate()}>
              {add.isPending && <Loader2 className="animate-spin" />}
              <Briefcase />
              {tw.addTo(course?.code ?? "")}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
