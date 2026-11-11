"use client"

import { useRef, useState } from "react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { AlertTriangle, Check, FileUp, Loader2, Save } from "lucide-react"
import { toast } from "sonner"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Textarea } from "@/components/ui/textarea"
import { queryKeys } from "@/lib/query-keys"

import {
  ACCEPTED_PAPER_FILES,
  type ExamType,
  type ExtractedQuestion,
  type IntegrityJob,
  type IntegrityOverview,
  integrityApi,
  isJobActive,
  type QuestionPaper,
} from "./api"
const SKIP = "skip"

type PanelProps = {
  overview: IntegrityOverview
  sectionId: string
  examType: ExamType
  canManage: boolean
}

const METHOD_LABEL: Record<NonNullable<QuestionPaper["extraction_method"]>, string> = {
  VISION: "read from page images",
  TEXT_LAYER: "read from the PDF's own text",
  DOCX: "read from the Word document",
  MIXED: "read from the PDF's text and page images",
}

export function JobProgress({ job, title, unit }: { job: IntegrityJob; title: string; unit: string }) {
  const total = job.progress_total ?? 0
  const done = Math.min(job.progress_done, total)
  const percent = total > 0 ? Math.round((done / total) * 100) : 0
  return (
    <Alert>
      <Loader2 className="animate-spin" />
      <AlertTitle>{title}</AlertTitle>
      <AlertDescription className="w-full space-y-2">
        <p>
          {job.status === "QUEUED"
            ? "Waiting to start…"
            : total > 0
              ? `${unit} ${Math.min(done + 1, total)} of ${total}`
              : "Working…"}
          {" · You can leave this page; it carries on in the background."}
        </p>
        <div
          className="h-1.5 w-full overflow-hidden rounded-full bg-muted"
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={percent}
        >
          <div className="h-full rounded-full bg-primary transition-[width] duration-500" style={{ width: `${percent}%` }} />
        </div>
      </AlertDescription>
    </Alert>
  )
}

export function PaperPanel({ overview, sectionId, examType, canManage }: PanelProps) {
  const qc = useQueryClient()
  const fileInput = useRef<HTMLInputElement>(null)
  const paper = overview.paper
  const job = overview.job
  const busy = isJobActive(job)
  const reading = busy && job?.kind === "READ_PAPER"
  const readFailed =
    paper?.extraction_status === "FAILED" ||
    (job?.kind === "READ_PAPER" && job.status === "FAILED" && paper?.extraction_status !== "EXTRACTED")

  const upload = useMutation({
    mutationFn: (file: File) => integrityApi.uploadPaper(sectionId, examType, file),
    onSuccess: (data) => qc.setQueryData(queryKeys.integrity.overview(sectionId, examType), data),
  })

  return (
    <Card>
      <CardHeader>
        <CardTitle>1. Question paper</CardTitle>
        <CardDescription>
          Upload the paper as a PDF, a Word document or a photo. The AI reads the questions, and you check
          the wording before it is saved. The file itself is not stored.
        </CardDescription>
        {canManage && (
          <CardAction>
            <input
              ref={fileInput}
              type="file"
              accept={ACCEPTED_PAPER_FILES}
              className="hidden"
              onChange={(event) => {
                const file = event.target.files?.[0]
                event.target.value = ""
                if (file) upload.mutate(file)
              }}
            />
            <Button
              size="sm"
              variant={paper ? "outline" : "default"}
              disabled={upload.isPending || busy}
              onClick={() => fileInput.current?.click()}
            >
              {upload.isPending ? <Loader2 className="animate-spin" /> : <FileUp />}
              {paper ? "Replace paper" : "Upload paper"}
            </Button>
          </CardAction>
        )}
      </CardHeader>
      <CardContent className="space-y-4">
        {upload.isPending && (
          <Alert>
            <Loader2 className="animate-spin" />
            <AlertTitle>Uploading…</AlertTitle>
          </Alert>
        )}
        {reading && job && (
          <JobProgress
            job={job}
            title="Reading the paper…"
            unit={paper?.extraction_method === "DOCX" ? "Part" : "Page"}
          />
        )}
        {upload.isError && (
          <Alert variant="destructive">
            <AlertTitle>The paper could not be uploaded</AlertTitle>
            <AlertDescription>{upload.error.message}</AlertDescription>
          </Alert>
        )}
        {!paper ? (
          !upload.isPending && !reading && (
            <p className="text-sm text-muted-foreground">No paper has been uploaded for this exam yet.</p>
          )
        ) : reading ? null : readFailed ? (
          <Alert variant="destructive">
            <AlertTitle>The last upload could not be read</AlertTitle>
            <AlertDescription>{paper.extraction_error ?? job?.error}</AlertDescription>
          </Alert>
        ) : paper.extraction_status === "EXTRACTED" ? (
          <>
            <p className="text-xs text-muted-foreground">
              {paper.original_filename} ·{" "}
              {paper.page_count == null
                ? "Word document"
                : `${paper.page_count} page${paper.page_count === 1 ? "" : "s"}`}
              {paper.extraction_method && ` · ${METHOD_LABEL[paper.extraction_method]}`} · by{" "}
              {paper.extraction_model} ({paper.extraction_prompt_version}) ·{" "}
              {new Date(paper.updated_at).toLocaleString()}
            </p>
            <ExtractedReview
              key={paper.updated_at}
              overview={overview}
              sectionId={sectionId}
              examType={examType}
              canManage={canManage}
            />
          </>
        ) : null}
      </CardContent>
    </Card>
  )
}

