"use client"

import { useQuery } from "@tanstack/react-query"
import { formatDistanceToNowStrict } from "date-fns"
import { Activity, ChevronDown, Cpu, Database, Gauge, Plug, Search, Server, Timer, Zap } from "lucide-react"
import dynamic from "next/dynamic"
import { useEffect, useMemo, useState } from "react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import { docsAdminApi, docsPublicApi } from "@/lib/docs/api"
import type {
  ApiReference,
  ChangelogItem,
  DocsMode,
  FeatureItem,
  FeatureStatus,
  LiveData,
} from "@/lib/docs/types"
import { cn } from "@/lib/utils"

const LiveCharts = dynamic(() => import("./live-charts"), {
  ssr: false,
  loading: () => <Skeleton className="h-56 w-full rounded-xl" />,
})

export function useLive(mode: DocsMode) {
  return useQuery<LiveData>({
    queryKey: ["docs", "live", mode],
    queryFn: mode === "preview" ? docsAdminApi.live : docsPublicApi.live,
    refetchInterval: 30_000,
    staleTime: 10_000,
    refetchOnWindowFocus: true,
    retry: 1,
  })
}

export function useNow(intervalMs = 5_000) {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), intervalMs)
    return () => clearInterval(id)
  }, [intervalMs])
  return now
}

export function ago(iso: string | null | undefined): string {
  if (!iso) return "never"
  return formatDistanceToNowStrict(new Date(iso), { addSuffix: true })
}

function uptime(seconds: number): string {
  const d = Math.floor(seconds / 86_400)
  const h = Math.floor((seconds % 86_400) / 3_600)
  const m = Math.floor((seconds % 3_600) / 60)
  if (d) return `${d}d ${h}h`
  if (h) return `${h}h ${m}m`
  return `${m}m`
}

const nf = new Intl.NumberFormat("en-US")

// ── Live system band ──────────────────────────────────────────────────────────

function Tile({ icon: Icon, label, value, hint }: {
  icon: typeof Activity
  label: string
  value: React.ReactNode
  hint?: string
}) {
  return (
    <div className="rounded-xl border bg-card p-3.5">
      <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
        <Icon className="size-3.5" aria-hidden />
        {label}
      </div>
      <div className="mt-1 text-lg font-semibold tracking-tight tabular-nums">{value}</div>
      {hint && <div className="mt-0.5 truncate text-xs text-muted-foreground">{hint}</div>}
    </div>
  )
}

export function LiveSystemBand({ mode }: { mode: DocsMode }) {
  const { data: live, isError, dataUpdatedAt, isFetching } = useLive(mode)
  const now = useNow()
  if (isError && !live) {
    return (
      <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-4 text-sm">
        Live figures are unavailable right now; the rest of the page is current.
      </div>
    )
  }
  if (!live) return <Skeleton className="h-40 w-full rounded-2xl" />
  const ok = live.system.status === "operational"
  const seconds = Math.max(0, Math.round((now - dataUpdatedAt) / 1000))
  return (
    <section aria-label="Live system" className="rounded-2xl border bg-gradient-to-br from-[#eef7f2] to-transparent p-4 sm:p-5 dark:from-[#173328]/60">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-sm font-medium">
          <span className="relative flex size-2.5">
            <span className={cn("absolute inline-flex size-full animate-ping rounded-full opacity-60 motion-reduce:hidden", ok ? "bg-emerald-500" : "bg-amber-500")} />
            <span className={cn("relative inline-flex size-2.5 rounded-full", ok ? "bg-emerald-500" : "bg-amber-500")} />
          </span>
          {ok ? "All systems operational" : "Running with reduced capacity (cache or queue unavailable)"}
        </div>
        <div className="text-xs text-muted-foreground" aria-live="polite">
          Live from this server · updated {seconds < 5 ? "just now" : `${seconds}s ago`}
          {isFetching ? " · refreshing" : ""}
        </div>
      </div>
      <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-4">
        <Tile icon={Server} label="Uptime" value={uptime(live.system.uptime_seconds)} hint={`since ${new Date(live.system.started_at).toLocaleDateString()}`} />
        <Tile icon={Plug} label="API endpoints" value={nf.format(live.api.endpoints)} hint={`${live.api.modules} modules`} />
        <Tile icon={Cpu} label="MCP tools" value={live.api.mcp_tools.length} hint="read-only, for AI agents" />
        <Tile icon={Database} label="Database" value={live.system.database ? "Healthy" : "Down"} hint={live.system.migration ? `schema ${live.system.migration.split("_")[0]}` : undefined} />
        <Tile icon={Zap} label="AI calls, 30 days" value={nf.format(live.ai.calls_30d)} hint={`last ${ago(live.ai.last_call_at)}`} />
        <Tile icon={Timer} label="Avg AI latency" value={live.ai.avg_latency_ms_30d ? `${(live.ai.avg_latency_ms_30d / 1000).toFixed(1)} s` : "—"} hint="per model call, 30 days" />
        <Tile icon={Gauge} label="Personal data redacted" value={nf.format(live.ai.redactions_30d)} hint="items, before external calls" />
        <Tile icon={Activity} label="Audit events, 14 days" value={nf.format(live.events.daily.reduce((s, d) => s + d.events, 0))} hint={live.events.recent[0] ? `last ${ago(live.events.recent[0].at)}` : undefined} />
      </div>
    </section>
  )
}

