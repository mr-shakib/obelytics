"use client"

import { useEffect, useId, useState } from "react"

import { Skeleton } from "@/components/ui/skeleton"

type Rendered = { code: string; svg?: string; error?: string }

/**
 * A Mermaid diagram, rendered in the browser. Mermaid is loaded only when a diagram is on
 * screen (it is large), and in strict mode, which strips scripts from the output.
 */
export function MermaidDiagram({ code, label }: { code: string; label: string }) {
  const baseId = useId().replace(/[^a-zA-Z0-9]/g, "")
  const [rendered, setRendered] = useState<Rendered | null>(null)

  useEffect(() => {
    let cancelled = false
    async function render() {
      const mermaid = (await import("mermaid")).default
      const dark = document.documentElement.classList.contains("dark")
      mermaid.initialize({
        startOnLoad: false,
        securityLevel: "strict",
        theme: dark ? "dark" : "base",
        fontFamily: "var(--font-poppins), ui-sans-serif, system-ui, sans-serif",
        flowchart: { curve: "basis", padding: 14, nodeSpacing: 36, rankSpacing: 44 },
        themeVariables: dark
          ? { primaryColor: "#173328", primaryBorderColor: "#5BD69B", lineColor: "#7cc4a0", fontSize: "14px" }
          : {
              primaryColor: "#eef7f2",
              primaryBorderColor: "#1d7254",
              primaryTextColor: "#10201a",
              lineColor: "#5b6b63",
              secondaryColor: "#fff7ea",
              tertiaryColor: "#f7faf8",
              clusterBkg: "#f7faf8",
              clusterBorder: "#c9e6d6",
              fontSize: "14px",
            },
      })
      try {
        const { svg } = await mermaid.render(`mmd-${baseId}-${Date.now()}`, code)
        if (!cancelled) setRendered({ code, svg })
      } catch (err) {
        if (!cancelled) setRendered({ code, error: err instanceof Error ? err.message : String(err) })
      }
    }
    if (code.trim()) void render()
    return () => {
      cancelled = true
    }
  }, [code, baseId])

  if (!code.trim()) return null
  if (!rendered || rendered.code !== code) return <Skeleton className="h-72 w-full rounded-xl" />
  if (rendered.error) {
    return (
      <div className="rounded-xl border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">
        The diagram could not be drawn: {rendered.error.split("\n")[0]}
      </div>
    )
  }
  return (
    <figure
      role="img"
      aria-label={label}
      className="overflow-x-auto rounded-xl border bg-card p-4 sm:p-6 print:overflow-visible [&_svg]:mx-auto [&_svg]:h-auto [&_svg]:max-w-full"
      dangerouslySetInnerHTML={{ __html: rendered.svg ?? "" }}
    />
  )
}
