"use client"

import { useState } from "react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { FileUp, Info, Loader2, Sparkles } from "lucide-react"
import { toast } from "sonner"
import { WarningList } from "@/components/courses/refine-statement"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Textarea } from "@/components/ui/textarea"
import { useHasAnyPermission } from "@/hooks/use-permission"
import { authoringApi, type OutlineOutcome, type OutlinePreview } from "@/lib/api/authoring"
import { cn } from "@/lib/utils"

type Parts = { description: boolean; objectives: boolean; outcomes: boolean; topics: boolean }

/**
 * Import a course outline (Word or text PDF): AI reads it into the course's description,
 * objectives, COs and weekly topics. The teacher checks and edits the preview first;
 * existing COs are never overwritten, and the file itself is not kept.
 */
export function ImportOutlineDialog({ curriculumId, courseId }: { curriculumId?: string; courseId: string }) {
  const qc = useQueryClient()
  const allowed = useHasAnyPermission(["co.create", "course.update"])
  const [open, setOpen] = useState(false)
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<OutlinePreview | null>(null)
  const [parts, setParts] = useState<Parts>({ description: true, objectives: true, outcomes: true, topics: true })
  const [description, setDescription] = useState("")
  const [outcomes, setOutcomes] = useState<(OutlineOutcome & { selected: boolean })[]>([])

  const read = useMutation({
    mutationFn: () => authoringApi.readOutline(curriculumId!, courseId, file!),
    onSuccess: (data) => {
      setPreview(data)
      setDescription(data.description ?? "")
      setOutcomes(data.outcomes.map((o) => ({ ...o, selected: !o.exists })))
      setParts({
        description: !!data.description,
        objectives: data.objectives.length > 0,
        outcomes: data.outcomes.some((o) => !o.exists),
        topics: data.topics.length > 0,
      })
    },
  })

  const apply = useMutation({
    mutationFn: () =>
      authoringApi.applyOutline(preview!.suggestion_id, {
        description: parts.description ? description : undefined,
        objectives: parts.objectives ? preview!.objectives : undefined,
        outcomes: parts.outcomes
          ? outcomes
              .filter((o) => o.selected && !o.exists)
              .map((o) => ({ code: o.code, statement: o.statement, bloom_level_ids: o.bloom_levels.map((b) => b.id) }))
          : undefined,
        topics: parts.topics ? preview!.topics : undefined,
      }),
    onSuccess: (result) => {
      const done = [
        result.description && "description",
        result.objectives > 0 && `${result.objectives} objectives`,
        result.outcomes_added.length > 0 && `${result.outcomes_added.join(", ")}`,
        result.lesson_items > 0 && `${result.lesson_items}-week lesson plan`,
        result.syllabus && !result.lesson_items && "course content",
      ].filter(Boolean)
      toast.success(done.length ? `Imported ${done.join(", ")}` : "Nothing was imported")
      qc.invalidateQueries()
      close()
    },
  })

  function close() {
    if (preview && !apply.isSuccess) authoringApi.decide(preview.suggestion_id, "REJECTED")
    setOpen(false)
    setFile(null)
    setPreview(null)
  }

  if (!allowed) return null
  const chosenOutcomes = outcomes.filter((o) => o.selected && !o.exists).length
  const anything = parts.description || parts.objectives || (parts.outcomes && chosenOutcomes > 0) || parts.topics

  return (
    <>
      <Button
        variant="outline"
        size="sm"
        disabled={!curriculumId}
        title={curriculumId ? "Read a course outline document into this course with AI" : "Course is not part of any curriculum yet"}
        onClick={() => setOpen(true)}
      >
        <FileUp />
        Import outline
      </Button>

      <Dialog open={open} onOpenChange={(next) => (next ? setOpen(true) : close())}>
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-3xl">
          <DialogHeader>
            <DialogTitle>Import a course outline with AI</DialogTitle>
            <DialogDescription>
              Upload the outline as Word or a text PDF. AI reads the description, objectives, course outcomes and
              weekly topics; you check them before anything is saved. Existing COs are never changed, and the file
              is not kept.
            </DialogDescription>
          </DialogHeader>

          {!preview && (
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
              <input
                type="file"
                accept=".docx,.pdf,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                onChange={(event) => setFile(event.target.files?.[0] ?? null)}
                className="text-sm file:mr-3 file:rounded-md file:border file:bg-background file:px-3 file:py-1.5 file:text-sm"
              />
              <Button disabled={!file || read.isPending} onClick={() => read.mutate()}>
                {read.isPending ? <Loader2 className="animate-spin" /> : <Sparkles />}
                {read.isPending ? "Reading…" : "Read with AI"}
              </Button>
            </div>
          )}

          {preview && (
            <div className="space-y-5">
              {preview.warnings.length > 0 && <WarningList warnings={preview.warnings} />}

              <Section
                title="Description"
                checked={parts.description}
                disabled={!preview.description}
                note={preview.current.has_description ? "Replaces the current description." : undefined}
                onCheck={(v) => setParts((p) => ({ ...p, description: v }))}
              >
                {preview.description ? (
                  <Textarea rows={3} value={description} onChange={(e) => setDescription(e.target.value)} />
                ) : (
                  <Empty>No description found.</Empty>
                )}
              </Section>

              <Section
                title={`Objectives (${preview.objectives.length})`}
                checked={parts.objectives}
                disabled={preview.objectives.length === 0}
                note={preview.current.objectives > 0 ? `Replaces the ${preview.current.objectives} current objectives.` : undefined}
                onCheck={(v) => setParts((p) => ({ ...p, objectives: v }))}
              >
                {preview.objectives.length ? (
                  <ol className="list-decimal space-y-0.5 pl-5 text-sm">
                    {preview.objectives.map((o, i) => <li key={i}>{o}</li>)}
                  </ol>
                ) : (
                  <Empty>No objectives found.</Empty>
                )}
              </Section>

              <Section
                title={`Course outcomes (${outcomes.length})`}
                checked={parts.outcomes}
                disabled={!outcomes.some((o) => !o.exists)}
                note="Adds the ticked COs. COs the course already has are left as they are."
                onCheck={(v) => setParts((p) => ({ ...p, outcomes: v }))}
              >
                {outcomes.length ? (
                  <ul className="space-y-3">
                    {outcomes.map((o, i) => (
                      <li key={o.code} className={cn("space-y-1.5 rounded-md border p-2.5", (o.exists || !o.selected) && "opacity-60")}>
                        <div className="flex items-center justify-between gap-2">
                          <label className="flex items-center gap-2 text-sm font-medium">
                            <input
                              type="checkbox"
                              className="h-4 w-4 accent-primary"
                              checked={o.selected && !o.exists}
                              disabled={o.exists || !parts.outcomes}
                              onChange={(e) =>
                                setOutcomes((prev) => prev.map((x, j) => (j === i ? { ...x, selected: e.target.checked } : x)))
                              }
                            />
                            <span className="font-mono">{o.code}</span>
                            {o.exists && <Badge variant="secondary" className="text-xs">already in the course</Badge>}
                          </label>
                          <div className="flex flex-wrap gap-1">
                            {o.bloom_levels.map((b) => (
                              <Badge key={b.id} variant="outline" className={cn("font-mono text-xs", !o.bloom_stated && "border-dashed")}>
                                {b.code} {b.name}
                              </Badge>
                            ))}
                          </div>
                        </div>
                        <Textarea
                          rows={2}
                          value={o.statement}
                          disabled={o.exists}
                          onChange={(e) =>
                            setOutcomes((prev) => prev.map((x, j) => (j === i ? { ...x, statement: e.target.value } : x)))
                          }
                        />
                        <WarningList warnings={o.warnings} />
                      </li>
                    ))}
                  </ul>
                ) : (
                  <Empty>No course outcomes found.</Empty>
                )}
              </Section>

              <Section
                title={`Weekly topics (${preview.topics.length})`}
                checked={parts.topics}
                disabled={preview.topics.length === 0}
                note={
                  preview.current.lesson_items > 0
                    ? "Updates the course content. The existing lesson plan is kept."
                    : "Sets the course content and creates the lesson plan."
                }
                onCheck={(v) => setParts((p) => ({ ...p, topics: v }))}
              >
                {preview.topics.length ? (
                  <ol className="space-y-0.5 text-sm">
                    {preview.topics.map((t, i) => (
                      <li key={i} className="flex gap-2">
                        <span className="w-16 shrink-0 text-muted-foreground">{t.week ? `Week ${t.week}` : `#${i + 1}`}</span>
                        {t.topic}
                      </li>
                    ))}
                  </ol>
                ) : (
                  <Empty>No topics found.</Empty>
                )}
              </Section>

              <p className="flex items-start gap-1.5 text-xs text-muted-foreground">
                <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                Read from {preview.filename} by {preview.model} · {preview.prompt_version}. After importing, map the new COs
                to POs with ✨ on the CO-PO matrix.
              </p>
            </div>
          )}

          <DialogFooter showCloseButton>
            {preview && (
              <>
                <Button variant="outline" onClick={() => { authoringApi.decide(preview.suggestion_id, "REJECTED"); setPreview(null) }}>
                  Choose another file
                </Button>
                <Button disabled={!anything || apply.isPending} onClick={() => apply.mutate()}>
                  {apply.isPending && <Loader2 className="animate-spin" />}
                  Import
                </Button>
              </>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}

function Section({
  title,
  checked,
  disabled,
  note,
  onCheck,
  children,
}: {
  title: string
  checked: boolean
  disabled?: boolean
  note?: string
  onCheck: (value: boolean) => void
  children: React.ReactNode
}) {
  return (
    <section className={cn("space-y-2", !checked && "opacity-60")}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <label className="flex items-center gap-2 text-sm font-semibold">
          <input
            type="checkbox"
            className="h-4 w-4 accent-primary"
            checked={checked && !disabled}
            disabled={disabled}
            onChange={(e) => onCheck(e.target.checked)}
          />
          {title}
        </label>
        {note && <span className="text-xs text-muted-foreground">{note}</span>}
      </div>
      {children}
    </section>
  )
}

function Empty({ children }: { children: React.ReactNode }) {
  return <p className="text-sm text-muted-foreground">{children}</p>
}
