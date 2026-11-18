"use client"

import { format } from "date-fns"
import { CalendarClock, Copy, ExternalLink, Infinity as InfinityIcon, Loader2, RotateCcw, Timer } from "lucide-react"
import { useState } from "react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import type { SettingsInput } from "@/lib/docs/api"
import type { AdminDocs, ScheduleMode, VisibilityState } from "@/lib/docs/types"
import { cn } from "@/lib/utils"

export const STATE_STYLE: Record<VisibilityState, { label: string; className: string }> = {
  live: { label: "Live — public", className: "bg-emerald-500/10 text-emerald-700 ring-emerald-500/30 dark:text-emerald-300" },
  not_started: { label: "Scheduled", className: "bg-sky-500/10 text-sky-700 ring-sky-500/30 dark:text-sky-300" },
  ended: { label: "Window ended", className: "bg-amber-500/10 text-amber-700 ring-amber-500/30 dark:text-amber-300" },
  disabled: { label: "Off — not public", className: "bg-destructive/10 text-destructive ring-destructive/30" },
}

/** ISO → value for <input type="datetime-local"> in the browser's time zone. */
function toLocal(iso: string | null): string {
  if (!iso) return ""
  const d = new Date(iso)
  const pad = (n: number) => String(n).padStart(2, "0")
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function fromLocal(value: string): string | null {
  return value ? new Date(value).toISOString() : null
}

function nice(iso: string | null) {
  return iso ? format(new Date(iso), "EEE d MMM yyyy, HH:mm") : "—"
}

const MODES: { mode: ScheduleMode; title: string; text: string; icon: typeof Timer }[] = [
  { mode: "always", title: "Always on", text: "Public until you switch it off.", icon: InfinityIcon },
  { mode: "window", title: "Date window", text: "Public between a start and an end.", icon: CalendarClock },
  { mode: "duration", title: "Duration", text: "Public for a set time from a start.", icon: Timer },
]

export function PublishingPanel({ docs, saving, onSave, onReset }: {
  docs: AdminDocs
  saving: boolean
  onSave: (body: SettingsInput) => void
  onReset: () => void
}) {
  const s = docs.settings
  const [enabled, setEnabled] = useState(s.is_enabled)
  const [mode, setMode] = useState<ScheduleMode>(s.schedule_mode)
  const [start, setStart] = useState(toLocal(s.starts_at))
  const [end, setEnd] = useState(toLocal(s.ends_at))
  const [amount, setAmount] = useState(() => {
    const m = s.duration_minutes ?? 0
    return m && m % 1440 === 0 ? String(m / 1440) : m ? String(Math.round(m / 60)) : "72"
  })
  const [unit, setUnit] = useState<"hours" | "days">(() => (s.duration_minutes && s.duration_minutes % 1440 === 0 ? "days" : "hours"))
  const [teamName, setTeamName] = useState(s.team_name ?? "")
  const zone = Intl.DateTimeFormat().resolvedOptions().timeZone
  const state = STATE_STYLE[docs.visibility.state]

  function save() {
    const minutes = Math.round(Number(amount) * (unit === "days" ? 1440 : 60))
    if (mode !== "always" && !start) return toast.error("Choose a start date and time")
    if (mode === "window" && !end) return toast.error("Choose an end date and time")
    if (mode === "duration" && !(minutes > 0)) return toast.error("Enter a duration")
    onSave({
      is_enabled: enabled,
      schedule_mode: mode,
      starts_at: mode === "always" ? null : fromLocal(start),
      ends_at: mode === "window" ? fromLocal(end) : null,
      duration_minutes: mode === "duration" ? minutes : null,
      team_name: teamName.trim() || null,
    })
  }

  async function copy() {
    await navigator.clipboard.writeText(docs.public_url)
    toast.success("Public link copied")
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
      <Card>
        <CardHeader>
          <CardTitle>Visibility and schedule</CardTitle>
          <CardDescription>
            Off: /docs shows “Not available” to everyone. On: it is public, within the schedule below.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <button
            type="button"
            role="switch"
            aria-checked={enabled}
            onClick={() => setEnabled((v) => !v)}
            className="flex w-full items-center justify-between gap-4 rounded-xl border p-4 text-left"
          >
            <div>
              <div className="font-medium">Publish the /docs page</div>
              <div className="text-sm text-muted-foreground">{enabled ? "On — visible within the schedule" : "Off — not accessible"}</div>
            </div>
            <span className={cn("relative inline-flex h-6 w-11 shrink-0 rounded-full transition-colors", enabled ? "bg-emerald-600" : "bg-muted-foreground/30")}>
              <span className={cn("absolute top-0.5 size-5 rounded-full bg-white shadow transition-transform", enabled ? "translate-x-5" : "translate-x-0.5")} />
            </span>
          </button>

          <fieldset className="space-y-2">
            <legend className="mb-2 text-sm font-medium">Schedule</legend>
            <div className="grid gap-2 sm:grid-cols-3">
              {MODES.map((m) => (
                <label
                  key={m.mode}
                  className={cn(
                    "flex cursor-pointer flex-col gap-1 rounded-xl border p-3 text-sm transition-colors",
                    mode === m.mode ? "border-[#1d7254] bg-[#eef7f2] dark:border-[#5BD69B] dark:bg-[#173328]" : "hover:bg-muted/50"
                  )}
                >
                  <input type="radio" name="mode" value={m.mode} checked={mode === m.mode} onChange={() => setMode(m.mode)} className="sr-only" />
                  <span className="flex items-center gap-1.5 font-medium"><m.icon className="size-4" aria-hidden /> {m.title}</span>
                  <span className="text-xs text-muted-foreground">{m.text}</span>
                </label>
              ))}
            </div>
          </fieldset>

          {mode !== "always" && (
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label htmlFor="start">Start</Label>
                <Input id="start" type="datetime-local" value={start} onChange={(e) => setStart(e.target.value)} />
              </div>
              {mode === "window" ? (
                <div className="space-y-1.5">
                  <Label htmlFor="end">End</Label>
                  <Input id="end" type="datetime-local" value={end} onChange={(e) => setEnd(e.target.value)} />
                </div>
              ) : (
                <div className="space-y-1.5">
                  <Label htmlFor="amount">Duration</Label>
                  <div className="flex gap-2">
                    <Input id="amount" type="number" min={1} value={amount} onChange={(e) => setAmount(e.target.value)} className="w-28" />
                    <select
                      value={unit}
                      onChange={(e) => setUnit(e.target.value as "hours" | "days")}
                      aria-label="Unit"
                      className="h-8 rounded-lg border border-input bg-transparent px-2 text-sm"
                    >
                      <option value="hours">hours</option>
                      <option value="days">days</option>
                    </select>
                  </div>
                </div>
              )}
              <p className="text-xs text-muted-foreground sm:col-span-2">Times are in your browser&apos;s time zone ({zone}).</p>
            </div>
          )}

          <div className="space-y-1.5">
            <Label htmlFor="team-name">Team name (optional)</Label>
            <Input id="team-name" value={teamName} onChange={(e) => setTeamName(e.target.value)} placeholder="e.g. Team Obelytics" maxLength={150} />
          </div>

          <div className="flex flex-wrap items-center gap-2 border-t pt-4">
            <Button onClick={save} disabled={saving}>
              {saving && <Loader2 className="animate-spin" data-icon="inline-start" />} Save visibility
            </Button>
            <Button variant="outline" onClick={onReset} disabled={saving}>
              <RotateCcw data-icon="inline-start" /> Default window (June 10–14)
            </Button>
          </div>
        </CardContent>
      </Card>

      <div className="space-y-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Right now</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <span className={cn("inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ring-1", state.className)}>{state.label}</span>
            <p className="text-muted-foreground">{docs.visibility.message}</p>
            <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-xs">
              <dt className="text-muted-foreground">Opens</dt><dd>{docs.settings.schedule_mode === "always" ? "—" : nice(docs.visibility.starts_at)}</dd>
              <dt className="text-muted-foreground">Closes</dt><dd>{docs.settings.schedule_mode === "always" ? "never" : nice(docs.visibility.ends_at)}</dd>
            </dl>
            <div className="flex flex-wrap gap-2 pt-1">
              <Button size="sm" variant="outline" nativeButton={false} render={<a href="/docs" target="_blank" rel="noreferrer" />}>
                Open /docs <ExternalLink data-icon="inline-end" />
              </Button>
              <Button size="sm" variant="ghost" onClick={() => void copy()}>
                <Copy data-icon="inline-start" /> Copy link
              </Button>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Default window</CardTitle>
            <CardDescription>
              {nice(docs.settings.default_starts_at)} → {nice(docs.settings.default_ends_at)} (June 10, 00:00 → June 14, 23:59, {docs.settings.timezone}).
            </CardDescription>
          </CardHeader>
        </Card>
      </div>
    </div>
  )
}
