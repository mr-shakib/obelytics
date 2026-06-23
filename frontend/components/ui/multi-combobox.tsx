"use client"

import * as React from "react"
import { ChevronsUpDown, X } from "lucide-react"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"

export type ComboboxOption = {
  value: string
  label: string
}

function MultiCombobox({
  options,
  values,
  onValuesChange,
  placeholder = "Select…",
  searchPlaceholder = "Search…",
  emptyText = "No results found.",
  className,
  triggerClassName,
  disabled,
}: {
  options: ComboboxOption[]
  values: string[]
  onValuesChange: (values: string[]) => void
  placeholder?: string
  searchPlaceholder?: string
  emptyText?: string
  className?: string
  triggerClassName?: string
  disabled?: boolean
}) {
  const [open, setOpen] = React.useState(false)
  const selected = options.filter((o) => values.includes(o.value))

  function toggle(val: string) {
    if (values.includes(val)) {
      onValuesChange(values.filter((v) => v !== val))
    } else {
      onValuesChange([...values, val])
    }
  }

  function remove(val: string) {
    onValuesChange(values.filter((v) => v !== val))
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger
        disabled={disabled}
        render={
          <Button
            variant="outline"
            role="combobox"
            aria-expanded={open}
            className={cn("justify-between font-normal min-h-9 h-auto py-1.5 w-full", triggerClassName)}
          />
        }
      >
        {selected.length === 0 ? (
          <span className="text-muted-foreground">{placeholder}</span>
        ) : (
          <div className="flex flex-wrap gap-1">
            {selected.map((s) => (
              <Badge key={s.value} variant="secondary" className="text-xs gap-1 pr-1">
                {s.label}
                <button
                  type="button"
                  onClick={(e) => { e.stopPropagation(); remove(s.value) }}
                  className="ml-0.5 rounded-full hover:bg-muted-foreground/20 p-0.5"
                >
                  <X className="h-3 w-3" />
                </button>
              </Badge>
            ))}
          </div>
        )}
        <ChevronsUpDown className="opacity-50 shrink-0 ml-2" />
      </PopoverTrigger>
      <PopoverContent className={cn("w-(--anchor-width) min-w-48 p-0", className)} align="start">
        <Command>
          <CommandInput placeholder={searchPlaceholder} />
          <CommandList>
            <CommandEmpty>{emptyText}</CommandEmpty>
            <CommandGroup>
              {options.map((option) => {
                const checked = values.includes(option.value)
                return (
                  <CommandItem
                    key={option.value}
                    value={option.label}
                    onSelect={() => toggle(option.value)}
                  >
                    <span className={cn("flex-1", checked && "font-medium")}>{option.label}</span>
                    {checked && <span className="text-primary">✓</span>}
                  </CommandItem>
                )
              })}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  )
}

export { MultiCombobox }
