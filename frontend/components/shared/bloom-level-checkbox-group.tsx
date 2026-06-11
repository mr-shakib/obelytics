"use client"

import { Label } from "@/components/ui/label"

export type BloomDomain = { id: string; name: string }
export type BloomLevel = {
  id: string
  code: string
  name: string
  bloom_domain_id: string
  order_index: number
}

interface BloomLevelCheckboxGroupProps {
  bloomDomains: BloomDomain[]
  bloomLevels: BloomLevel[]
  value: string[]
  onChange: (ids: string[]) => void
  disabled?: boolean
}

export function BloomLevelCheckboxGroup({
  bloomDomains,
  bloomLevels,
  value,
  onChange,
  disabled,
}: BloomLevelCheckboxGroupProps) {
  function toggle(id: string, checked: boolean) {
    onChange(checked ? [...value, id] : value.filter((v) => v !== id))
  }

  return (
    <div className="space-y-3">
      {bloomDomains.map((domain) => {
        const levels = bloomLevels
          .filter((l) => l.bloom_domain_id === domain.id)
          .sort((a, b) => a.order_index - b.order_index)
        if (levels.length === 0) return null
        return (
          <div key={domain.id} className="space-y-1.5">
            <p className="text-xs font-medium text-muted-foreground">{domain.name}</p>
            <div className="flex flex-wrap gap-x-4 gap-y-1.5">
              {levels.map((l) => (
                <div key={l.id} className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id={`bloom-level-${l.id}`}
                    checked={value.includes(l.id)}
                    disabled={disabled}
                    onChange={(e) => toggle(l.id, e.target.checked)}
                    className="h-4 w-4 rounded border-border disabled:opacity-50 disabled:cursor-not-allowed"
                  />
                  <Label htmlFor={`bloom-level-${l.id}`} className="font-normal">
                    {l.code} — {l.name}
                  </Label>
                </div>
              ))}
            </div>
          </div>
        )
      })}
    </div>
  )
}

/** Sort bloom level ids by domain order, then by level order within the domain. */
export function sortBloomLevelIds(
  ids: string[],
  bloomLevels: BloomLevel[],
  bloomDomains: BloomDomain[]
): string[] {
  const domainIndex = new Map(bloomDomains.map((d, i) => [d.id, i]))
  const levelById = new Map(bloomLevels.map((l) => [l.id, l]))
  return [...ids].sort((a, b) => {
    const la = levelById.get(a)
    const lb = levelById.get(b)
    if (!la || !lb) return 0
    const da = domainIndex.get(la.bloom_domain_id) ?? 0
    const db = domainIndex.get(lb.bloom_domain_id) ?? 0
    if (da !== db) return da - db
    return la.order_index - lb.order_index
  })
}
