"use client"

import { useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { AlertTriangle, Check, Copy, Download, FileText, Loader2, Sparkles, Trash2, Upload, X } from "lucide-react"
import { toast } from "sonner"

import { PageHeader } from "@/components/shared/page-header"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import { useHasAnyPermission } from "@/hooks/use-permission"
import { apiClient } from "@/lib/api/client"
import { type EvidenceDraft, evidenceApi } from "@/lib/api/evidence"
import { useI18n } from "@/lib/i18n"
import { cn } from "@/lib/utils"

type Curriculum = { id: string; name: string; program_id: string }

const SAMPLE_GUIDE_URL = "/samples/sample-accreditation-guide.txt"

const STATUS_CLASS = {
  DRAFT: "border-border bg-muted text-muted-foreground",
  ACCEPTED: "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-300",
  REJECTED: "border-red-200 bg-red-50 text-red-700 dark:border-red-900 dark:bg-red-950/40 dark:text-red-300",
} as const

export function EvidenceClient() {
  const { t } = useI18n()
  const te = t.evidence
  const qc = useQueryClient()
  const canManage = useHasAnyPermission(["accreditation.manage"])
  const [curriculumId, setCurriculumId] = useState("")
  const [criterion, setCriterion] = useState("")
  const [guidance, setGuidance] = useState("")

  const { data: curricula = [] } = useQuery({
    queryKey: ["curricula", "list", "evidence"],
    queryFn: async () => {
      const { data } = await apiClient.GET("/curricula" as never)
      const raw = data as unknown as Curriculum[] | { items?: Curriculum[] }
      return Array.isArray(raw) ? raw : raw?.items ?? []
    },
  })
  const curriculum = curricula.find((c) => c.id === curriculumId) ?? (curricula.length === 1 ? curricula[0] : undefined)
  const draftsKey = ["evidence", "drafts", curriculum?.id]
  const { data: drafts = [] } = useQuery({
    queryKey: draftsKey,
    queryFn: () => evidenceApi.drafts(curriculum!.program_id, curriculum!.id),
    enabled: !!curriculum,
  })

  const draft = useMutation({
    mutationFn: () =>
      evidenceApi.draft(curriculum!.program_id, {
        curriculum_id: curriculum!.id,
        criterion_title: criterion.trim(),
        criterion_guidance: guidance.trim() || undefined,
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: draftsKey }),
  })

  const [latest, ...earlier] = drafts

  return (
    <div className="space-y-6">
      <PageHeader title={te.title} description={te.description} />

      <div className="max-w-md space-y-1.5">
        <Label>{t.workforce.curriculum}</Label>
        <Select value={curriculum?.id ?? ""} onValueChange={(v) => v && setCurriculumId(v)}>
          <SelectTrigger>
            <SelectValue placeholder={t.workforce.chooseCurriculum}>{curriculum?.name}</SelectValue>
          </SelectTrigger>
          <SelectContent>
            {curricula.map((c) => (
              <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(0,2fr)]">
        <DocumentsCard canManage={canManage} />

        <Card>
          <CardHeader>
            <CardTitle>{te.draftTitle}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="space-y-1.5">
              <Label htmlFor="criterion">{te.criterion}</Label>
              <Input
                id="criterion"
                value={criterion}
                placeholder={te.criterionPlaceholder}
                onChange={(e) => setCriterion(e.target.value)}
                maxLength={255}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="guidance">{te.guidance}</Label>
              <Textarea
                id="guidance"
                rows={3}
                value={guidance}
                placeholder={te.guidancePlaceholder}
                onChange={(e) => setGuidance(e.target.value)}
              />
            </div>
            {canManage && (
              <Button disabled={!curriculum || criterion.trim().length < 3 || draft.isPending} onClick={() => draft.mutate()}>
                {draft.isPending ? <Loader2 className="animate-spin" /> : <Sparkles />}
                {draft.isPending ? te.drafting : te.draft}
              </Button>
            )}
            {draft.isError && <p className="text-sm text-destructive">{draft.error.message}</p>}
          </CardContent>
        </Card>
      </div>

      {latest ? (
        <DraftView key={latest.id} draft={latest} canManage={canManage} invalidateKey={draftsKey} />
      ) : (
        curriculum && <p className="text-sm text-muted-foreground">{te.none}</p>
      )}

      {earlier.length > 0 && (
        <div className="space-y-2">
          <p className="text-sm font-medium">{te.earlier}</p>
          {earlier.map((d) => (
            <details key={d.id} className="rounded-md border px-3 py-2">
              <summary className="flex cursor-pointer flex-wrap items-center gap-2 text-sm">
                <span className="font-medium">{d.criterion_title}</span>
                <Badge variant="outline" className={STATUS_CLASS[d.status]}>{te.status[d.status]}</Badge>
                <span className="text-xs text-muted-foreground">{new Date(d.created_at).toLocaleDateString()}</span>
              </summary>
              <div className="mt-3">
                <DraftView draft={d} canManage={canManage} invalidateKey={draftsKey} compact />
              </div>
            </details>
          ))}
        </div>
      )}
    </div>
  )
}

function DocumentsCard({ canManage }: { canManage: boolean }) {
  const { t } = useI18n()
  const te = t.evidence
  const qc = useQueryClient()
  const [title, setTitle] = useState("")
  const [file, setFile] = useState<File | null>(null)
  const { data: documents = [] } = useQuery({ queryKey: ["evidence", "documents"], queryFn: evidenceApi.documents })
  const upload = useMutation({
    mutationFn: () => evidenceApi.addDocument(file!, title.trim() || undefined),
    onSuccess: () => {
      setTitle("")
      setFile(null)
      qc.invalidateQueries({ queryKey: ["evidence", "documents"] })
    },
  })
  const remove = useMutation({
    mutationFn: (id: string) => evidenceApi.deleteDocument(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["evidence", "documents"] }),
  })

  return (
    <Card>
      <CardHeader>
        <CardTitle>{te.documents}</CardTitle>
        <CardDescription>
          {te.documentsDescription}
          <a href={SAMPLE_GUIDE_URL} download className="mt-1.5 flex w-fit items-center gap-1 text-xs font-medium text-primary hover:underline">
            <Download className="size-3" />
            {te.sample}
          </a>
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {documents.length === 0 ? (
          <p className="text-sm text-muted-foreground">{te.noDocuments}</p>
        ) : (
          documents.map((d) => (
            <div key={d.id} className="flex items-start justify-between gap-2 rounded-md border p-2.5">
              <div className="flex min-w-0 items-start gap-2">
                <FileText className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium">{d.title}</p>
                  <p className="text-xs text-muted-foreground">{d.filename} · {te.passages(d.passage_count)}</p>
                </div>
              </div>
              {canManage && (
                <Button variant="ghost" size="icon-xs" aria-label={te.remove(d.title)} disabled={remove.isPending}
                        onClick={() => remove.mutate(d.id)}>
                  <Trash2 />
                </Button>
              )}
            </div>
          ))
        )}
        {canManage && (
          <div className="space-y-2 border-t pt-3">
            <Input value={title} placeholder={te.docTitle} onChange={(e) => setTitle(e.target.value)} maxLength={255} />
            <div className="flex gap-2">
              <Input type="file" accept=".pdf,.docx,.txt" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
              <Button size="sm" disabled={!file || upload.isPending} onClick={() => upload.mutate()}>
                {upload.isPending ? <Loader2 className="animate-spin" /> : <Upload />}
                {upload.isPending ? te.uploading : te.upload}
              </Button>
            </div>
            {upload.isError && <p className="text-xs text-destructive">{upload.error.message}</p>}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function DraftView({
  draft,
  canManage,
  invalidateKey,
  compact = false,
}: {
  draft: EvidenceDraft
  canManage: boolean
  invalidateKey: readonly unknown[]
  compact?: boolean
}) {
  const { t, dateTime } = useI18n()
  const te = t.evidence
  const qc = useQueryClient()
  const [open, setOpen] = useState<string | null>(null)
  const plain = draft.sentences.map((s) => s.text).join(" ")
  const [text, setText] = useState(draft.edited_text ?? plain)
  const supported = draft.sentences.filter((s) => s.status === "supported").length

  const decide = useMutation({
    mutationFn: (decision: "ACCEPTED" | "REJECTED") =>
      evidenceApi.decide(draft.id, decision, decision === "ACCEPTED" && text !== plain ? text : undefined),
    onSuccess: () => qc.invalidateQueries({ queryKey: invalidateKey }),
  })

  const source = open ? draft.sources[open] : null

  return (
    <Card className={cn(compact && "border-0 shadow-none")}>
      {!compact && (
        <CardHeader>
          <div className="flex flex-wrap items-center gap-2">
            <CardTitle>{draft.criterion_title}</CardTitle>
            <Badge variant="outline" className={STATUS_CLASS[draft.status]}>{te.status[draft.status]}</Badge>
          </div>
          <CardDescription>{te.checked(supported, draft.sentences.length)}</CardDescription>
        </CardHeader>
      )}
      <CardContent className={cn("space-y-4", compact && "p-0")}>
        <div className="space-y-2 leading-relaxed">
          {draft.sentences.map((s, i) => (
            <div
              key={i}
              className={cn(
                "rounded-md px-2.5 py-1.5 text-sm",
                s.status === "check" && "bg-amber-50 ring-1 ring-amber-200 dark:bg-amber-950/30 dark:ring-amber-900",
                s.gap && s.status === "supported" && "bg-muted/50 italic text-muted-foreground",
              )}
            >
              <span>{s.text}</span>
              {s.gap && <Badge variant="outline" className="ml-1.5 align-middle text-[10px] not-italic">{te.gap}</Badge>}
              {s.cites.map((id) => (
                <button
                  key={id}
                  type="button"
                  onClick={() => setOpen(open === id ? null : id)}
                  title={draft.sources[id]?.label}
                  className={cn(
                    "ml-1 rounded px-1 align-baseline font-mono text-[11px]",
                    id.startsWith("M")
                      ? "bg-sky-100 text-sky-800 dark:bg-sky-900/40 dark:text-sky-200"
                      : "bg-violet-100 text-violet-800 dark:bg-violet-900/40 dark:text-violet-200",
                    open === id && "ring-2 ring-primary",
                  )}
                >
                  {id}
                </button>
              ))}
              {s.status === "check" && (
                <p className="mt-1 flex items-start gap-1 text-xs not-italic text-amber-800 dark:text-amber-300">
                  <AlertTriangle className="mt-0.5 size-3 shrink-0" />
                  {te.toCheck}: {s.issues.join("; ")}
                </p>
              )}
            </div>
          ))}
        </div>

        {source && open && (
          <div className="rounded-md border bg-muted/30 p-3 text-sm">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              {open} · {open.startsWith("M") ? te.manual : te.record}
            </p>
            <p className="mt-1 font-medium">{source.label}</p>
            <p className="mt-1 text-muted-foreground">{source.text}</p>
          </div>
        )}

        {draft.missing.length > 0 && (
          <div className="space-y-1">
            <p className="text-sm font-medium">{te.missing}</p>
            <ul className="list-disc space-y-0.5 pl-5 text-sm text-muted-foreground">
              {draft.missing.map((m, i) => <li key={i}>{m}</li>)}
            </ul>
          </div>
        )}

        {canManage && draft.status === "DRAFT" && (
          <div className="space-y-2 border-t pt-3">
            <Label htmlFor={`final-${draft.id}`}>{te.editLabel}</Label>
            <Textarea id={`final-${draft.id}`} rows={6} value={text} onChange={(e) => setText(e.target.value)} />
            <div className="flex flex-wrap gap-2">
              <Button size="sm" disabled={decide.isPending} onClick={() => decide.mutate("ACCEPTED")}>
                <Check />
                {te.accept}
              </Button>
              <Button size="sm" variant="outline" disabled={decide.isPending} onClick={() => decide.mutate("REJECTED")}>
                <X />
                {te.reject}
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => {
                  navigator.clipboard?.writeText(text)
                  toast.success(te.copied)
                }}
              >
                <Copy />
                {te.copy}
              </Button>
            </div>
          </div>
        )}
        {draft.status === "ACCEPTED" && draft.edited_text && (
          <p className="whitespace-pre-wrap rounded-md border p-3 text-sm">{draft.edited_text}</p>
        )}
        <p className="text-xs text-muted-foreground">
          {draft.model} · {draft.prompt_version} · {dateTime(draft.created_at)} · {Object.keys(draft.sources).length} {te.sources.toLowerCase()}
        </p>
      </CardContent>
    </Card>
  )
}
