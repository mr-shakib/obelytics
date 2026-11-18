"use client"

import { ExternalLink, FileDown, Link2, Menu, Printer, Search, Share2 } from "lucide-react"
import { useEffect, useMemo, useState } from "react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import {
  Command,
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { docsPublicApi } from "@/lib/docs/api"
import { type DocsGroup, type DocsMode, type DocsSection, GROUP_ORDER, GROUP_TITLES, type PublicDocs } from "@/lib/docs/types"
import { cn } from "@/lib/utils"

import { LiveSystemBand } from "./live"
import { plainText } from "./markdown"
import { SectionBody, youtubeEmbed } from "./section-body"

const GITHUB = "https://github.com/mr-shakib/obelytics"

// One fixed zone and locale, so the server-rendered HTML and the browser agree (no hydration mismatch).
const ZONE = "Asia/Dhaka"
const DAY = new Intl.DateTimeFormat("en-GB", { timeZone: ZONE, day: "numeric", month: "short", year: "numeric" })
const DAY_TIME = new Intl.DateTimeFormat("en-GB", {
  timeZone: ZONE, day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit", hour12: false,
})

function grouped(sections: DocsSection[]) {
  return GROUP_ORDER.map((group) => ({ group, sections: sections.filter((s) => s.group === group) })).filter(
    (g) => g.sections.length
  )
}

/** The section whose heading was last scrolled past the header line. */
function useActiveSection(keys: string[]) {
  const [active, setActive] = useState<string | null>(null)
  useEffect(() => {
    let frame = 0
    function update() {
      frame = 0
      let current: string | null = null
      for (const key of keys) {
        const el = document.getElementById(key)
        if (el && el.getBoundingClientRect().top <= 140) current = key
      }
      const atBottom = window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 4
      setActive(atBottom ? keys.at(-1) ?? current : current)
    }
    function onScroll() {
      if (!frame) frame = requestAnimationFrame(update)
    }
    window.addEventListener("scroll", onScroll, { passive: true })
    window.addEventListener("resize", onScroll)
    onScroll()
    return () => {
      window.removeEventListener("scroll", onScroll)
      window.removeEventListener("resize", onScroll)
      if (frame) cancelAnimationFrame(frame)
    }
  }, [keys])
  return active
}

/** Every typed word must appear in the section; title matches rank first. */
function searchFilter(value: string, search: string, keywords?: string[]): number {
  const words = search.toLowerCase().split(/\s+/).filter(Boolean)
  if (!words.length) return 1
  const text = value.toLowerCase()
  if (!words.every((w) => text.includes(w))) return 0
  const title = (keywords?.[0] ?? "").toLowerCase()
  return words.every((w) => title.includes(w)) ? 1 : 0.5
}

function sectionUrl(key?: string) {
  const base = `${window.location.origin}/docs`
  return key ? `${base}#${key}` : base
}

async function copyLink(key?: string) {
  try {
    await navigator.clipboard.writeText(sectionUrl(key))
    toast.success(key ? "Link to this section copied" : "Link to the page copied")
  } catch {
    toast.error("Copy failed — the address is in the address bar")
  }
}

