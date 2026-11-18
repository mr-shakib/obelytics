"use client"

import { ArrowDown, ArrowUp, Plus, Trash2 } from "lucide-react"

import { MermaidDiagram } from "@/components/docs/mermaid-diagram"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { AI_FEATURES, type ChangelogItem, type FeatureItem, type SectionData, SIGNALS } from "@/lib/docs/types"

type Props = { kind: string; data: SectionData; onChange: (data: SectionData) => void }

const SELECT =
  "h-8 w-full rounded-lg border border-input bg-transparent px-2 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"

function move<T>(list: T[], from: number, to: number): T[] {
  if (to < 0 || to >= list.length) return list
  const next = [...list]
  const [item] = next.splice(from, 1)
  next.splice(to, 0, item)
  return next
}

function RowTools({ index, count, onMove, onRemove }: {
  index: number
  count: number
  onMove: (to: number) => void
  onRemove: () => void
}) {
  return (
    <div className="flex items-center gap-0.5">
      <Button type="button" variant="ghost" size="icon-xs" disabled={index === 0} onClick={() => onMove(index - 1)} aria-label="Move up"><ArrowUp /></Button>
      <Button type="button" variant="ghost" size="icon-xs" disabled={index === count - 1} onClick={() => onMove(index + 1)} aria-label="Move down"><ArrowDown /></Button>
      <Button type="button" variant="ghost" size="icon-xs" onClick={onRemove} aria-label="Remove"><Trash2 /></Button>
    </div>
  )
}

function FeaturesEditor({ data, onChange }: Omit<Props, "kind">) {
  const items = (data.items ?? []) as FeatureItem[]
  const set = (next: FeatureItem[]) => onChange({ ...data, items: next })
  const update = (i: number, patch: Partial<FeatureItem>) => set(items.map((it, j) => (j === i ? { ...it, ...patch } : it)))
  return (
    <div className="space-y-2">
      {items.map((item, i) => (
        <div key={i} className="space-y-2 rounded-lg border p-3">
          <div className="flex items-center gap-2">
            <Input value={item.name} onChange={(e) => update(i, { name: e.target.value })} placeholder="Feature name" className="font-medium" aria-label="Feature name" />
            <RowTools index={i} count={items.length} onMove={(to) => set(move(items, i, to))} onRemove={() => set(items.filter((_, j) => j !== i))} />
          </div>
          <div className="grid gap-2 sm:grid-cols-4">
            <Input value={item.area} onChange={(e) => update(i, { area: e.target.value })} placeholder="Area" aria-label="Area" />
            <select className={SELECT} value={item.status} onChange={(e) => update(i, { status: e.target.value as FeatureItem["status"] })} aria-label="Status">
              <option value="live">Live</option>
              <option value="beta">Beta</option>
              <option value="upcoming">Upcoming</option>
              <option value="planned">Planned</option>
            </select>
            <select className={SELECT} value={item.signal ?? ""} onChange={(e) => update(i, { signal: e.target.value || null })} aria-label="Live usage counter">
              <option value="">No live counter</option>
              {SIGNALS.map((s) => <option key={s} value={s}>{s.replaceAll("_", " ")}</option>)}
            </select>
            <select className={SELECT} value={item.ai_feature ?? ""} onChange={(e) => update(i, { ai_feature: e.target.value || null })} aria-label="AI feature">
              <option value="">Not an AI feature</option>
              {AI_FEATURES.map((f) => <option key={f} value={f}>AI: {f}</option>)}
            </select>
          </div>
          <Input value={item.description} onChange={(e) => update(i, { description: e.target.value })} placeholder="One-line description" aria-label="Description" />
        </div>
      ))}
      <Button type="button" variant="outline" size="sm" onClick={() => set([...items, { name: "", area: "", status: "planned", description: "", signal: null, ai_feature: null }])}>
        <Plus data-icon="inline-start" /> Add feature
      </Button>
    </div>
  )
}

