"use client"

import { useQuery } from "@tanstack/react-query"
import { format } from "date-fns"
import { ArrowDown, ArrowUp, Eye, EyeOff, GripVertical, History, Loader2, Plus, Send, Trash2, Undo2 } from "lucide-react"
import { useState } from "react"

import { Markdown } from "@/components/docs/markdown"
import { ConfirmDialog } from "@/components/shared/confirm-dialog"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { docsAdminApi } from "@/lib/docs/api"
import { type AdminDocs, type AdminSection, type DocsGroup, GROUP_ORDER, GROUP_TITLES, type SectionData } from "@/lib/docs/types"
import { cn } from "@/lib/utils"

import { DATA_KIND_LABEL, DataEditor, LIVE_KIND_NOTE } from "./data-editors"
import { MarkdownEditor } from "./markdown-editor"

export type SectionActions = {
  busy: boolean
  saveDraft: (id: string, body: { title: string; body: string; data?: SectionData }) => Promise<unknown>
  publish: (id: string) => Promise<unknown>
  publishAll: () => Promise<unknown>
  discard: (id: string) => Promise<unknown>
  restore: (id: string, version: number) => Promise<unknown>
  setVisible: (id: string, visible: boolean) => Promise<unknown>
  remove: (id: string) => Promise<unknown>
  reorder: (ids: string[]) => Promise<unknown>
  create: (title: string, group: DocsGroup) => Promise<unknown>
}

function ordered(sections: AdminSection[]) {
  return GROUP_ORDER.flatMap((g) => sections.filter((s) => s.group === g))
}

// ── Editor ────────────────────────────────────────────────────────────────────

function SectionEditor({ section, actions }: { section: AdminSection; actions: SectionActions }) {
  const [title, setTitle] = useState(section.draft_title)
  const [body, setBody] = useState(section.draft_body)
  const [data, setData] = useState<SectionData>(section.draft_data ?? {})
  const [historyOpen, setHistoryOpen] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const dirty =
    title !== section.draft_title || body !== section.draft_body || JSON.stringify(data) !== JSON.stringify(section.draft_data ?? {})
  const hasData = section.kind in DATA_KIND_LABEL

  const payload = () => ({ title: title.trim() || section.draft_title, body, ...(hasData ? { data } : {}) })
  const save = () => actions.saveDraft(section.id, payload())
  async function publish() {
    if (dirty) await actions.saveDraft(section.id, payload())
    await actions.publish(section.id)
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant="outline" className="font-mono">{section.kind}</Badge>
        <span className="text-xs text-muted-foreground">#{section.key}</span>
        {section.published_version > 0 && (
          <span className="text-xs text-muted-foreground">
            · published v{section.published_version}
            {section.published_at ? `, ${format(new Date(section.published_at), "d MMM yyyy HH:mm")}` : ""}
          </span>
        )}
        {dirty && <Badge className="bg-amber-500/15 text-amber-700 dark:text-amber-300">Unsaved</Badge>}
        {!dirty && section.has_changes && <Badge className="bg-sky-500/15 text-sky-700 dark:text-sky-300">Draft not published</Badge>}
        {!section.is_visible && <Badge variant="secondary">Hidden</Badge>}
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="section-title">Title</Label>
        <Input id="section-title" value={title} onChange={(e) => setTitle(e.target.value)} maxLength={200} className="text-base font-medium" />
      </div>

      {hasData && (
        <div className="space-y-2">
          <Label>{DATA_KIND_LABEL[section.kind]}</Label>
          <DataEditor kind={section.kind} data={data} onChange={setData} />
        </div>
      )}

      <div className="space-y-1.5">
        <Label>Text</Label>
        {LIVE_KIND_NOTE[section.kind] && <p className="text-xs text-muted-foreground">{LIVE_KIND_NOTE[section.kind]}</p>}
        <MarkdownEditor value={body} onChange={setBody} onSave={() => void save()} />
      </div>

      <div className="sticky bottom-0 -mx-1 flex flex-wrap items-center gap-2 border-t bg-background/95 px-1 py-3 backdrop-blur">
        <Button variant="outline" onClick={() => void save()} disabled={!dirty || actions.busy}>
          Save draft <kbd className="ml-1 hidden font-mono text-[10px] text-muted-foreground sm:inline">Ctrl S</kbd>
        </Button>
        <Button onClick={() => void publish()} disabled={(!dirty && !section.has_changes) || actions.busy}>
          {actions.busy ? <Loader2 className="animate-spin" data-icon="inline-start" /> : <Send data-icon="inline-start" />} Publish
        </Button>
        <Button
          variant="ghost"
          onClick={() => {
            if (dirty) {
              setTitle(section.draft_title)
              setBody(section.draft_body)
              setData(section.draft_data ?? {})
            } else void actions.discard(section.id)
          }}
          disabled={(!dirty && (!section.has_changes || section.published_version === 0)) || actions.busy}
          title={dirty ? "Undo unsaved edits" : "Go back to the published version"}
        >
          <Undo2 data-icon="inline-start" /> {dirty ? "Undo edits" : "Discard draft"}
        </Button>
        <div className="ml-auto flex items-center gap-1">
          <Button variant="ghost" size="sm" onClick={() => setHistoryOpen(true)} disabled={section.published_version === 0}>
            <History data-icon="inline-start" /> History
          </Button>
          <Button variant="ghost" size="sm" onClick={() => void actions.setVisible(section.id, !section.is_visible)} disabled={actions.busy}>
            {section.is_visible ? <EyeOff data-icon="inline-start" /> : <Eye data-icon="inline-start" />}
            {section.is_visible ? "Hide" : "Show"}
          </Button>
          {!section.is_builtin && (
            <Button variant="ghost" size="sm" className="text-destructive" onClick={() => setConfirmDelete(true)}>
              <Trash2 data-icon="inline-start" /> Delete
            </Button>
          )}
        </div>
      </div>

      {historyOpen && (
        <VersionsDialog
          section={section}
          onClose={() => setHistoryOpen(false)}
          onRestore={async (v) => {
            await actions.restore(section.id, v)
            setHistoryOpen(false)
          }}
        />
      )}
      <ConfirmDialog
        open={confirmDelete}
        onOpenChange={setConfirmDelete}
        title={`Delete “${section.draft_title}”?`}
        description="The section and its version history are removed. This can't be undone."
        confirmLabel="Delete section"
        variant="destructive"
        loading={actions.busy}
        onConfirm={() => void actions.remove(section.id).then(() => setConfirmDelete(false))}
      />
    </div>
  )
}