function Nav({ groups, active, onNavigate }: {
  groups: { group: DocsGroup; sections: DocsSection[] }[]
  active: string | null
  onNavigate?: () => void
}) {
  return (
    <nav aria-label="Sections" className="space-y-6 text-sm">
      {groups.map(({ group, sections }) => (
        <div key={group}>
          <div className="mb-2 px-2 text-[11px] font-semibold tracking-wider text-muted-foreground uppercase">{GROUP_TITLES[group]}</div>
          <ul className="space-y-0.5">
            {sections.map((s) => (
              <li key={s.key}>
                <a
                  href={`#${s.key}`}
                  onClick={onNavigate}
                  aria-current={active === s.key ? "location" : undefined}
                  className={cn(
                    "block rounded-md px-2 py-1.5 transition-colors hover:bg-muted",
                    active === s.key
                      ? "bg-[#eef7f2] font-medium text-[#1d7254] dark:bg-[#173328] dark:text-[#5BD69B]"
                      : "text-foreground/80"
                  )}
                >
                  {s.title}
                </a>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </nav>
  )
}

export function DocsView({ docs, mode }: { docs: PublicDocs; mode: DocsMode }) {
  const groups = useMemo(() => grouped(docs.sections), [docs.sections])
  const keys = useMemo(() => docs.sections.map((s) => s.key), [docs.sections])
  const active = useActiveSection(keys)
  const [searchOpen, setSearchOpen] = useState(false)
  const [navOpen, setNavOpen] = useState(false)
  const demo = docs.sections.find((s) => s.kind === "demo")
  const video = demo?.data.video_url && youtubeEmbed(demo.data.video_url) ? demo.data.video_url : null
  const lastPublished = docs.sections
    .map((s) => s.published_at)
    .filter((d): d is string => !!d)
    .sort()
    .at(-1)

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const typing = (e.target as HTMLElement | null)?.closest("input, textarea, [contenteditable=true]")
      if ((e.key === "k" && (e.metaKey || e.ctrlKey)) || (e.key === "/" && !typing)) {
        e.preventDefault()
        setSearchOpen(true)
      }
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [])

  const searchIndex = useMemo(
    () =>
      docs.sections.map((s) => {
        const items = Array.isArray(s.data.items)
          ? (s.data.items as Record<string, unknown>[]).map((i) => Object.values(i).filter((v) => typeof v === "string").join(" ")).join(" ")
          : ""
        const team = s.kind === "team" ? docs.team.map((m) => `${m.full_name} ${m.role}`).join(" ") : ""
        const text = plainText(`${s.body} ${items} ${team}`)
        return { key: s.key, title: s.title, group: s.group, text, snippet: text.slice(0, 120) }
      }),
    [docs.sections, docs.team]
  )

  function jump(key: string) {
    setSearchOpen(false)
    document.getElementById(key)?.scrollIntoView({ behavior: "smooth", block: "start" })
    history.replaceState(null, "", `#${key}`)
  }

  const actions = (
    <>
      <Button variant="outline" size="sm" onClick={() => setSearchOpen(true)} className="gap-2 text-muted-foreground">
        <Search data-icon="inline-start" />
        <span className="hidden sm:inline">Search</span>
        <kbd className="hidden rounded border bg-muted px-1 font-mono text-[10px] md:inline">Ctrl K</kbd>
      </Button>
      <Button variant="ghost" size="icon-sm" onClick={() => window.print()} aria-label="Print or save as PDF" title="Print or save as PDF">
        <Printer />
      </Button>
      {mode === "public" && (
        <Button variant="ghost" size="icon-sm" nativeButton={false} render={<a href={docsPublicApi.exportUrl} download="obelytics-docs.md" />} aria-label="Download as Markdown" title="Download as Markdown">
          <FileDown />
        </Button>
      )}
      <Button variant="ghost" size="icon-sm" onClick={() => void copyLink()} aria-label="Copy a link to this page" title="Copy a link to this page">
        <Share2 />
      </Button>
    </>
  )

  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className={cn("z-40 border-b bg-background/85 backdrop-blur print:hidden", mode === "public" ? "sticky top-0" : "")}>
        <div className="mx-auto flex h-14 max-w-7xl items-center gap-3 px-4 sm:px-6">
          <Button variant="ghost" size="icon-sm" className="lg:hidden" onClick={() => setNavOpen(true)} aria-label="Open the section menu">
            <Menu />
          </Button>
          <a href="#top" className="flex min-w-0 items-center gap-2 font-semibold">
            {/* eslint-disable-next-line @next/next/no-img-element -- small static SVG */}
            <img src="/brand/obelytics-mark.svg" alt="" width={24} height={24} className="size-6 dark:hidden" />
            {/* eslint-disable-next-line @next/next/no-img-element -- small static SVG */}
            <img src="/brand/obelytics-mark-on-dark.svg" alt="" width={24} height={24} className="hidden size-6 dark:block" />
            <span className="truncate">{docs.product}</span>
            <span className="hidden rounded-full bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground sm:inline">Docs</span>
          </a>
          <div className="ml-auto flex items-center gap-1">{actions}</div>
        </div>
      </header>

      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:grid lg:grid-cols-[220px_minmax(0,1fr)] lg:gap-10">
        <aside className="hidden lg:block print:hidden">
          <div className="sticky top-14 max-h-[calc(100vh-3.5rem)] overflow-y-auto py-8 pr-2">
            <Nav groups={groups} active={active} />
          </div>
        </aside>

        <main id="top" className="min-w-0 py-8 sm:py-10">
          <div className="max-w-4xl">
            <section className="pb-8">
              <p className="text-sm font-semibold tracking-wide text-[#1d7254] uppercase dark:text-[#5BD69B]">
                AI-native outcome-based education
              </p>
              <h1 className="mt-2 text-3xl font-bold tracking-tight text-balance sm:text-4xl">
                Turning academic outcomes into proven capabilities.
              </h1>
              <p className="mt-3 max-w-2xl text-base leading-7 text-muted-foreground text-pretty">
                {docs.product}{" "}runs a degree program&apos;s whole outcome-based education cycle, from course design to
                accreditation, with AI that checks the evidence instead of just storing it. This page is our pitch deck,
                technical documentation and a live view of the running system.
              </p>
              <div className="mt-5 flex flex-wrap gap-2 print:hidden">
                <Button nativeButton={false} render={<a href="https://obelytics.bitstreamhq.com" target="_blank" rel="noreferrer" />}>
                  Open the live demo <ExternalLink data-icon="inline-end" />
                </Button>
                {video && (
                  <Button variant="outline" nativeButton={false} render={<a href="#product-demo" />}>
                    Watch the 3-minute pitch
                  </Button>
                )}
                <Button variant="outline" nativeButton={false} render={<a href={GITHUB} target="_blank" rel="noreferrer" />}>
                  Source on GitHub
                </Button>
              </div>
            </section>

            <LiveSystemBand mode={mode} />

            {groups.map(({ group, sections }) => (
              <div key={group} className="mt-12">
                <div className="mb-2 flex items-center gap-3">
                  <h2 className="text-xs font-semibold tracking-[0.18em] text-muted-foreground uppercase">{GROUP_TITLES[group]}</h2>
                  <div className="h-px flex-1 bg-border" />
                </div>
                {sections.map((s) => (
                  <section key={s.key} id={s.key} className="group/section scroll-mt-20 border-b py-9 last:border-b-0 print:break-inside-avoid-page">
                    <div className="mb-4 flex items-start justify-between gap-3">
                      <h3 className="text-2xl font-semibold tracking-tight">
                        <a href={`#${s.key}`} className="hover:underline hover:decoration-muted-foreground/40 hover:underline-offset-8">
                          {s.title}
                        </a>
                      </h3>
                      <Button
                        variant="ghost"
                        size="icon-xs"
                        onClick={() => void copyLink(s.key)}
                        aria-label={`Copy a link to ${s.title}`}
                        title="Copy a link to this section"
                        className="mt-1 opacity-60 group-hover/section:opacity-100 focus-visible:opacity-100 print:hidden"
                      >
                        <Link2 />
                      </Button>
                    </div>
                    <SectionBody section={s} docs={docs} mode={mode} />
                    {s.published_at && (
                      <p className="mt-5 text-xs text-muted-foreground">
                        Version {s.version} · published {DAY.format(new Date(s.published_at))}
                      </p>
                    )}
                  </section>
                ))}
              </div>
            ))}

            <footer className="mt-12 border-t pt-6 text-sm text-muted-foreground">
              <p>
                Every figure marked live is read from this deployment when the page loads, and refreshes every 30 seconds.
                {lastPublished ? ` Content last published ${DAY_TIME.format(new Date(lastPublished))} (Dhaka time).` : ""}
              </p>
              <p className="mt-1">
                © {new Date().getFullYear()} {docs.product} ·{" "}
                <a className="underline underline-offset-4" href={GITHUB} target="_blank" rel="noreferrer">GitHub</a>
              </p>
            </footer>
          </div>
        </main>
      </div>

      <Sheet open={navOpen} onOpenChange={setNavOpen}>
        <SheetContent side="left" className="w-72 overflow-y-auto p-4">
          <SheetHeader className="p-0">
            <SheetTitle>Sections</SheetTitle>
          </SheetHeader>
          <Nav groups={groups} active={active} onNavigate={() => setNavOpen(false)} />
        </SheetContent>
      </Sheet>

      <CommandDialog open={searchOpen} onOpenChange={setSearchOpen} title="Search the docs" description="Find a section">
        <Command filter={searchFilter}>
        <CommandInput placeholder="Search sections, features, team…" />
        <CommandList>
          <CommandEmpty>Nothing found.</CommandEmpty>
          {GROUP_ORDER.map((group) => {
            const rows = searchIndex.filter((r) => r.group === group)
            if (!rows.length) return null
            return (
              <CommandGroup key={group} heading={GROUP_TITLES[group]}>
                {rows.map((r) => (
                  <CommandItem key={r.key} value={`${r.key} ${r.title} ${r.text}`} keywords={[r.title]} onSelect={() => jump(r.key)}>
                    <div className="min-w-0">
                      <div className="font-medium">{r.title}</div>
                      <div className="truncate text-xs text-muted-foreground">{r.snippet}</div>
                    </div>
                  </CommandItem>
                ))}
              </CommandGroup>
            )
          })}
        </CommandList>
        </Command>
      </CommandDialog>
    </div>
  )
}