function ChangelogEditor({ data, onChange }: Omit<Props, "kind">) {
  const items = (data.items ?? []) as ChangelogItem[]
  const set = (next: ChangelogItem[]) => onChange({ ...data, items: next })
  const update = (i: number, patch: Partial<ChangelogItem>) => set(items.map((it, j) => (j === i ? { ...it, ...patch } : it)))
  return (
    <div className="space-y-2">
      <Button type="button" variant="outline" size="sm" onClick={() => {
        const today = new Date().toISOString().slice(0, 10)
        set([{ version: today.replaceAll("-", "."), date: today, title: "", notes: "" }, ...items])
      }}>
        <Plus data-icon="inline-start" /> Add entry at the top
      </Button>
      {items.map((item, i) => (
        <div key={i} className="space-y-2 rounded-lg border p-3">
          <div className="flex items-center gap-2">
            <Input value={item.version} onChange={(e) => update(i, { version: e.target.value })} placeholder="Version" className="w-32 font-mono" aria-label="Version" />
            <Input type="date" value={item.date} onChange={(e) => update(i, { date: e.target.value })} className="w-40" aria-label="Date" />
            <Input value={item.title} onChange={(e) => update(i, { title: e.target.value })} placeholder="Title" aria-label="Title" />
            <RowTools index={i} count={items.length} onMove={(to) => set(move(items, i, to))} onRemove={() => set(items.filter((_, j) => j !== i))} />
          </div>
          <Input value={item.notes} onChange={(e) => update(i, { notes: e.target.value })} placeholder="What changed" aria-label="Notes" />
        </div>
      ))}
    </div>
  )
}

function DiagramEditor({ data, onChange }: Omit<Props, "kind">) {
  return (
    <div className="grid gap-3 lg:grid-cols-2">
      <div className="space-y-1.5">
        <Label htmlFor="mermaid">Mermaid source</Label>
        <textarea
          id="mermaid"
          value={data.mermaid ?? ""}
          onChange={(e) => onChange({ ...data, mermaid: e.target.value })}
          spellCheck={false}
          className="min-h-[360px] w-full resize-y rounded-xl border bg-background p-3 font-mono text-[12px] leading-5 outline-none focus-visible:border-ring"
        />
        <p className="text-xs text-muted-foreground">
          Flowchart syntax: <code>A[&quot;Box&quot;] --&gt; B[(&quot;Database&quot;)]</code>. Use <code>&lt;br/&gt;</code> for a line break.
        </p>
      </div>
      <div className="space-y-1.5">
        <Label>Preview</Label>
        <MermaidDiagram code={data.mermaid ?? ""} label="Diagram preview" />
      </div>
    </div>
  )
}

function DemoEditor({ data, onChange }: Omit<Props, "kind">) {
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <div className="space-y-1.5">
        <Label htmlFor="video">YouTube video link</Label>
        <Input id="video" value={data.video_url ?? ""} onChange={(e) => onChange({ ...data, video_url: e.target.value })} placeholder="https://youtu.be/…" />
        <p className="text-xs text-muted-foreground">Public or unlisted. It is embedded at the top of this section.</p>
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="demo">Live demo link</Label>
        <Input id="demo" value={data.demo_url ?? ""} onChange={(e) => onChange({ ...data, demo_url: e.target.value })} placeholder="https://…" />
      </div>
    </div>
  )
}

/** Structured content for sections that have more than text. */
export function DataEditor({ kind, data, onChange }: Props) {
  if (kind === "features") return <FeaturesEditor data={data} onChange={onChange} />
  if (kind === "changelog") return <ChangelogEditor data={data} onChange={onChange} />
  if (kind === "diagram") return <DiagramEditor data={data} onChange={onChange} />
  if (kind === "demo") return <DemoEditor data={data} onChange={onChange} />
  return null
}

export const DATA_KIND_LABEL: Record<string, string> = {
  features: "Features",
  changelog: "Entries",
  diagram: "Diagram",
  demo: "Video and demo",
}

export const LIVE_KIND_NOTE: Record<string, string> = {
  traction: "A live usage table (real institutions vs demo) appears under the text.",
  analytics: "Live charts, AI usage per feature and recent events appear under the text.",
  api: "The live MCP tool list and the full endpoint reference appear under the text.",
  team: "The team grid (Team tab) appears under the text.",
}
