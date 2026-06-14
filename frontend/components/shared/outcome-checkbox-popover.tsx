"use client"

import { useId } from "react"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"

export type OutcomeOption = { id: string; code: string }

interface OutcomeCheckboxPopoverProps {
  options: OutcomeOption[]
  value: string[]
  onChange: (ids: string[]) => void
  placeholder?: string
  disabled?: boolean
}

export function OutcomeCheckboxPopover({
  options,
  value,
  onChange,
  placeholder = "Select…",
  disabled,
}: OutcomeCheckboxPopoverProps) {
  const uid = useId()

  function toggle(optionId: string, checked: boolean) {
    onChange(checked ? [...value, optionId] : value.filter((v) => v !== optionId))
  }

  const selectedLabel = options
    .filter((o) => value.includes(o.id))
    .map((o) => o.code)
    .join(", ")

  return (
    <Popover>
      <PopoverTrigger
        disabled={disabled}
        render={
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="w-full min-w-28 justify-start font-normal"
          />
        }
      >
        <span className={cn("truncate", !selectedLabel && "text-muted-foreground")}>
          {selectedLabel || placeholder}
        </span>
      </PopoverTrigger>
      <PopoverContent className="w-56 p-2" align="start">
        {options.length === 0 ? (
          <p className="px-1 py-1 text-sm text-muted-foreground">No options available.</p>
        ) : (
          <div className="max-h-64 space-y-1 overflow-y-auto">
            {options.map((option) => (
              <div key={option.id} className="flex items-center gap-2 px-1 py-0.5">
                <input
                  type="checkbox"
                  id={`outcome-${uid}-${option.id}`}
                  checked={value.includes(option.id)}
                  disabled={disabled}
                  onChange={(e) => toggle(option.id, e.target.checked)}
                  className="h-4 w-4 rounded border-border disabled:opacity-50 disabled:cursor-not-allowed"
                />
                <Label htmlFor={`outcome-${uid}-${option.id}`} className="font-normal">
                  {option.code}
                </Label>
              </div>
            ))}
          </div>
        )}
      </PopoverContent>
    </Popover>
  )
}