// ── Usage ─────────────────────────────────────────────────────────────────────

const USAGE_ORDER = [
  "organizations", "users", "programs", "courses", "course_outcomes", "mapping_sets", "sections",
  "students", "marks", "published_results", "papers", "question_audits", "reviews", "rewrites",
  "improvement_plans", "job_postings", "evidence_drafts", "copilot_conversations", "mcp_calls", "ai_calls",
]

export function UsageTable({ mode }: { mode: DocsMode }) {
  const { data: live } = useLive(mode)
  if (!live) return <Skeleton className="h-64 w-full rounded-xl" />
  const rows = USAGE_ORDER.filter((k) => live.usage[k]).map((k) => ({ key: k, ...live.usage[k] }))
  return (
    <div className="overflow-hidden rounded-xl border">
      <table className="w-full text-sm">
        <thead className="bg-muted/60 text-xs tracking-wide text-muted-foreground uppercase">
          <tr>
            <th className="px-3 py-2.5 text-left font-semibold">Live figure</th>
            <th className="px-3 py-2.5 text-right font-semibold">Real institutions</th>
            <th className="px-3 py-2.5 text-right font-semibold">Demo (synthetic)</th>
            <th className="hidden px-3 py-2.5 text-right font-semibold sm:table-cell">Latest</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.key} className="border-t">
              <td className="px-3 py-2">{r.label}</td>
              <td className="px-3 py-2 text-right font-medium tabular-nums">{nf.format(r.real)}</td>
              <td className="px-3 py-2 text-right text-muted-foreground tabular-nums">{nf.format(r.demo)}</td>
              <td className="hidden px-3 py-2 text-right text-xs text-muted-foreground sm:table-cell">{r.last_at ? ago(r.last_at) : "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ── Feature matrix ────────────────────────────────────────────────────────────

const STATUS_STYLE: Record<FeatureStatus | "off", { label: string; className: string }> = {
  live: { label: "Live", className: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300" },
  beta: { label: "Beta", className: "bg-amber-500/10 text-amber-700 dark:text-amber-300" },
  upcoming: { label: "Upcoming", className: "bg-sky-500/10 text-sky-700 dark:text-sky-300" },
  planned: { label: "Planned", className: "bg-muted text-muted-foreground" },
  off: { label: "Off on this server", className: "bg-destructive/10 text-destructive" },
}

export function FeatureMatrix({ items, mode }: { items: FeatureItem[]; mode: DocsMode }) {
  const { data: live } = useLive(mode)
  const [filter, setFilter] = useState<FeatureStatus | "all">("all")
  const providers = new Map(live?.ai.features.map((f) => [f.feature, f.provider]))
  const counts = items.reduce<Record<string, number>>((acc, i) => ({ ...acc, [i.status]: (acc[i.status] ?? 0) + 1 }), {})
  const shown = filter === "all" ? items : items.filter((i) => i.status === filter)
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-1.5 print:hidden" role="group" aria-label="Filter by status">
        {(["all", "live", "beta", "upcoming", "planned"] as const).map((s) => (
          <Button key={s} size="xs" variant={filter === s ? "default" : "outline"} onClick={() => setFilter(s)} aria-pressed={filter === s}>
            {s === "all" ? `All ${items.length}` : `${STATUS_STYLE[s].label} ${counts[s] ?? 0}`}
          </Button>
        ))}
      </div>
      <div className="overflow-x-auto rounded-xl border">
        <table className="w-full min-w-[640px] text-sm">
          <thead className="bg-muted/60 text-xs tracking-wide text-muted-foreground uppercase">
            <tr>
              <th className="px-3 py-2.5 text-left font-semibold">Feature</th>
              <th className="px-3 py-2.5 text-left font-semibold">Area</th>
              <th className="px-3 py-2.5 text-left font-semibold">Status</th>
              <th className="px-3 py-2.5 text-right font-semibold">Live usage</th>
            </tr>
          </thead>
          <tbody>
            {shown.map((item, i) => {
              const off = item.status === "live" && item.ai_feature && providers.get(item.ai_feature) === "off"
              const style = STATUS_STYLE[off ? "off" : item.status]
              const usage = item.signal ? live?.usage[item.signal] : undefined
              return (
                <tr key={`${item.name}-${i}`} className="border-t align-top">
                  <td className="px-3 py-2.5">
                    <div className="font-medium">{item.name}</div>
                    {item.description && <div className="mt-0.5 text-xs leading-5 text-muted-foreground">{item.description}</div>}
                  </td>
                  <td className="px-3 py-2.5 text-muted-foreground">{item.area}</td>
                  <td className="px-3 py-2.5">
                    <span className={cn("inline-flex rounded-full px-2 py-0.5 text-xs font-medium whitespace-nowrap", style.className)}>
                      {style.label}
                    </span>
                    {item.ai_feature && <span className="ml-1.5 text-[10px] font-semibold tracking-wider text-[#1d7254] uppercase dark:text-[#5BD69B]">AI</span>}
                  </td>
                  <td className="px-3 py-2.5 text-right text-xs whitespace-nowrap tabular-nums">
                    {usage ? (
                      <>
                        <div><span className="font-medium text-foreground">{nf.format(usage.real)}</span> real · {nf.format(usage.demo)} demo</div>
                        <div className="text-muted-foreground">{usage.last_at ? ago(usage.last_at) : ""}</div>
                      </>
                    ) : item.signal && !live ? <Skeleton className="ml-auto h-4 w-16" /> : <span className="text-muted-foreground">—</span>}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ── Analytics ─────────────────────────────────────────────────────────────────

export function AnalyticsPanel({ mode }: { mode: DocsMode }) {
  const { data: live } = useLive(mode)
  if (!live) return <Skeleton className="h-72 w-full rounded-xl" />
  return (
    <div className="space-y-5">
      <LiveCharts ai={live.ai.daily} events={live.events.daily} />
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="overflow-hidden rounded-xl border">
          <div className="border-b bg-muted/60 px-3 py-2.5 text-xs font-semibold tracking-wide text-muted-foreground uppercase">AI features on this server</div>
          <ul className="divide-y text-sm">
            {live.ai.features.map((f) => (
              <li key={f.feature} className="flex items-start justify-between gap-3 px-3 py-2.5">
                <div className="min-w-0">
                  <div className="font-medium">{f.title}</div>
                  <div className="text-xs text-muted-foreground">
                    {f.provider === "off" ? "Switched off" : `${f.provider === "hosted" ? "Hosted" : "Self-hosted"} · ${f.model ?? "model not set"}`}
                    {f.external ? " · personal data redacted" : ""}
                  </div>
                </div>
                <div className="shrink-0 text-right text-xs tabular-nums">
                  <div className="font-medium">{nf.format(f.calls_30d)} calls</div>
                  <div className="text-muted-foreground">{f.last_call_at ? ago(f.last_call_at) : "30 days"}</div>
                </div>
              </li>
            ))}
          </ul>
        </div>
        <div className="overflow-hidden rounded-xl border">
          <div className="border-b bg-muted/60 px-3 py-2.5 text-xs font-semibold tracking-wide text-muted-foreground uppercase">Recent events (audit log)</div>
          <ul className="divide-y text-sm">
            {live.events.recent.length === 0 && <li className="px-3 py-3 text-muted-foreground">No events yet.</li>}
            {live.events.recent.slice(0, 8).map((e, i) => (
              <li key={`${e.at}-${i}`} className="flex items-center justify-between gap-3 px-3 py-2">
                <span className="min-w-0 truncate">
                  <span className="font-medium">{e.action.replaceAll("_", " ").toLowerCase()}</span>
                  <span className="text-muted-foreground"> · {e.entity_type.replaceAll("_", " ")}</span>
                </span>
                <span className="flex shrink-0 items-center gap-2 text-xs text-muted-foreground">
                  {e.demo && <Badge variant="outline" className="h-4 px-1.5 text-[10px]">demo</Badge>}
                  {ago(e.at)}
                </span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  )
}

// ── API reference (loaded on demand) ──────────────────────────────────────────

const METHOD_STYLE: Record<string, string> = {
  GET: "text-sky-700 bg-sky-500/10 dark:text-sky-300",
  POST: "text-emerald-700 bg-emerald-500/10 dark:text-emerald-300",
  PUT: "text-amber-700 bg-amber-500/10 dark:text-amber-300",
  PATCH: "text-violet-700 bg-violet-500/10 dark:text-violet-300",
  DELETE: "text-red-700 bg-red-500/10 dark:text-red-300",
}

export function ApiPanel({ mode }: { mode: DocsMode }) {
  const { data: live } = useLive(mode)
  const [open, setOpen] = useState(false)
  const [q, setQ] = useState("")
  const { data: ref, isLoading } = useQuery<ApiReference>({
    queryKey: ["docs", "api-reference", mode],
    queryFn: mode === "preview" ? docsAdminApi.apiReference : docsPublicApi.apiReference,
    enabled: open,
    staleTime: 5 * 60_000,
  })
  const groups = useMemo(() => {
    if (!ref) return []
    const needle = q.trim().toLowerCase()
    return ref.groups
      .map((g) => ({
        ...g,
        endpoints: needle
          ? g.endpoints.filter((e) => `${e.method} ${e.path} ${e.summary} ${g.module}`.toLowerCase().includes(needle))
          : g.endpoints,
      }))
      .filter((g) => g.endpoints.length)
  }, [ref, q])

  return (
    <div className="space-y-4">
      {live && (
        <div className="rounded-xl border p-4">
          <div className="mb-2 text-sm font-semibold">MCP tools (live)</div>
          <ul className="grid gap-2 sm:grid-cols-2">
            {live.api.mcp_tools.map((t) => (
              <li key={t.name} className="rounded-lg bg-muted/50 px-3 py-2">
                <code className="font-mono text-xs font-semibold">{t.name}</code>
                <div className="mt-0.5 text-xs leading-5 text-muted-foreground">{t.description}</div>
              </li>
            ))}
          </ul>
        </div>
      )}
      <div className="rounded-xl border">
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left text-sm font-semibold print:hidden"
        >
          <span>
            REST endpoints{live ? ` — ${nf.format(live.api.endpoints)} live in ${live.api.modules} modules` : ""}
          </span>
          <ChevronDown className={cn("size-4 transition-transform", open && "rotate-180")} aria-hidden />
        </button>
        {open && (
          <div className="space-y-4 border-t p-4">
            <div className="relative">
              <Search className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
              <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Filter endpoints, e.g. attainment or POST" className="pl-8" aria-label="Filter endpoints" />
            </div>
            {isLoading && <Skeleton className="h-40 w-full" />}
            {groups.map((g) => (
              <details key={g.module} className="group rounded-lg border" open={!!q}>
                <summary className="flex cursor-pointer items-center justify-between px-3 py-2 text-sm font-medium">
                  {g.module}
                  <span className="text-xs text-muted-foreground">{g.endpoints.length}</span>
                </summary>
                <ul className="divide-y border-t">
                  {g.endpoints.map((e) => (
                    <li key={`${e.method} ${e.path}`} className="flex flex-wrap items-center gap-x-3 gap-y-1 px-3 py-1.5 text-xs">
                      <span className={cn("w-14 rounded px-1.5 py-0.5 text-center font-mono font-semibold", METHOD_STYLE[e.method] ?? "bg-muted")}>{e.method}</span>
                      <code className="font-mono break-all">{e.path}</code>
                      <span className="text-muted-foreground">{e.summary}</span>
                      {e.auth === "public" && <Badge variant="outline" className="h-4 px-1.5 text-[10px]">public</Badge>}
                    </li>
                  ))}
                </ul>
              </details>
            ))}
            {ref && !groups.length && <p className="text-sm text-muted-foreground">No endpoint matches “{q}”.</p>}
          </div>
        )}
      </div>
    </div>
  )
}

// ── Changelog ─────────────────────────────────────────────────────────────────

export function ChangelogTimeline({ items }: { items: ChangelogItem[] }) {
  if (!items.length) return null
  return (
    <ol className="relative space-y-6 border-l border-[#1d7254]/25 pl-6">
      {items.map((item, i) => (
        <li key={`${item.version}-${i}`} className="relative">
          <span className="absolute top-1.5 -left-[1.95rem] size-3 rounded-full border-2 border-background bg-[#1d7254] dark:bg-[#5BD69B]" aria-hidden />
          <div className="flex flex-wrap items-baseline gap-x-2">
            <span className="font-mono text-xs font-semibold text-[#1d7254] dark:text-[#5BD69B]">{item.version}</span>
            <span className="font-semibold">{item.title}</span>
            {item.date && <time className="text-xs text-muted-foreground" dateTime={item.date}>{item.date}</time>}
          </div>
          {item.notes && <p className="mt-1 text-sm leading-6 text-muted-foreground">{item.notes}</p>}
        </li>
      ))}
    </ol>
  )
}
