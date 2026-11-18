import { CalendarClock, Lock } from "lucide-react"

import type { Visibility } from "@/lib/docs/types"

/** Shown instead of the page while it is switched off or outside its schedule. */
export function DocsUnavailable({ visibility }: { visibility: Visibility | null }) {
  const scheduled = visibility?.state === "not_started"
  const Icon = scheduled ? CalendarClock : Lock
  return (
    <main className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="w-full max-w-md rounded-2xl border bg-card p-8 text-center shadow-sm">
        {/* eslint-disable-next-line @next/next/no-img-element -- small static SVG */}
        <img src="/brand/obelytics-mark.svg" alt="Obelytics" width={40} height={40} className="mx-auto size-10" />
        <div className="mx-auto mt-6 flex size-10 items-center justify-center rounded-full bg-muted">
          <Icon className="size-5 text-muted-foreground" aria-hidden />
        </div>
        <h1 className="mt-4 text-xl font-semibold">
          {scheduled ? "Not available yet" : visibility ? "Not available" : "Temporarily unavailable"}
        </h1>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          {visibility?.message ?? "The documentation could not be loaded. Please try again in a moment."}
        </p>
      </div>
    </main>
  )
}
