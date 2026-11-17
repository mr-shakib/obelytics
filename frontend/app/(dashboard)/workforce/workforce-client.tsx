"use client"

import { useState } from "react"
import Link from "next/link"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Briefcase, Loader2, Plus, Sparkles, Trash2 } from "lucide-react"
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
import { type MarketAnalysis, type SkillCoverage, workforceApi } from "@/lib/api/workforce"
import { cn } from "@/lib/utils"

type Curriculum = { id: string; name: string; program_id: string; status: string }

const COVERAGE = {
  covered: { label: "Covered", className: "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-300" },
  partial: { label: "Partly covered", className: "border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-300" },
  gap: { label: "Gap", className: "border-red-200 bg-red-50 text-red-700 dark:border-red-900 dark:bg-red-950/40 dark:text-red-300" },
  unjudged: { label: "Not judged", className: "border-border bg-muted text-muted-foreground" },
} as const

export function WorkforceClient() {
  const qc = useQueryClient()
  const canManage = useHasAnyPermission(["po.update", "curriculum.update"])
  const [curriculumId, setCurriculumId] = useState("")
  const [adding, setAdding] = useState(false)
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
      <PageHeader
        title="Workforce Readiness"
        description="Do the program's outcomes develop what employers ask for? Collect job postings, let AI read their skills, and check them against every course outcome in the curriculum."
      />

      <div className="max-w-md space-y-1.5">
        <Label>Curriculum</Label>
        <Select value={curriculum?.id ?? ""} onValueChange={(v) => v && setCurriculumId(v)}>
          <SelectTrigger>
            <SelectValue placeholder="Choose a curriculum">{curriculum?.name}</SelectValue>
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
              <CardTitle>Job postings ({postings.length})</CardTitle>
              <CardDescription>Shared by the program&apos;s curricula. Paste them from employers or job boards.</CardDescription>
              {canManage && (
                <CardAction>
                  <Button size="sm" variant="outline" onClick={() => setAdding(true)}>
                    <Plus />
                    Add
                  </Button>
                </CardAction>
              )}
            </CardHeader>
            <CardContent className="space-y-3">
              {postingsLoading ? (
                <div className="h-20 animate-pulse rounded bg-muted" />
              ) : postings.length === 0 ? (
                <p className="text-sm text-muted-foreground">No postings yet.</p>
              ) : (
                postings.map((p) => (
                  <div key={p.id} className="space-y-1.5 rounded-md border p-3">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <p className="text-sm font-medium">{p.title}</p>
                        {p.employer && <p className="text-xs text-muted-foreground">{p.employer}</p>}
                      </div>
                      {canManage && (
                        <Button
                          variant="ghost"
                          size="icon-xs"
                          aria-label={`Remove ${p.title}`}
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
                      <p className="text-xs text-muted-foreground">Skills not read yet — the next analysis reads them.</p>
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
  const maxDemand = Math.max(1, ...(analysis?.program_outcomes.map((p) => p.demand) ?? [1]))
  return (
    <Card>
      <CardHeader>
        <CardTitle>Market demand vs course outcomes</CardTitle>
        <CardDescription>
          AI judges which COs develop each skill; code checks every reference and weights coverage by how many
          postings ask for the skill. Advisory — nothing is changed.
        </CardDescription>
        {canManage && (
          <CardAction>
            <Button size="sm" disabled={running || !canRun} onClick={onRun}>
              {running ? <Loader2 className="animate-spin" /> : <Sparkles />}
              {running ? "Analysing…" : analysis ? "Analyse again" : "Analyse"}
            </Button>
          </CardAction>
        )}
      </CardHeader>
      <CardContent className="space-y-5">
        {!analysis ? (
          <p className="text-sm text-muted-foreground">
            {canRun ? "Run the analysis to compare the postings with the curriculum." : "Add job postings first."}
          </p>
        ) : (
          <>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <Stat label="Demand covered" value={analysis.summary.coverage_pct !== null ? `${analysis.summary.coverage_pct}%` : "—"} strong />
              <Stat label="Covered" value={analysis.summary.covered} />
              <Stat label="Partly covered" value={analysis.summary.partial} />
              <Stat label="Gaps" value={analysis.summary.gap} />
            </div>

            <div className="divide-y rounded-lg border">
              {analysis.skills.map((s) => (
                <div key={s.skill} className="space-y-1.5 p-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-medium">{s.skill}</span>
                      <Badge variant="outline" className={COVERAGE[s.coverage].className}>{COVERAGE[s.coverage].label}</Badge>
                      <span className="text-xs text-muted-foreground">
                        {s.postings} of {analysis.posting_count} postings{s.required === s.postings ? ", required" : ""}
                      </span>
                    </div>
                    {canManage && (s.coverage === "gap" || s.coverage === "partial") && s.suggested_course && (
                      <Button size="xs" variant="outline" onClick={() => onDraft(s)}>
                        <Sparkles />
                        Draft a CO in {s.suggested_course.code}
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
              <p className="text-sm font-medium">Which POs carry the skills employers want</p>
              <p className="text-xs text-muted-foreground">
                Postings asking for skills developed by COs mapped to each PO (through the CO-PO mapping).
              </p>
              <div className="space-y-1">
                {analysis.program_outcomes.map((po) => (
                  <div key={po.code} className="flex items-center gap-2 text-xs" title={po.skills.join(", ") || "No demanded skill"}>
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
              {analysis.posting_count} postings · {analysis.model} · {analysis.prompt_version} ·{" "}
              {new Date(analysis.created_at).toLocaleString()}
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
  const [title, setTitle] = useState("")
  const [employer, setEmployer] = useState("")
  const [text, setText] = useState("")
  const add = useMutation({
    mutationFn: () => workforceApi.addPosting(programId!, { title, employer: employer || undefined, text }),
    onSuccess: (posting) => {
      toast.success(posting.skills ? `Read ${posting.skills.length} skills` : "Saved — skills will be read at the next analysis")
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
          <DialogTitle>Add a job posting</DialogTitle>
          <DialogDescription>Paste the full description. AI reads the skills it asks for.</DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="posting-title">Job title</Label>
              <Input id="posting-title" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Junior Backend Engineer" />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="posting-employer">Employer (optional)</Label>
              <Input id="posting-employer" value={employer} onChange={(e) => setEmployer(e.target.value)} />
            </div>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="posting-text">Description</Label>
            <Textarea id="posting-text" rows={10} value={text} onChange={(e) => setText(e.target.value)} />
          </div>
        </div>
        <DialogFooter showCloseButton>
          <Button disabled={title.trim().length < 2 || text.trim().length < 40 || add.isPending} onClick={() => add.mutate()}>
            {add.isPending && <Loader2 className="animate-spin" />}
            Add and read skills
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
      toast.success(`Added ${code} to ${course!.code}. Map it to POs on the course's Mappings page.`)
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
          <DialogTitle>Close the gap: {skill?.skill}</DialogTitle>
          <DialogDescription>
            {course ? `AI drafts a course outcome for ${course.code} ${course.title}. ` : ""}
            Read and edit it before adding it to the course.
          </DialogDescription>
        </DialogHeader>
        {!draft ? (
          <Button disabled={write.isPending || !course} onClick={() => write.mutate()}>
            {write.isPending ? <Loader2 className="animate-spin" /> : <Sparkles />}
            {write.isPending ? "Writing…" : `Draft a CO for ${course?.code ?? "the course"}`}
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
              Add to {course?.code}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
