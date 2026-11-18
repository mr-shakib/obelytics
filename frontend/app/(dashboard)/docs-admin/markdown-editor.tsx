"use client"

import { Bold, Code, Heading3, Italic, Link2, List, ListOrdered, Quote, Table2 } from "lucide-react"
import { useRef, useState } from "react"

import { Markdown } from "@/components/docs/markdown"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

type Props = {
  value: string
  onChange: (value: string) => void
  onSave?: () => void
  placeholder?: string
}

type Edit = { text: string; start: number; end: number }

function wrap(value: string, start: number, end: number, before: string, after = before, fallback = "text"): Edit {
  const selected = value.slice(start, end) || fallback
  const text = value.slice(0, start) + before + selected + after + value.slice(end)
  return { text, start: start + before.length, end: start + before.length + selected.length }
}

function prefixLines(value: string, start: number, end: number, prefix: (i: number) => string): Edit {
  const lineStart = value.lastIndexOf("\n", start - 1) + 1
  const lineEnd = value.indexOf("\n", end) === -1 ? value.length : value.indexOf("\n", end)
  const lines = value.slice(lineStart, lineEnd).split("\n")
  const block = lines.map((l, i) => prefix(i) + l).join("\n")
  const text = value.slice(0, lineStart) + block + value.slice(lineEnd)
  return { text, start: lineStart, end: lineStart + block.length }
}

const TABLE = "\n| Column | Column |\n|---|---|\n| Value | Value |\n"

type Make = (v: string, s: number, e: number) => Edit

const TOOLS: { id: string; icon: typeof Bold; label: string; make: Make }[] = [
  { id: "bold", icon: Bold, label: "Bold (Ctrl+B)", make: (v, s, e) => wrap(v, s, e, "**") },
  { id: "italic", icon: Italic, label: "Italic (Ctrl+I)", make: (v, s, e) => wrap(v, s, e, "_") },
  { id: "heading", icon: Heading3, label: "Heading", make: (v, s, e) => prefixLines(v, s, e, () => "### ") },
  { id: "ul", icon: List, label: "Bulleted list", make: (v, s, e) => prefixLines(v, s, e, () => "- ") },
  { id: "ol", icon: ListOrdered, label: "Numbered list", make: (v, s, e) => prefixLines(v, s, e, (i) => `${i + 1}. `) },
  { id: "quote", icon: Quote, label: "Quote", make: (v, s, e) => prefixLines(v, s, e, () => "> ") },
  { id: "code", icon: Code, label: "Code", make: (v, s, e) => wrap(v, s, e, "`", "`", "code") },
  { id: "link", icon: Link2, label: "Link (Ctrl+K)", make: (v, s, e) => wrap(v, s, e, "[", "](https://)", "link text") },
  { id: "table", icon: Table2, label: "Table", make: (v, _s, e) => ({ text: v.slice(0, e) + TABLE + v.slice(e), start: e + 1, end: e + TABLE.length }) },
]
const SHORTCUTS: Record<string, string> = { b: "bold", i: "italic", k: "link" }

/**
 * Formatting toolbar + live preview. What the preview shows is exactly what the public page
 * renders (same component), so editors see the result as they type.
 */
export function MarkdownEditor({ value, onChange, onSave, placeholder }: Props) {
  const ref = useRef<HTMLTextAreaElement>(null)
  const [view, setView] = useState<"write" | "preview">("write")

  // Event handlers only: reads the textarea's selection, applies the edit, restores the selection.
  function apply(id: string) {
    const el = ref.current
    const tool = TOOLS.find((t) => t.id === id)
    if (!el || !tool) return
    const { text, start, end } = tool.make(value, el.selectionStart, el.selectionEnd)
    onChange(text)
    requestAnimationFrame(() => {
      el.focus()
      el.setSelectionRange(start, end)
    })
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (!(e.ctrlKey || e.metaKey)) return
    const key = e.key.toLowerCase()
    if (SHORTCUTS[key]) {
      e.preventDefault()
      apply(SHORTCUTS[key])
    } else if (key === "s" && onSave) {
      e.preventDefault()
      onSave()
    }
  }

  return (
    <div className="overflow-hidden rounded-xl border">
      <div className="flex flex-wrap items-center gap-0.5 border-b bg-muted/40 px-1.5 py-1">
        {TOOLS.map((t) => (
          <Button key={t.id} type="button" variant="ghost" size="icon-sm" onClick={() => apply(t.id)} title={t.label} aria-label={t.label}>
            <t.icon />
          </Button>
        ))}
        <div className="ml-auto flex rounded-md border bg-background p-0.5 lg:hidden">
          {(["write", "preview"] as const).map((v) => (
            <button
              key={v}
              type="button"
              onClick={() => setView(v)}
              className={cn("rounded px-2 py-0.5 text-xs capitalize", view === v ? "bg-muted font-medium" : "text-muted-foreground")}
            >
              {v}
            </button>
          ))}
        </div>
      </div>
      <div className="grid lg:grid-cols-2">
        <textarea
          ref={ref}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder={placeholder ?? "Write with the toolbar or Markdown…"}
          spellCheck
          aria-label="Section text"
          className={cn(
            "min-h-[420px] w-full resize-y bg-background p-4 font-mono text-[13px] leading-6 outline-none lg:border-r",
            view === "preview" && "hidden lg:block"
          )}
        />
        <div className={cn("max-h-[640px] min-h-[420px] overflow-y-auto bg-card p-5", view === "write" && "hidden lg:block")}>
          <div className="mb-3 text-[11px] font-semibold tracking-wider text-muted-foreground uppercase">Live preview</div>
          {value.trim() ? <Markdown>{value}</Markdown> : <p className="text-sm text-muted-foreground">Nothing to preview yet.</p>}
        </div>
      </div>
    </div>
  )
}
