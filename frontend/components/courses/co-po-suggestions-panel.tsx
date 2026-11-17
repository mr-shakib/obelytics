"use client"

import { AlertTriangle, Ban, Info, Loader2, Sparkles, X } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import type { MappingSuggestResponse, SuggestedAttribute, SuggestedLink } from "@/lib/api/authoring"
import { cn } from "@/lib/utils"

interface Props {
  suggestion: MappingSuggestResponse
  selected: Set<number>
  weights: Map<number, 1 | 2 | 3>
  canManage: boolean
  applying: boolean
  onToggle: (index: number) => void
  onSelectAll: (select: boolean) => void
  onWeightChange: (index: number, weight: 1 | 2 | 3) => void
  onApply: () => void
  onDismiss: () => void
}

/** The AI's CO-PO links, each already checked against the K, CEP and CEA rules. */
export function CoPoSuggestionsPanel({
  suggestion,
  selected,
  weights,
  canManage,
  applying,
  onToggle,
  onSelectAll,
  onWeightChange,
  onApply,
  onDismiss,
}: Props) {
  const scope = suggestion.course_outcome_codes ?? []
  const applicable = suggestion.links.filter((l) => l.can_apply)
  const allSelected = applicable.length > 0 && applicable.every((l) => selected.has(l.index))

  return (
    <div className="space-y-3 rounded-xl border border-violet-200 bg-violet-50/40 p-4 dark:border-violet-900/50 dark:bg-violet-950/10">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="space-y-0.5">
          <div className="flex items-center gap-1.5 text-sm font-medium text-violet-900 dark:text-violet-200">
            <Sparkles className="h-4 w-4" />
            AI suggestions
            {scope.length > 0 && (
              <span className="font-normal text-muted-foreground">for {scope.join(", ")}</span>
            )}
          </div>
          <p className="text-xs text-muted-foreground">
            Every link was checked against the mapping rules. Review each one; nothing is saved until you apply it.
            {" "}· {suggestion.model} · {suggestion.prompt_version}
          </p>
        </div>
        <Button type="button" variant="ghost" size="icon-sm" aria-label="Dismiss suggestions" onClick={onDismiss}>
          <X />
        </Button>
      </div>

      {suggestion.pos_without_knowledge_profiles.length > 0 && (
        <p className="flex items-start gap-1.5 text-xs text-muted-foreground">
          <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          {suggestion.pos_without_knowledge_profiles.join(", ")}{" "}
          {suggestion.pos_without_knowledge_profiles.length === 1 ? "has" : "have"} no required knowledge
          profiles set, so the K rule cannot check links to{" "}
          {suggestion.pos_without_knowledge_profiles.length === 1 ? "it" : "them"}. Set them on the program page.
        </p>
      )}

      {suggestion.links.length === 0 ? (
        <p className="text-sm text-muted-foreground">The AI did not suggest any links.</p>
      ) : (
        <ul className="divide-y rounded-lg border bg-background">
          {suggestion.links.map((link) => (
            <LinkRow
              key={link.index}
              link={link}
              checked={selected.has(link.index)}
              weight={weights.get(link.index) ?? link.weight}
              canManage={canManage}
              onToggle={() => onToggle(link.index)}
              onWeightChange={(w) => onWeightChange(link.index, w)}
            />
          ))}
        </ul>
      )}

      {suggestion.existing_not_suggested.length > 0 && (
        <p className="text-xs text-muted-foreground">
          The AI did not suggest these existing links — check they still hold:{" "}
          {suggestion.existing_not_suggested.map((l) => `${l.co_code}→${l.po_code}`).join(", ")}.
        </p>
      )}

      {canManage && applicable.length > 0 && (
        <div className="flex flex-wrap items-center gap-2">
          <Button type="button" size="sm" disabled={selected.size === 0 || applying} onClick={onApply}>
            {applying && <Loader2 className="animate-spin" />}
            Apply {selected.size} selected
          </Button>
          <Button type="button" size="sm" variant="outline" onClick={() => onSelectAll(!allSelected)}>
            {allSelected ? "Clear selection" : `Select all ${applicable.length} that pass the rules`}
          </Button>
        </div>
      )}
    </div>
  )
}

function LinkRow({
  link,
  checked,
  weight,
  canManage,
  onToggle,
  onWeightChange,
}: {
  link: SuggestedLink
  checked: boolean
  weight: 1 | 2 | 3
  canManage: boolean
  onToggle: () => void
  onWeightChange: (weight: 1 | 2 | 3) => void
}) {
  const blocked = link.issues.length > 0
  return (
    <li className={cn("flex gap-3 p-3", (blocked || link.already_mapped) && "bg-muted/30")}>
      <div className="pt-0.5">
        {link.can_apply && canManage ? (
          <input
            type="checkbox"
            className="h-4 w-4 cursor-pointer accent-primary"
            checked={checked}
            onChange={onToggle}
            aria-label={`Apply ${link.co_code} to ${link.po_code}`}
          />
        ) : blocked ? (
          <Ban className="h-4 w-4 text-destructive" aria-label="Breaks a mapping rule" />
        ) : (
          <span className="block h-4 w-4" />
        )}
      </div>
      <div className="min-w-0 flex-1 space-y-1.5">
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <span className="font-mono font-semibold">
            {link.co_code} → {link.po_code}
          </span>
          {link.can_apply && canManage ? (
            <select
              value={weight}
              onChange={(event) => onWeightChange(Number(event.target.value) as 1 | 2 | 3)}
              className="h-6 rounded border bg-background px-1 text-xs"
              aria-label="Weight"
            >
              <option value={3}>Weight 3 · strong</option>
              <option value={2}>Weight 2 · moderate</option>
              <option value={1}>Weight 1 · weak</option>
            </select>
          ) : (
            <Badge variant="outline" className="text-xs">Weight {link.weight}</Badge>
          )}
          {link.confidence !== null && (
            <span className="text-xs text-muted-foreground">{Math.round(link.confidence * 100)}% confident</span>
          )}
          {link.already_mapped && <Badge variant="secondary" className="text-xs">Already mapped</Badge>}
        </div>
        {link.justification && <p className="text-sm text-muted-foreground">{link.justification}</p>}
        <AttributeChips label="K" items={link.knowledge_profiles} />
        <AttributeChips label="CEP" items={link.complex_problems} />
        <AttributeChips label="CEA" items={link.complex_activities} />
        {link.issues.map((issue, i) => (
          <p key={`i${i}`} className="flex items-start gap-1.5 text-xs text-destructive">
            <Ban className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            {issue}
          </p>
        ))}
        {link.warnings.map((warning, i) => (
          <p key={`w${i}`} className="flex items-start gap-1.5 text-xs text-amber-800 dark:text-amber-300">
            <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            {warning}
          </p>
        ))}
      </div>
    </li>
  )
}

function AttributeChips({ label, items }: { label: string; items: SuggestedAttribute[] }) {
  if (items.length === 0) return null
  return (
    <div className="flex flex-wrap items-center gap-1">
      {items.map((item) => (
        <span
          key={item.id}
          title={item.justification || undefined}
          className={cn(
            "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
            item.already_mapped
              ? "bg-muted text-muted-foreground"
              : "bg-violet-100 text-violet-800 dark:bg-violet-900/40 dark:text-violet-200"
          )}
        >
          {item.already_mapped ? "Uses" : "Adds"} {item.code}
          <span className="sr-only"> ({label})</span>
        </span>
      ))}
    </div>
  )
}