type Row = ExtractedQuestion & { target: string }

function ExtractedReview({ overview, sectionId, examType, canManage }: PanelProps) {
  const qc = useQueryClient()
  const [rows, setRows] = useState<Row[]>(() =>
    (overview.paper?.questions ?? []).map((q) => ({ ...q, target: q.matched_question_id ?? SKIP })),
  )
  const marksheet = overview.questions
  const labelOf = new Map(marksheet.map((q) => [q.question_id, q.label]))
  const savedText = new Map(marksheet.map((q) => [q.question_id, q.question_text]))

  const targets = rows.filter((row) => row.target !== SKIP).map((row) => row.target)
  const duplicate = targets.length !== new Set(targets).size
  const unmatched = rows.length - targets.length

  const save = useMutation({
    mutationFn: () =>
      integrityApi.saveQuestionTexts(
        sectionId,
        examType,
        rows
          .filter((row) => row.target !== SKIP)
          .map((row) => ({ question_id: row.target, question_text: row.text.trim() || null })),
      ),
    onSuccess: (data) => {
      qc.setQueryData(queryKeys.integrity.overview(sectionId, examType), data)
      toast.success("Question wording saved. You can run the audit now.")
    },
  })

  const update = (index: number, change: Partial<Row>) =>
    setRows((current) => current.map((row, i) => (i === index ? { ...row, ...change } : row)))

  if (rows.length === 0) {
    return <p className="text-sm text-muted-foreground">The AI found no questions on this paper.</p>
  }

  return (
    <div className="space-y-3">
      {marksheet.length === 0 && (
        <Alert>
          <AlertDescription>
            This exam has no marksheet questions yet. Set them up in the course assessment first, then
            match the paper&apos;s questions to them here.
          </AlertDescription>
        </Alert>
      )}
      <div className="rounded-lg border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-24">On paper</TableHead>
              <TableHead>Question as read by the AI</TableHead>
              <TableHead className="w-44">Marksheet question</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((row, index) => {
              const saved = row.target !== SKIP && savedText.get(row.target) === row.text.trim()
              return (
                <TableRow key={`${row.label}-${index}`} className="align-top">
                  <TableCell className="whitespace-normal">
                    <p className="font-medium">{row.label}</p>
                    <p className="text-xs text-muted-foreground">
                      {row.marks != null ? `${row.marks} marks` : "marks not read"}
                      {row.co ? ` · ${row.co}` : ""}
                    </p>
                  </TableCell>
                  <TableCell className="space-y-1.5 whitespace-normal">
                    {row.context && (
                      <p className="line-clamp-2 text-xs text-muted-foreground">Scenario: {row.context}</p>
                    )}
                    <Textarea
                      value={row.text}
                      disabled={!canManage}
                      rows={Math.min(6, Math.max(2, Math.ceil(row.text.length / 90)))}
                      onChange={(event) => update(index, { text: event.target.value })}
                    />
                    {row.figure && <p className="text-xs text-muted-foreground">Figure: {row.figure}</p>}
                    {row.warning && (
                      <p className="flex items-start gap-1 text-xs text-amber-700 dark:text-amber-400">
                        <AlertTriangle className="mt-0.5 size-3 shrink-0" />
                        {row.warning}
                      </p>
                    )}
                  </TableCell>
                  <TableCell className="space-y-1.5 whitespace-normal">
                    <Select
                      value={row.target}
                      disabled={!canManage}
                      onValueChange={(value) => { if (value != null) update(index, { target: value as string }) }}
                    >
                      <SelectTrigger className="w-full">
                        <SelectValue>{row.target === SKIP ? "Don't use" : labelOf.get(row.target)}</SelectValue>
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value={SKIP}>Don&apos;t use</SelectItem>
                        {marksheet.map((q) => (
                          <SelectItem key={q.question_id} value={q.question_id}>
                            {q.label} ({q.max_marks} marks)
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {saved && (
                      <p className="flex items-center gap-1 text-xs text-emerald-600 dark:text-emerald-400">
                        <Check className="size-3" /> Saved
                      </p>
                    )}
                  </TableCell>
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
      </div>
      {canManage && (
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-xs text-muted-foreground">
            Check each question against the paper and fix anything the AI misread.
            {unmatched > 0 && ` ${unmatched} not matched to the marksheet.`}
            {duplicate && (
              <span className="text-destructive"> Two paper questions point at the same marksheet question.</span>
            )}
          </p>
          <Button size="sm" disabled={save.isPending || duplicate || targets.length === 0} onClick={() => save.mutate()}>
            {save.isPending ? <Loader2 className="animate-spin" /> : <Save />}
            Save wording to marksheet
          </Button>
        </div>
      )}
    </div>
  )
}