function VersionsDialog({ section, onClose, onRestore }: {
  section: AdminSection
  onClose: () => void
  onRestore: (version: number) => Promise<void>
}) {
  const { data: versions, isLoading } = useQuery({
    queryKey: ["docs", "versions", section.id, section.published_version],
    queryFn: () => docsAdminApi.versions(section.id),
  })
  const [open, setOpen] = useState<number | null>(null)
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Version history — {section.draft_title}</DialogTitle>
          <DialogDescription>Every publish is kept. Restoring copies a version into the draft; publish it to make it live.</DialogDescription>
        </DialogHeader>
        <div className="max-h-[60vh] space-y-2 overflow-y-auto">
          {isLoading && <Loader2 className="mx-auto animate-spin" />}
          {versions?.map((v) => (
            <div key={v.version} className="rounded-lg border">
              <div className="flex items-center justify-between gap-2 px-3 py-2">
                <button type="button" className="min-w-0 text-left" onClick={() => setOpen(open === v.version ? null : v.version)}>
                  <div className="text-sm font-medium">
                    v{v.version} · {v.title}
                    {v.version === section.published_version && <Badge className="ml-2 bg-emerald-500/15 text-emerald-700 dark:text-emerald-300">live</Badge>}
                  </div>
                  <div className="text-xs text-muted-foreground">{format(new Date(v.published_at), "d MMM yyyy, HH:mm")}</div>
                </button>
                <Button size="sm" variant="outline" onClick={() => void onRestore(v.version)}>Restore to draft</Button>
              </div>
              {open === v.version && (
                <div className="max-h-64 overflow-y-auto border-t bg-muted/30 p-3">
                  <Markdown className="text-sm">{v.body || "_(no text)_"}</Markdown>
                </div>
              )}
            </div>
          ))}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Close</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function AddSectionDialog({ open, onOpenChange, onCreate, busy }: {
  open: boolean
  onOpenChange: (o: boolean) => void
  onCreate: (title: string, group: DocsGroup) => void
  busy: boolean
}) {
  const [title, setTitle] = useState("")
  const [group, setGroup] = useState<DocsGroup>("operations")
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Add a section</DialogTitle>
          <DialogDescription>A text section you can write, publish and reorder like the others.</DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          <div className="space-y-1.5">
            <Label htmlFor="new-title">Title</Label>
            <Input id="new-title" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Pilot results" />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="new-group">Part of the page</Label>
            <select id="new-group" value={group} onChange={(e) => setGroup(e.target.value as DocsGroup)} className="h-8 w-full rounded-lg border border-input bg-transparent px-2 text-sm">
              {GROUP_ORDER.map((g) => <option key={g} value={g}>{GROUP_TITLES[g]}</option>)}
            </select>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button disabled={!title.trim() || busy} onClick={() => { onCreate(title.trim(), group); setTitle("") }}>Add section</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ── Panel ─────────────────────────────────────────────────────────────────────

export function SectionsPanel({ docs, actions }: { docs: AdminDocs; actions: SectionActions }) {
  const list = ordered(docs.sections)
  const [selectedId, setSelectedId] = useState<string>(list[0]?.id ?? "")
  const [dragId, setDragId] = useState<string | null>(null)
  const [overId, setOverId] = useState<string | null>(null)
  const [adding, setAdding] = useState(false)
  const selected = list.find((s) => s.id === selectedId) ?? list[0]
  const changes = list.filter((s) => s.has_changes).length

  function reorderTo(fromId: string, toId: string) {
    const from = list.find((s) => s.id === fromId)
    const to = list.find((s) => s.id === toId)
    if (!from || !to || from.id === to.id || from.group !== to.group) return
    const ids = list.map((s) => s.id).filter((id) => id !== from.id)
    ids.splice(ids.indexOf(to.id) + (list.indexOf(from) < list.indexOf(to) ? 1 : 0), 0, from.id)
    void actions.reorder(ids)
  }

  function step(section: AdminSection, dir: -1 | 1) {
    const siblings = list.filter((s) => s.group === section.group)
    const target = siblings[siblings.indexOf(section) + dir]
    if (target) reorderTo(section.id, target.id)
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2 rounded-xl border bg-muted/30 px-4 py-3">
        <div className="text-sm">
          {changes ? <><span className="font-semibold">{changes}</span> section{changes === 1 ? "" : "s"} with unpublished changes</> : "Everything is published."}
        </div>
        <div className="ml-auto flex gap-2">
          <Button variant="outline" size="sm" onClick={() => setAdding(true)}><Plus data-icon="inline-start" /> Add section</Button>
          <Button size="sm" onClick={() => void actions.publishAll()} disabled={!changes || actions.busy}>
            <Send data-icon="inline-start" /> Publish all changes
          </Button>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[300px_minmax(0,1fr)]">
        <nav aria-label="Sections" className="space-y-4 xl:sticky xl:top-4 xl:max-h-[calc(100vh-2rem)] xl:overflow-y-auto">
          {GROUP_ORDER.map((group) => {
            const rows = list.filter((s) => s.group === group)
            if (!rows.length) return null
            return (
              <div key={group}>
                <div className="mb-1.5 px-1 text-[11px] font-semibold tracking-wider text-muted-foreground uppercase">{GROUP_TITLES[group]}</div>
                <ul className="space-y-1">
                  {rows.map((s, i) => (
                    <li
                      key={s.id}
                      draggable
                      onDragStart={(e) => { setDragId(s.id); e.dataTransfer.effectAllowed = "move" }}
                      onDragOver={(e) => { if (dragId && list.find((x) => x.id === dragId)?.group === s.group) { e.preventDefault(); setOverId(s.id) } }}
                      onDragLeave={() => setOverId((o) => (o === s.id ? null : o))}
                      onDrop={(e) => { e.preventDefault(); if (dragId) reorderTo(dragId, s.id); setDragId(null); setOverId(null) }}
                      onDragEnd={() => { setDragId(null); setOverId(null) }}
                      className={cn(
                        "group flex items-center gap-1 rounded-lg border bg-card pr-1 transition-colors",
                        selected?.id === s.id && "border-[#1d7254] ring-1 ring-[#1d7254]/30 dark:border-[#5BD69B]",
                        overId === s.id && "border-dashed border-[#1d7254]",
                        dragId === s.id && "opacity-50"
                      )}
                    >
                      <span className="cursor-grab px-1 text-muted-foreground active:cursor-grabbing" aria-hidden><GripVertical className="size-4" /></span>
                      <button type="button" onClick={() => setSelectedId(s.id)} className="min-w-0 flex-1 py-2 text-left">
                        <div className={cn("truncate text-sm", !s.is_visible && "text-muted-foreground line-through")}>{s.draft_title}</div>
                        <div className="flex gap-1.5 text-[10px] text-muted-foreground">
                          <span>{s.kind}</span>
                          {s.has_changes && <span className="font-medium text-sky-600 dark:text-sky-400">· draft</span>}
                          {!s.is_visible && <span>· hidden</span>}
                        </div>
                      </button>
                      <div className="flex opacity-0 transition-opacity group-hover:opacity-100 focus-within:opacity-100">
                        <Button variant="ghost" size="icon-xs" disabled={i === 0} onClick={() => step(s, -1)} aria-label={`Move ${s.draft_title} up`}><ArrowUp /></Button>
                        <Button variant="ghost" size="icon-xs" disabled={i === rows.length - 1} onClick={() => step(s, 1)} aria-label={`Move ${s.draft_title} down`}><ArrowDown /></Button>
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            )
          })}
        </nav>

        <div className="min-w-0">
          {selected ? (
            <SectionEditor key={`${selected.id}:${selected.updated_at}:${selected.published_version}`} section={selected} actions={actions} />
          ) : (
            <p className="text-sm text-muted-foreground">Choose a section.</p>
          )}
        </div>
      </div>

      <AddSectionDialog
        open={adding}
        onOpenChange={setAdding}
        busy={actions.busy}
        onCreate={(title, group) => {
          void actions.create(title, group).then((res) => {
            const created = (res as AdminDocs | undefined)?.sections
              .filter((s) => !s.is_builtin && s.draft_title === title)
              .sort((a, b) => (b.updated_at ?? "").localeCompare(a.updated_at ?? ""))[0]
            if (created) setSelectedId(created.id)
            setAdding(false)
          })
        }}
      />
    </div>
  )
}
